"""Alibaba DashScope embedding via its OpenAI-compatible API."""

import httpx

from app.core.config import Settings
from app.infrastructure.embedding.base import EmbeddingClient


class DashScopeEmbeddingClient(EmbeddingClient):
    def __init__(self, settings: Settings | None = None) -> None:
        from app.core.config import get_settings

        self._settings = settings or get_settings()

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        api_key = self._settings.dashscope_api_key
        if not api_key:
            raise RuntimeError("DASHSCOPE_API_KEY is not configured")
        url = f"{self._settings.embedding_base_url}/embeddings"
        payload = {
            "model": self._settings.embedding_model,
            "input": texts,
            "dimensions": self._settings.embedding_dimensions,
            "encoding_format": "float",
        }
        headers = {"Authorization": f"Bearer {api_key}"}
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
        data = response.json()["data"]
        ordered = sorted(data, key=lambda item: item["index"])
        return [item["embedding"] for item in ordered]
