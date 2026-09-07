"""Task execution, retry, stale-state, and retry-endpoint behavior."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import update

from app.api.dependencies import get_ingestion_dispatcher
from app.core.config import get_settings
from app.domain.models.chunk import ChunkMetadata, VectorRecord
from app.infrastructure.embedding.base import EmbeddingClient
from app.infrastructure.database.models.document import DocumentModel
from app.infrastructure.database.session import get_session_maker
from app.infrastructure.vector_store.chroma import (
    ChromaVectorRepository,
    reset_collection,
)
from app.rag.ingestion.errors import ParsingError
from app.worker import run_ingestion_with_retries
from app.main import app


class FlakyEmbeddingClient(EmbeddingClient):
    def __init__(self, fail_count: int) -> None:
        self.fail_count = fail_count
        self.calls = 0

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        if self.calls <= self.fail_count:
            raise RuntimeError("embedding provider unavailable")
        return [
            [float((idx + j) % 7 + 1) for j in range(4)]
            for idx, _ in enumerate(texts)
        ]


@pytest_asyncio.fixture(scope="module", autouse=True)
async def _isolated_vector_collection() -> None:
    settings = get_settings()
    original = settings.chroma_collection
    settings.chroma_collection = "lifeagent_test_retry_vectors"
    reset_collection(settings.chroma_collection)
    yield
    settings.chroma_collection = original


async def _upload(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    filename: str,
    content: bytes,
) -> httpx.Response:
    return await client.post(
        "/api/v1/documents",
        files={"file": (filename, content)},
        data={"document_type": "note"},
        headers=auth_headers,
    )


async def _set_status(
    document_id: str, status: str, *, backdate_minutes: int = 0
) -> None:
    async with get_session_maker()() as session:
        values: dict = {"status": status}
        if backdate_minutes:
            values["updated_at"] = datetime.now(timezone.utc) - timedelta(
                minutes=backdate_minutes
            )
        await session.execute(
            update(DocumentModel)
            .where(DocumentModel.id == document_id)
            .values(**values)
        )
        await session.commit()


async def _get_status(client, document_id: str, auth_headers) -> dict:
    response = await client.get(
        f"/api/v1/documents/{document_id}", headers=auth_headers
    )
    assert response.status_code == 200
    return response.json()


async def test_transient_failures_retry_and_complete(
    client, auth_headers, tmp_path, monkeypatch
) -> None:
    get_settings().upload_dir = str(tmp_path)
    monkeypatch.setattr(get_settings(), "ingestion_retry_delay_seconds", 0)
    created = await _upload(
        client, auth_headers, "note.txt", b"retryable content"
    )
    document_id = created.json()["document_id"]
    embedding = FlakyEmbeddingClient(fail_count=2)

    await run_ingestion_with_retries(
        document_id, embedding_client=embedding
    )

    status = await _get_status(client, document_id, auth_headers)
    assert status["status"] == "completed"
    assert embedding.calls == 3


async def test_permanent_failure_is_not_retried(
    client, auth_headers, tmp_path
) -> None:
    get_settings().upload_dir = str(tmp_path)
    created = await _upload(client, auth_headers, "empty.txt", b"")
    document_id = created.json()["document_id"]
    embedding = FlakyEmbeddingClient(fail_count=0)

    await run_ingestion_with_retries(
        document_id, embedding_client=embedding
    )

    status = await _get_status(client, document_id, auth_headers)
    assert status["status"] == "failed"
    assert embedding.calls == 0


async def test_stale_processing_document_is_recoverable(
    client, auth_headers, tmp_path
) -> None:
    get_settings().upload_dir = str(tmp_path)
    created = await _upload(client, auth_headers, "note.txt", b"stale doc")
    document_id = created.json()["document_id"]
    # Simulate a worker crash: stuck in processing for 20 minutes.
    await _set_status(document_id, "processing", backdate_minutes=20)

    retry = await client.post(
        f"/api/v1/documents/{document_id}/retry", headers=auth_headers
    )
    assert retry.status_code == 202

    await run_ingestion_with_retries(
        document_id,
        embedding_client=FlakyEmbeddingClient(fail_count=0),
    )
    status = await _get_status(client, document_id, auth_headers)
    assert status["status"] == "completed"


async def test_retry_clears_previous_vectors_before_reindex(
    client, auth_headers, tmp_path
) -> None:
    get_settings().upload_dir = str(tmp_path)
    created = await _upload(client, auth_headers, "note.txt", b"content body")
    document_id = created.json()["document_id"]
    embedding = FlakyEmbeddingClient(fail_count=0)

    await run_ingestion_with_retries(document_id, embedding_client=embedding)
    repository = ChromaVectorRepository()
    first_ids = set(await repository.list_ids_by_document(document_id))
    assert first_ids

    await _set_status(document_id, "failed")
    await run_ingestion_with_retries(document_id, embedding_client=embedding)

    second_ids = set(await repository.list_ids_by_document(document_id))
    status = await _get_status(client, document_id, auth_headers)
    assert status["status"] == "completed"
    assert second_ids
    assert first_ids.isdisjoint(second_ids)
    await repository.delete_by_document(document_id)


async def test_retry_endpoint_enqueues_failed_document(
    client, auth_headers, tmp_path
) -> None:
    get_settings().upload_dir = str(tmp_path)
    created = await _upload(client, auth_headers, "empty.txt", b"")
    document_id = created.json()["document_id"]
    # Empty documents fail permanently; drive the failure through the worker.
    await run_ingestion_with_retries(
        document_id,
        embedding_client=FlakyEmbeddingClient(fail_count=0),
    )
    status = await _get_status(client, document_id, auth_headers)
    assert status["status"] == "failed"

    calls: list[str] = []

    async def dispatcher(document_id: str) -> None:
        calls.append(document_id)

    async def override_dependency():
        return dispatcher

    app.dependency_overrides[get_ingestion_dispatcher] = override_dependency

    try:
        response = await client.post(
            f"/api/v1/documents/{document_id}/retry", headers=auth_headers
        )
        assert response.status_code == 202
        assert calls == [document_id]
    finally:
        app.dependency_overrides.pop(get_ingestion_dispatcher, None)


async def test_retry_rejects_completed_document(
    client, auth_headers, tmp_path
) -> None:
    get_settings().upload_dir = str(tmp_path)
    created = await _upload(client, auth_headers, "note.txt", b"already done")
    document_id = created.json()["document_id"]
    await run_ingestion_with_retries(
        document_id,
        embedding_client=FlakyEmbeddingClient(fail_count=0),
    )

    response = await client.post(
        f"/api/v1/documents/{document_id}/retry", headers=auth_headers
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DOCUMENT_NOT_RETRYABLE"


async def test_cross_user_retry_is_404(
    client, auth_headers, auth_headers_second, tmp_path
) -> None:
    get_settings().upload_dir = str(tmp_path)
    created = await _upload(client, auth_headers, "empty.txt", b"")
    document_id = created.json()["document_id"]
    await run_ingestion_with_retries(
        document_id,
        embedding_client=FlakyEmbeddingClient(fail_count=0),
    )

    response = await client.post(
        f"/api/v1/documents/{document_id}/retry",
        headers=auth_headers_second,
    )
    assert response.status_code == 404


async def test_upload_queues_ingestion_without_blocking(
    client, auth_headers, tmp_path
) -> None:
    get_settings().upload_dir = str(tmp_path)
    calls: list[str] = []

    async def dispatcher(document_id: str) -> None:
        calls.append(document_id)

    async def override_dependency():
        return dispatcher

    app.dependency_overrides[get_ingestion_dispatcher] = override_dependency

    try:
        response = await _upload(
            client, auth_headers, "note.txt", b"queued content"
        )
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "uploaded"
        assert calls == [body["document_id"]]
    finally:
        app.dependency_overrides.pop(get_ingestion_dispatcher, None)
