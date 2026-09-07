"""Document upload, validation, and management."""

from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.domain.entities.document import Document
from app.infrastructure.storage.local_storage import LocalFileStorage
from app.repositories.document_repository import DocumentRepository

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
    ) -> None:
        self._repository = repository
        self._storage = storage or LocalFileStorage()

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
        self._storage.delete(document.file_path)
        await self._repository.delete(document_id)
