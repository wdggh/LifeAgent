"""Dependencies shared by protected routes."""

from collections.abc import Awaitable, Callable

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.security import decode_access_token
from app.domain.entities.user import User
from app.infrastructure.database.session import get_db
from app.infrastructure.embedding.factory import get_embedding_client
from app.infrastructure.llm.base import LLMClient
from app.infrastructure.llm.dashscope import DashScopeLLMClient
from app.infrastructure.llm.deepseek import DeepSeekClient
from app.infrastructure.database.user_repository import SQLAlchemyUserRepository
from app.infrastructure.vector_store.chroma import ChromaVectorRepository
from app.rag.retrieval.retriever import Retriever
from app.worker import enqueue_document_ingestion

IngestionDispatcher = Callable[[str], Awaitable[None]]


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(401, "UNAUTHENTICATED", "Authentication required")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise AppError(401, "UNAUTHENTICATED", "Authentication required")
    return token


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the current User from the bearer token."""

    token = _bearer_token(authorization)
    settings = get_settings()
    user_id = decode_access_token(token, settings.jwt_secret)
    if user_id is None:
        raise AppError(401, "INVALID_TOKEN", "Invalid or expired token")
    user = await SQLAlchemyUserRepository(db).get_by_id(user_id)
    if user is None:
        raise AppError(401, "INVALID_TOKEN", "Invalid or expired token")
    return user


async def get_ingestion_dispatcher() -> IngestionDispatcher:
    """Provide the ingestion enqueue function (overridable in tests)."""

    return enqueue_document_ingestion


async def get_llm_client() -> LLMClient:
    """Provide the configured LLM client (overridable in tests)."""

    settings = get_settings()
    if settings.llm_provider in {"dashscope", "qwen"}:
        return DashScopeLLMClient()
    return DeepSeekClient()


async def get_retriever() -> Retriever:
    """Provide the user-scoped retriever (overridable in tests)."""

    return Retriever(
        embedding_client=get_embedding_client(),
        vector_repository=ChromaVectorRepository(),
    )
