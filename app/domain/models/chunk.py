"""Chunk, metadata, and vector record domain models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    content: str
    chunk_index: int
    start_page: int
    end_page: int


@dataclass(frozen=True)
class ChunkMetadata:
    user_id: str
    document_id: str
    document_name: str
    document_type: str
    start_page: int
    end_page: int
    chunk_index: int
    embedding_model: str

    def as_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "document_id": self.document_id,
            "document_name": self.document_name,
            "document_type": self.document_type,
            "start_page": self.start_page,
            "end_page": self.end_page,
            "chunk_index": self.chunk_index,
            "embedding_model": self.embedding_model,
        }


@dataclass(frozen=True)
class VectorRecord:
    chunk_id: str
    embedding: list[float]
    content: str
    metadata: ChunkMetadata
