"""Document repository abstraction."""

from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.entities.document import Document


class DocumentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, document_id: str) -> Document | None:
        raise NotImplementedError

    @abstractmethod
    async def list_by_user(
        self, user_id: str, page: int, page_size: int
    ) -> list[Document]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id_and_user(
        self, document_id: str, user_id: str
    ) -> Document | None:
        raise NotImplementedError

    @abstractmethod
    async def create(self, document: Document) -> Document:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, document_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def update_status(
        self,
        document_id: str,
        *,
        status: str,
        processing_stage: str | None = None,
        error_message: str | None = None,
        embedding_model: str | None = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def list_stale_processing(
        self, updated_before: datetime
    ) -> list[Document]:
        raise NotImplementedError
