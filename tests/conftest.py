"""Shared async test harness.

Conventions:
- Tests run with APP_ENV=test against the isolated `lifeagent_test` database
  (PostgreSQL via docker compose); tables are rebuilt per session and rows are
  cleaned before every test.
- The primary seam is the public HTTP API through an async httpx client with an
  ASGI transport. Real external providers (LLM/Embedding) are never called.
"""

import os

os.environ["APP_ENV"] = "test"
os.environ.pop("DEEPSEEK_API_KEY", None)
os.environ.pop("DASHSCOPE_API_KEY", None)
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://lifeagent:lifeagent@localhost:5433/lifeagent_test",
)

import httpx
import pytest_asyncio
from sqlalchemy import text

import pytest
from app.core.config import get_settings
from app.infrastructure.database.base import Base
from app.infrastructure.database.session import get_engine, get_session_maker
from app.main import app


@pytest.fixture(scope="session")
def settings():
    return get_settings()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _database() -> None:
    settings = get_settings()
    assert settings.app_env == "test", "tests must run in the test environment"
    engine = get_engine()
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _clean_rows() -> None:
    async with get_session_maker()() as session:
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(text(f'DELETE FROM "{table.name}"'))
        await session.commit()


@pytest_asyncio.fixture
async def client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as async_client:
        yield async_client
