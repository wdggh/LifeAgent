"""Shared test harness.

Conventions established by ticket 01:
- Tests run with APP_ENV=test and never touch real provider keys.
- The primary seam is the public HTTP API via FastAPI TestClient.
- Later tickets plug isolated PostgreSQL / Chroma instances and Fake
  LLM/Embedding clients into this harness.
"""

import os

os.environ["APP_ENV"] = "test"
os.environ.pop("DEEPSEEK_API_KEY", None)
os.environ.pop("DASHSCOPE_API_KEY", None)
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://lifeagent:lifeagent@localhost:5432/lifeagent_test",
)

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def settings() -> Settings:
    return get_settings()
