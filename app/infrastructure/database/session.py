"""Async engine and session management."""

from functools import lru_cache
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import Settings, get_settings


@lru_cache
def get_engine():
    settings: Settings = get_settings()
    poolclass = NullPool if settings.app_env == "test" else None
    return create_async_engine(settings.database_url, poolclass=poolclass)


@lru_cache
def get_session_maker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with get_session_maker()() as session:
        yield session
