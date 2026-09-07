"""Retriever with mandatory user scoping."""

from app.domain.models.search_result import SearchResult
from app.infrastructure.embedding.base import EmbeddingClient
from app.repositories.vector_repository import VectorRepository


class Retriever:
    def __init__(
        self,
        embedding_client: EmbeddingClient,
        vector_repository: VectorRepository,
    ) -> None:
        self._embeddings = embedding_client
        self._vectors = vector_repository

    async def search(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        document_type: str | None = None,
        document_id: str | None = None,
    ) -> list[SearchResult]:
        """Search the current user's knowledge base only.

        user_id is always injected here and is never a Tool parameter.
        """

        if not query.strip():
            return []
        query_embedding = (await self._embeddings.embed_texts([query]))[0]
        return await self._vectors.search(
            query_embedding=query_embedding,
            top_k=top_k,
            user_id=user_id,
            document_type=document_type,
            document_id=document_id,
        )
