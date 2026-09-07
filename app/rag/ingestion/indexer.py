"""Build vector records and write them to the vector store."""

import uuid

from app.domain.entities.document import Document
from app.domain.models.chunk import Chunk, ChunkMetadata, VectorRecord
from app.repositories.vector_repository import VectorRepository


class Indexer:
    def __init__(
        self, vector_repository: VectorRepository, embedding_model: str
    ) -> None:
        self._vector_repository = vector_repository
        self._embedding_model = embedding_model

    async def index(
        self,
        document: Document,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> int:
        records: list[VectorRecord] = []
        for chunk, embedding in zip(chunks, embeddings):
            metadata = ChunkMetadata(
                user_id=document.user_id,
                document_id=document.id,
                document_name=document.filename,
                document_type=document.document_type,
                start_page=chunk.start_page,
                end_page=chunk.end_page,
                chunk_index=chunk.chunk_index,
                embedding_model=self._embedding_model,
            )
            records.append(
                VectorRecord(
                    chunk_id=(
                        f"{document.id}:{chunk.chunk_index}:"
                        f"{uuid.uuid4().hex[:8]}"
                    ),
                    embedding=embedding,
                    content=chunk.content,
                    metadata=metadata,
                )
            )
        await self._vector_repository.add_vectors(records)
        return len(records)
