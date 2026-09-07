"""Embedding batching over the provider abstraction."""

from app.domain.models.chunk import Chunk
from app.infrastructure.embedding.base import EmbeddingClient


class Embedder:
    def __init__(self, client: EmbeddingClient, batch_size: int = 16) -> None:
        self._client = client
        self._batch_size = batch_size

    async def embed_chunks(self, chunks: list[Chunk]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for start in range(0, len(chunks), self._batch_size):
            batch = [chunk.content for chunk in chunks[start : start + self._batch_size]]
            embeddings.extend(await self._client.embed_texts(batch))
        return embeddings
