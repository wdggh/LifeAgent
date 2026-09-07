"""ARQ worker entry point and document ingestion task."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.infrastructure.database.document_repository import (
    SQLAlchemyDocumentRepository,
)
from app.infrastructure.database.session import get_session_maker
from app.infrastructure.embedding.base import EmbeddingClient
from app.infrastructure.embedding.factory import get_embedding_client
from app.infrastructure.storage.local_storage import LocalFileStorage
from app.infrastructure.vector_store.chroma import ChromaVectorRepository
from app.rag.ingestion.errors import ParsingError
from app.repositories.vector_repository import VectorRepository
from app.services.knowledge_service import KnowledgeService

logger = logging.getLogger("app.worker")


async def sweep_stale_processing(ctx: dict | None = None) -> None:
    """Re-queue Documents stuck in processing beyond the stale threshold.

    Runs on worker startup so a crash mid-job does not leave Documents stuck
    forever; users can also retry them manually via the API.
    """

    del ctx
    settings = get_settings()
    threshold = datetime.now(timezone.utc) - timedelta(
        minutes=settings.stale_processing_minutes
    )
    async with get_session_maker()() as session:
        documents = await SQLAlchemyDocumentRepository(
            session
        ).list_stale_processing(threshold)
    for document in documents:
        logger.warning(
            "re-queueing stale processing document",
            extra={"document_id": document.id},
        )
        await enqueue_document_ingestion(document.id)


async def run_ingestion_with_retries(
    document_id: str,
    *,
    embedding_client: EmbeddingClient | None = None,
    vector_repository: VectorRepository | None = None,
    storage: LocalFileStorage | None = None,
) -> None:
    """Ingest a document, retrying transient failures with backoff.

    Permanent parsing failures are recorded as failed by KnowledgeService and
    are not retried. Transient failures retry up to the configured attempt
    budget; when the budget is exhausted the document stays failed.
    """

    settings = get_settings()
    max_attempts = max(1, settings.ingestion_max_attempts)
    for attempt in range(1, max_attempts + 1):
        try:
            async with get_session_maker()() as session:
                service = KnowledgeService(
                    document_repository=SQLAlchemyDocumentRepository(session),
                    embedding_client=(
                        embedding_client or get_embedding_client()
                    ),
                    vector_repository=(
                        vector_repository or ChromaVectorRepository()
                    ),
                    storage=storage,
                )
                await service.ingest(document_id)
            return
        except ParsingError:
            logger.info(
                "ingestion stopped after permanent parsing failure",
                extra={"document_id": document_id, "attempt": attempt},
            )
            return
        except Exception as exc:
            if attempt >= max_attempts:
                logger.exception(
                    "ingestion exhausted retries",
                    extra={"document_id": document_id, "attempt": attempt},
                )
                raise
            delay = settings.ingestion_retry_delay_seconds * attempt
            logger.warning(
                "ingestion attempt failed; retrying",
                extra={
                    "document_id": document_id,
                    "attempt": attempt,
                    "delay_seconds": delay,
                    "error": type(exc).__name__,
                },
            )
            await asyncio.sleep(delay)


async def ingest_document(ctx: dict, document_id: str) -> None:
    """ARQ task: ingest one Document."""

    del ctx
    await run_ingestion_with_retries(document_id)


async def enqueue_document_ingestion(document_id: str) -> bool:
    """Queue a Document for ingestion on the ARQ worker."""

    settings = get_settings()
    if not settings.ingestion_enqueue_enabled:
        return False
    pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        await pool.enqueue_job("ingest_document", document_id)
        return True
    finally:
        await pool.aclose()


class WorkerSettings:
    """ARQ worker configuration (`arq app.worker.WorkerSettings`)."""

    functions = [ingest_document]
    on_startup = sweep_stale_processing
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 4
