"""Knowledge base ingestion pipeline orchestration."""

import logging

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.domain.constants import DocumentStatus, ProcessingStage
from app.infrastructure.storage.local_storage import LocalFileStorage
from app.rag.ingestion.chunker import Chunker
from app.rag.ingestion.embedder import Embedder
from app.rag.ingestion.errors import ParsingError
from app.rag.ingestion.indexer import Indexer
from app.rag.ingestion.parser import DocumentParser
from app.repositories.document_repository import DocumentRepository
from app.repositories.vector_repository import VectorRepository
from app.infrastructure.embedding.base import EmbeddingClient

logger = logging.getLogger("app.ingestion")


class KnowledgeService:
    """Owns the ingestion pipeline; invoked by the worker in ticket 06."""

    def __init__(
        self,
        document_repository: DocumentRepository,
        embedding_client: EmbeddingClient,
        vector_repository: VectorRepository,
        storage: LocalFileStorage | None = None,
    ) -> None:
        self._documents = document_repository
        self._embeddings = embedding_client
        self._vectors = vector_repository
        self._storage = storage or LocalFileStorage()

    async def ingest(self, document_id: str):
        document = await self._documents.get_by_id(document_id)
        if document is None:
            raise AppError(404, "DOCUMENT_NOT_FOUND", "Document not found")
        if document.status == DocumentStatus.COMPLETED:
            return document
        if document.status in {
            DocumentStatus.FAILED,
            DocumentStatus.PROCESSING,
        }:
            # A re-run must not mix stale vectors from a previous attempt.
            await self._vectors.delete_by_document(document.id)
        settings = get_settings()
        embedding_model = (
            f"{settings.embedding_model}:{settings.embedding_dimensions}"
        )
        try:
            await self._update_status(
                document_id,
                DocumentStatus.PROCESSING,
                stage=ProcessingStage.PARSING,
            )
            pages = DocumentParser().parse(
                self._storage.path_for(document.file_path),
                document.file_type,
            )

            await self._update_status(
                document_id,
                DocumentStatus.PROCESSING,
                stage=ProcessingStage.CHUNKING,
            )
            chunks = Chunker().chunk_pages(pages)
            if not chunks:
                raise ParsingError("Document contains no extractable content")

            await self._update_status(
                document_id,
                DocumentStatus.PROCESSING,
                stage=ProcessingStage.EMBEDDING,
            )
            embeddings = await Embedder(self._embeddings).embed_chunks(chunks)

            await self._update_status(
                document_id,
                DocumentStatus.PROCESSING,
                stage=ProcessingStage.INDEXING,
            )
            indexed = await Indexer(
                self._vectors, embedding_model
            ).index(document, chunks, embeddings)
            logger.info(
                "document indexed",
                extra={
                    "document_id": document.id,
                    "chunk_count": indexed,
                    "embedding_model": embedding_model,
                },
            )

            await self._update_status(
                document_id,
                DocumentStatus.COMPLETED,
                stage=None,
                embedding_model=embedding_model,
            )
            return await self._documents.get_by_id(document_id)
        except ParsingError as exc:
            await self._fail(document_id, exc.message)
            raise
        except Exception as exc:
            logger.exception("ingestion failed", exc_info=exc)
            await self._fail(
                document_id,
                f"Document processing failed ({type(exc).__name__})",
            )
            raise

    async def _update_status(
        self,
        document_id: str,
        status: str,
        stage: str | None = None,
        error_message: str | None = None,
        embedding_model: str | None = None,
    ) -> None:
        await self._documents.update_status(
            document_id,
            status=status,
            processing_stage=stage,
            error_message=error_message,
            embedding_model=embedding_model,
        )

    async def _fail(self, document_id: str, message: str) -> None:
        await self._update_status(
            document_id,
            DocumentStatus.FAILED,
            stage=None,
            error_message=message,
        )
