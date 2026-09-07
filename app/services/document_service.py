"""Document upload, validation, and management."""

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.domain.entities.document import Document
from app.infrastructure.vector_store.chroma import ChromaVectorRepository
from app.infrastructure.storage.local_storage import LocalFileStorage
from app.repositories.document_repository import DocumentRepository
from app.repositories.vector_repository import VectorRepository

logger = logging.getLogger("app.documents")

SUPPORTED_FILE_TYPES = {
    ".pdf": "pdf",
    ".txt": "txt",
    ".md": "markdown",
}


class DocumentService:
    def __init__(
        self,
        repository: DocumentRepository,
        storage: LocalFileStorage | None = None,
        vector_repository: VectorRepository | None = None,
    ) -> None:
        self._repository = repository
        self._storage = storage or LocalFileStorage()
        self._vectors = vector_repository

    async def upload(
        self,
        user_id: str,
        filename: str,
        document_type: str,
        content: bytes,
    ) -> Document:
        settings = get_settings()
        max_bytes = settings.max_file_size_mb * 1024 * 1024
        if len(content) > max_bytes:
            raise AppError(413, "FILE_TOO_LARGE", "File exceeds the size limit")

        file_type = self._validate_content(filename, content)
        file_path = self._storage.save(filename, content)
        document = Document(
            id="",
            user_id=user_id,
            filename=filename,
            file_type=file_type,
            file_path=file_path,
            file_size=len(content),
            document_type=document_type,
            status="uploaded",
        )
        try:
            return await self._repository.create(document)
        except Exception:
            self._storage.delete(file_path)
            raise

    @staticmethod
    def _validate_content(filename: str, content: bytes) -> str:
        suffix = Path(filename).suffix.lower()
        file_type = SUPPORTED_FILE_TYPES.get(suffix)
        if file_type is None:
            raise AppError(
                415, "UNSUPPORTED_FILE_TYPE", "Unsupported file type"
            )
        if file_type == "pdf":
            if not content.startswith(b"%PDF"):
                raise AppError(
                    415, "INVALID_FILE_CONTENT", "File content does not match its type"
                )
        else:
            sample = content[:65536]
            try:
                sample.decode("utf-8")
            except UnicodeDecodeError:
                raise AppError(
                    415, "INVALID_FILE_CONTENT", "File content does not match its type"
                ) from None
        return file_type

    async def list_documents(
        self, user_id: str, page: int, page_size: int
    ) -> list[Document]:
        return await self._repository.list_by_user(
            user_id, page, page_size
        )

    async def get_document(
        self, document_id: str, user_id: str
    ) -> Document:
        document = await self._repository.get_by_id_and_user(
            document_id, user_id
        )
        if document is None:
            raise AppError(404, "DOCUMENT_NOT_FOUND", "Document not found")
        return document

    async def delete_document(
        self, document_id: str, user_id: str
    ) -> None:
        document = await self.get_document(document_id, user_id)
        vectors = self._vectors or ChromaVectorRepository()
        try:
            # Order matters: vectors first, then the stored file, then the row.
            # Each step is idempotent so a failed delete can simply be retried.
            await vectors.delete_by_document(document.id)
            self._storage.delete(document.file_path)
            await self._repository.delete(document.id)
        except Exception as exc:
            logger.exception(
                "document deletion failed",
                extra={"document_id": document.id, "error": type(exc).__name__},
            )
            raise AppError(
                500,
                "DOCUMENT_DELETE_FAILED",
                "Failed to delete the document, please retry",
            ) from exc

    async def retry(self, document_id: str, user_id: str) -> Document:
        """Allow retrying a failed or stale-processing Document."""

        document = await self.get_document(document_id, user_id)
        retryable = document.status == "failed"
        if not retryable and document.status == "processing":
            stale_after = timedelta(
                minutes=get_settings().stale_processing_minutes
            )
            if document.updated_at and (
                datetime.now(timezone.utc) - document.updated_at
            ) >= stale_after:
                retryable = True
        if not retryable:
            raise AppError(
                409,
                "DOCUMENT_NOT_RETRYABLE",
                "Document cannot be retried in its current state",
            )
        return document
