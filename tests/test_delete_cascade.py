"""Delete cascade behavior: vectors, file, database row."""

import httpx
import pytest
import pytest_asyncio

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.domain.entities.document import Document
from app.domain.models.chunk import ChunkMetadata, VectorRecord
from app.infrastructure.database.document_repository import (
    SQLAlchemyDocumentRepository,
)
from app.infrastructure.database.session import get_session_maker
from app.infrastructure.embedding.base import EmbeddingClient
from app.infrastructure.vector_store.chroma import (
    ChromaVectorRepository,
    reset_collection,
)
from app.repositories.vector_repository import VectorRepository
from app.services.document_service import DocumentService
from app.services.knowledge_service import KnowledgeService


class FakeEmbeddingClient(EmbeddingClient):
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [
            [float((idx + j) % 7 + 1) for j in range(4)]
            for idx, _ in enumerate(texts)
        ]


class FailingOnceVectorRepository(VectorRepository):
    def __init__(self) -> None:
        self.failures_left = 1
        self.deleted: list[str] = []

    async def add_vectors(self, records: list[VectorRecord]) -> None:
        pass

    async def delete_by_document(self, document_id: str) -> None:
        if self.failures_left:
            self.failures_left -= 1
            raise RuntimeError("vector store unavailable")
        self.deleted.append(document_id)

    async def list_ids_by_document(self, document_id: str) -> list[str]:
        return []

    async def fetch_document_chunks(self, document_id: str) -> list:
        return []

    async def search(
        self,
        query_embedding: list[float],
        top_k: int,
        user_id: str,
        document_type: str | None = None,
        document_id: str | None = None,
    ) -> list:
        return []


@pytest_asyncio.fixture(scope="module", autouse=True)
async def _isolated_vector_collection() -> None:
    settings = get_settings()
    original = settings.chroma_collection
    settings.chroma_collection = "lifeagent_test_delete_vectors"
    reset_collection(settings.chroma_collection)
    yield
    settings.chroma_collection = original


async def _upload(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    tmp_path,
    content: bytes = b"delete me content",
) -> str:
    get_settings().upload_dir = str(tmp_path)
    response = await client.post(
        "/api/v1/documents",
        files={"file": ("note.txt", content)},
        data={"document_type": "note"},
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["document_id"]


async def _ingest(document_id: str) -> None:
    async with get_session_maker()() as session:
        service = KnowledgeService(
            document_repository=SQLAlchemyDocumentRepository(session),
            embedding_client=FakeEmbeddingClient(),
            vector_repository=ChromaVectorRepository(),
        )
        await service.ingest(document_id)


async def test_delete_removes_vectors_file_and_record(
    client, auth_headers, tmp_path
) -> None:
    document_id = await _upload(client, auth_headers, tmp_path)
    await _ingest(document_id)
    stored_file = list(tmp_path.iterdir())[0]
    assert stored_file.exists()

    repository = ChromaVectorRepository()
    assert await repository.list_ids_by_document(document_id)

    deleted = await client.delete(
        f"/api/v1/documents/{document_id}", headers=auth_headers
    )
    assert deleted.status_code == 204
    assert not stored_file.exists()
    assert not await repository.list_ids_by_document(document_id)

    missing = await client.get(
        f"/api/v1/documents/{document_id}", headers=auth_headers
    )
    assert missing.status_code == 404

    repeated = await client.delete(
        f"/api/v1/documents/{document_id}", headers=auth_headers
    )
    assert repeated.status_code == 404


async def test_failed_cleanup_keeps_row_and_retry_succeeds(
    client, tmp_path
) -> None:
    get_settings().upload_dir = str(tmp_path)
    import uuid

    username = f"delete_user_{uuid.uuid4().hex[:8]}"
    register = await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "passw0rd123"},
    )
    assert register.status_code == 201
    user_id = register.json()["user_id"]

    async with get_session_maker()() as session:
        repository = SQLAlchemyDocumentRepository(session)
        document = await repository.create(
            Document(
                id="",
                user_id=user_id,
                filename="note.txt",
                file_type="txt",
                file_path="",
                file_size=0,
                document_type="note",
                status="uploaded",
            )
        )
        document_id = document.id

        failing = FailingOnceVectorRepository()
        service = DocumentService(
            repository=repository,
            vector_repository=failing,
        )
        with pytest.raises(AppError) as exc_info:
            await service.delete_document(document_id, user_id)
        assert exc_info.value.status_code == 500
        assert exc_info.value.code == "DOCUMENT_DELETE_FAILED"

        still_there = await repository.get_by_id_and_user(
            document_id, user_id
        )
        assert still_there is not None

        await service.delete_document(document_id, user_id)
        assert failing.deleted == [document_id]
        assert await repository.get_by_id(document_id) is None
