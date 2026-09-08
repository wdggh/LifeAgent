"""Real ingestion & isolated evaluation harness (V2.0-05).

Live mode needs only PostgreSQL + Chroma + the configured embedding provider
(DashScope) and deliberately avoids Redis, the ARQ worker, and FastAPI: the
real ingestion pipeline (DocumentService.upload -> KnowledgeService.ingest,
which runs parse -> chunk -> embed -> index) is called directly.

Isolation:
- a dedicated ``eval_user`` owns all evaluation Documents;
- Chroma runs against an isolated collection named ``<base>_eval``;
- ``--reset`` drops/recreates that collection and deletes the eval user's
  Documents (rows + files) so a run is repeatable and idempotent.

The harness is seam-injectable so fast unit tests exercise the same
orchestration with fakes (no database, no Chroma, no network).

Run from the repository root:
    python -m tests.evaluation.runners.ingest_corpus --reset
"""

from __future__ import annotations

import argparse
import json
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.domain.constants import DocumentStatus
from app.domain.entities.user import User
from app.infrastructure.database.document_repository import (
    SQLAlchemyDocumentRepository,
)
from app.infrastructure.database.session import get_session_maker
from app.infrastructure.database.user_repository import SQLAlchemyUserRepository
from app.infrastructure.embedding.factory import get_embedding_client
from app.infrastructure.storage.local_storage import LocalFileStorage
from app.infrastructure.vector_store.chroma import (
    ChromaVectorRepository,
    reset_collection,
)
from app.repositories.vector_repository import VectorRepository
from app.services.document_service import DocumentService
from app.services.knowledge_service import KnowledgeService
from app.services.user_service import UserService

EVAL_USERNAME = "eval_user"
EVAL_PASSWORD = "eval-password-2026"
LIST_PAGE_SIZE = 100


def eval_collection_name(base: str) -> str:
    """Isolated Chroma collection for the live evaluation run."""

    return f"{base}_eval"


@dataclass(frozen=True)
class IngestionDeps:
    documents: DocumentService
    knowledge: KnowledgeService
    vectors: VectorRepository
    users: UserService


class CorpusIngestionHarness:
    """Orchestrates corpus upload + ingestion under one eval user."""

    def __init__(self, deps: IngestionDeps) -> None:
        self._deps = deps

    @property
    def vectors(self) -> VectorRepository:
        return self._deps.vectors

    async def ensure_eval_user(self) -> User:
        try:
            return await self._deps.users.authenticate(
                EVAL_USERNAME, EVAL_PASSWORD
            )
        except AppError as exc:
            if exc.status_code != 401:
                raise
            return await self._deps.users.register(
                EVAL_USERNAME, EVAL_PASSWORD
            )

    async def reset_eval_documents(self, user_id: str) -> None:
        """Delete every Document of the eval user (rows + files + vectors)."""

        page = 1
        while True:
            documents = await self._deps.documents.list_documents(
                user_id, page, LIST_PAGE_SIZE
            )
            for document in documents:
                await self._deps.documents.delete_document(
                    document.id, user_id
                )
            if len(documents) < LIST_PAGE_SIZE:
                break
            page += 1

    async def ingest_entry(
        self,
        user: User,
        entry: dict[str, Any],
        fixtures_root: Path,
    ) -> str:
        source = fixtures_root / entry["file"]
        if not source.exists():
            raise AssertionError(
                f"{entry['slug']}: fixture file missing: {source}"
            )
        document = await self._deps.documents.upload(
            user.id,
            source.name,
            entry["document_type"],
            source.read_bytes(),
        )
        completed = await self._deps.knowledge.ingest(document.id)
        if completed is None or completed.status != DocumentStatus.COMPLETED:
            raise AssertionError(
                f"{entry['slug']}: ingestion did not complete "
                f"(status={getattr(completed, 'status', None)})"
            )
        chunks = await self._deps.vectors.fetch_document_chunks(completed.id)
        self._verify_coverage(entry, chunks)
        return completed.id

    async def ingest_corpus(
        self,
        manifest: dict[str, Any],
        fixtures_root: Path,
        *,
        reset_documents: bool = False,
    ) -> dict[str, str]:
        """Ingest every corpus document; return slug -> document id."""

        user = await self.ensure_eval_user()
        if reset_documents:
            await self.reset_eval_documents(user.id)
        mapping: dict[str, str] = {}
        for entry in manifest["documents"]:
            mapping[entry["slug"]] = await self.ingest_entry(
                user, entry, fixtures_root
            )
        return mapping

    @staticmethod
    def _verify_coverage(entry: dict[str, Any], chunks: list) -> None:
        expected = set(range(1, int(entry["pages"]) + 1))
        covered: set[int] = set()
        for stored in chunks:
            covered.update(range(stored.start_page, stored.end_page + 1))
        if covered != expected:
            raise AssertionError(
                f"{entry['slug']}: page coverage mismatch after ingestion: "
                f"expected {sorted(expected)}, got {sorted(covered)}"
            )


@asynccontextmanager
async def live_harness(
    *,
    reset: bool = False,
) -> AsyncIterator[CorpusIngestionHarness]:
    """Build a harness against the real stack in the ``_eval`` collection."""

    settings = get_settings()
    original_collection = settings.chroma_collection
    settings.chroma_collection = eval_collection_name(original_collection)
    if reset:
        reset_collection(settings.chroma_collection)
    try:
        async with get_session_maker()() as session:
            vectors = ChromaVectorRepository()
            document_repository = SQLAlchemyDocumentRepository(session)
            deps = IngestionDeps(
                documents=DocumentService(
                    document_repository, LocalFileStorage(), vectors
                ),
                knowledge=KnowledgeService(
                    document_repository,
                    get_embedding_client(),
                    vectors,
                    LocalFileStorage(),
                ),
                vectors=vectors,
                users=UserService(SQLAlchemyUserRepository(session)),
            )
            yield CorpusIngestionHarness(deps)
    finally:
        settings.chroma_collection = original_collection


def _default_fixtures() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures"


async def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        default=str(_default_fixtures() / "corpus" / "manifest.json"),
    )
    parser.add_argument("--fixtures", default=str(_default_fixtures()))
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    async with live_harness(reset=args.reset) as harness:
        mapping = await harness.ingest_corpus(
            manifest,
            Path(args.fixtures),
            reset_documents=args.reset,
        )
    print(
        json.dumps(
            {"collection": eval_collection_name(get_settings().chroma_collection),
             "mapping": mapping},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    import asyncio

    raise SystemExit(asyncio.run(_main()))
