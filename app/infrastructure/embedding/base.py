"""Embedding provider abstraction."""

from abc import ABC, abstractmethod


class EmbeddingClient(ABC):
    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError
