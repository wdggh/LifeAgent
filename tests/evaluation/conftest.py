"""Fast-mode overrides for tests/evaluation.

Evaluation unit tests (gold mapping, dataset validation, metrics) must run
without PostgreSQL / Chroma / Redis / external providers. These no-op fixtures
shadow the session/function autouse database fixtures from ``tests/conftest.py``
for this subtree only; the full-stack tests outside this directory are
unaffected.
"""

import pytest


@pytest.fixture(scope="session", autouse=True)
def _database() -> None:
    yield


@pytest.fixture(autouse=True)
def _clean_rows() -> None:
    yield
