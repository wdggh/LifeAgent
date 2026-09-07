"""Ingestion pipeline core behavior."""

import httpx
import pytest
import pytest_asyncio

from app.core.config import get_settings
from app.infrastructure.embedding.base import EmbeddingClient
from app.infrastructure.database.session import get_session_maker
from app.infrastructure.database.document_repository import (
    SQLAlchemyDocumentRepository,
)
from app.infrastructure.vector_store.chroma import (
    ChromaVectorRepository,
    reset_collection,
)
from app.rag.ingestion.chunker import Chunker
from app.rag.ingestion.errors import ParsingError
from app.rag.ingestion.parser import ParsedPage
from app.services.knowledge_service import KnowledgeService


class FakeEmbeddingClient(EmbeddingClient):
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [
            [float((idx + j) % 7 + 1) for j in range(4)]
            for idx, _ in enumerate(texts)
        ]


@pytest_asyncio.fixture(scope="module", autouse=True)
async def _isolated_vector_collection() -> None:
    settings = get_settings()
    original = settings.chroma_collection
    settings.chroma_collection = "lifeagent_test_vectors"
    reset_collection(settings.chroma_collection)
    yield
    settings.chroma_collection = original


async def _upload(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    filename: str,
    content: bytes,
    document_type: str = "note",
) -> httpx.Response:
    return await client.post(
        "/api/v1/documents",
        files={"file": (filename, content)},
        data={"document_type": document_type},
        headers=auth_headers,
    )


async def _run_ingest(document_id: str) -> None:
    async with get_session_maker()() as session:
        service = KnowledgeService(
            document_repository=SQLAlchemyDocumentRepository(session),
            embedding_client=FakeEmbeddingClient(),
            vector_repository=ChromaVectorRepository(),
        )
        await service.ingest(document_id)


async def test_pipeline_completes_and_indexes_with_metadata(
    client, auth_headers, tmp_path
) -> None:
    get_settings().upload_dir = str(tmp_path)
    content = ("LifeAgent sample note.\n" + "content " * 400).encode("utf-8")
    created = await _upload(
        client, auth_headers, "note.txt", content, document_type="note"
    )
    assert created.status_code == 201, created.text
    document_id = created.json()["document_id"]

    try:
        await _run_ingest(document_id)

        detail = await client.get(
            f"/api/v1/documents/{document_id}", headers=auth_headers
        )
        assert detail.status_code == 200
        assert detail.json()["status"] == "completed"
        assert detail.json()["processing_stage"] is None

        repository = ChromaVectorRepository()
        records = repository.fetch_by_document(document_id)
        assert records, "vectors must be written to Chroma"
        first = records[0]
        assert first["metadata"]["user_id"]
        assert first["metadata"]["document_id"] == document_id
        assert first["metadata"]["document_name"] == "note.txt"
        assert first["metadata"]["document_type"] == "note"
        assert first["metadata"]["start_page"] == 1
        assert first["metadata"]["end_page"] == 1
        assert first["metadata"]["chunk_index"] == 0
        assert first["metadata"]["embedding_model"] == "text-embedding-v3:1024"
        assert len(first["embedding"]) == 4
        indexes = [r["metadata"]["chunk_index"] for r in records]
        assert indexes == sorted(indexes)
    finally:
        await ChromaVectorRepository().delete_by_document(document_id)


async def test_empty_document_fails_with_clear_error(
    client, auth_headers, tmp_path
) -> None:
    get_settings().upload_dir = str(tmp_path)
    created = await _upload(client, auth_headers, "empty.txt", b"")
    document_id = created.json()["document_id"]

    with pytest.raises(ParsingError):
        await _run_ingest(document_id)

    detail = await client.get(
        f"/api/v1/documents/{document_id}", headers=auth_headers
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "failed"
    assert "no extractable text" in detail.json()["error_message"]


async def test_corrupt_pdf_fails_with_clear_error(
    client, auth_headers, tmp_path
) -> None:
    get_settings().upload_dir = str(tmp_path)
    created = await _upload(
        client,
        auth_headers,
        "broken.pdf",
        b"%PDF-1.4\nthis is definitely not a real pdf body",
        document_type="contract",
    )
    document_id = created.json()["document_id"]

    with pytest.raises(ParsingError):
        await _run_ingest(document_id)

    detail = await client.get(
        f"/api/v1/documents/{document_id}", headers=auth_headers
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "failed"
    assert "Failed to parse PDF" in detail.json()["error_message"]


def test_chunker_preserves_page_ranges_and_order() -> None:
    pages = [
        ParsedPage(page=1, content="alpha " * 300),
        ParsedPage(page=2, content="beta"),
    ]
    chunks = Chunker().chunk_pages(pages)
    assert len(chunks) >= 2
    assert chunks[0].start_page == 1
    assert chunks[0].end_page == 1
    assert chunks[-1].start_page == 2
    assert chunks[-1].end_page == 2
    assert [chunk.chunk_index for chunk in chunks] == list(
        range(len(chunks))
    )
