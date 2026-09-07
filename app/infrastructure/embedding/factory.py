"""Embedding provider factory (kept minimal on purpose)."""

from app.core.config import Settings, get_settings
from app.infrastructure.embedding.base import EmbeddingClient
from app.infrastructure.embedding.dashscope import DashScopeEmbeddingClient


def get_embedding_client(
    settings: Settings | None = None,
) -> EmbeddingClient:
    settings = settings or get_settings()
    if settings.embedding_provider == "dashscope":
        return DashScopeEmbeddingClient(settings)
    raise ValueError(
        f"Unsupported embedding provider: {settings.embedding_provider}"
    )
