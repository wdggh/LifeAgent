"""Document repository abstraction."""

from abc import ABC, abstractmethod

from app.domain.entities.document import Document


class DocumentRepository(ABC):
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
