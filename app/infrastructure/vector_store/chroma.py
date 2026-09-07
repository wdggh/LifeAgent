"""Chroma vector store repository (standalone service)."""

from urllib.parse import urlparse

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings
from app.domain.models.chunk import VectorRecord
from app.domain.models.search_result import SearchResult
from app.repositories.vector_repository import VectorRepository


def _build_client() -> chromadb.ClientAPI:
    settings = get_settings()
    parsed = urlparse(settings.chroma_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8000
    return chromadb.HttpClient(
        host=host,
        port=port,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


class ChromaVectorRepository(VectorRepository):
    def __init__(self) -> None:
        self._client = _build_client()
        self._collection_name = get_settings().chroma_collection
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    async def add_vectors(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        self._collection.upsert(
            ids=[record.chunk_id for record in records],
            embeddings=[record.embedding for record in records],
            documents=[record.content for record in records],
            metadatas=[record.metadata.as_dict() for record in records],
        )

    async def delete_by_document(self, document_id: str) -> None:
        ids = self._collection.get(
            where={"document_id": document_id}, include=[]
        )["ids"]
        if ids:
            self._collection.delete(ids=ids)

    async def list_ids_by_document(self, document_id: str) -> list[str]:
        return self._collection.get(
            where={"document_id": document_id}, include=[]
        )["ids"]

    async def search(
        self,
        query_embedding: list[float],
        top_k: int,
        user_id: str,
        document_type: str | None = None,
        document_id: str | None = None,
    ) -> list[SearchResult]:
        conditions: list[dict] = [{"user_id": user_id}]
        if document_type:
            conditions.append({"document_type": document_type})
        if document_id:
            conditions.append({"document_id": document_id})
        where = conditions[0] if len(conditions) == 1 else {"$and": conditions}
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        if not result["ids"] or not result["ids"][0]:
            return []
        search_results = []
        for index, chunk_id in enumerate(result["ids"][0]):
            metadata = result["metadatas"][0][index]
            search_results.append(
                SearchResult(
                    chunk_id=chunk_id,
                    document_id=metadata["document_id"],
                    document_name=metadata["document_name"],
                    content=result["documents"][0][index],
                    score=round(1.0 - result["distances"][0][index], 4),
                    start_page=metadata.get("start_page"),
                    end_page=metadata.get("end_page"),
                    document_type=metadata.get("document_type"),
                )
            )
        return search_results

    def fetch_by_document(self, document_id: str) -> list[dict]:
        """Return stored vectors for a document (used by tests/debugging)."""

        result = self._collection.get(
            where={"document_id": document_id},
            include=["documents", "metadatas", "embeddings"],
        )
        records = []
        for idx, chunk_id in enumerate(result["ids"]):
            records.append(
                {
                    "chunk_id": chunk_id,
                    "content": result["documents"][idx],
                    "metadata": result["metadatas"][idx],
                    "embedding": result["embeddings"][idx],
                }
            )
        return records


def reset_collection(collection_name: str) -> None:
    """Delete and recreate a collection (used by the test harness)."""

    client = _build_client()
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
    client.get_or_create_collection(
        name=collection_name, metadata={"hnsw:space": "cosine"}
    )
