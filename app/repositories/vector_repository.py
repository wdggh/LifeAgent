"""Vector store repository abstraction."""

from abc import ABC, abstractmethod

from app.domain.models.chunk import VectorRecord


class VectorRepository(ABC):
    @abstractmethod
    async def add_vectors(self, records: list[VectorRecord]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete_by_document(self, document_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def list_ids_by_document(self, document_id: str) -> list[str]:
        raise NotImplementedError
