"""Vector store repository abstraction."""

from abc import ABC, abstractmethod

from app.domain.models.chunk import VectorRecord
from app.domain.models.search_result import SearchResult


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

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        top_k: int,
        user_id: str,
        document_type: str | None = None,
        document_id: str | None = None,
    ) -> list[SearchResult]:
        raise NotImplementedError
