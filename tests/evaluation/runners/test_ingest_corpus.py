"""Fast unit tests for the corpus ingestion harness (V2.0-05).

No database, Chroma, Redis, or DashScope: the harness is driven with fake
Document/Knowledge/Vector/User services through the real manifest.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.exceptions import AppError
from app.domain.constants import DocumentStatus

from tests.evaluation.runners.ingest_corpus import (
    CorpusIngestionHarness,
    IngestionDeps,
    eval_collection_name,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
MANIFEST = json.loads(
    (FIXTURES / "corpus" / "manifest.json").read_text(encoding="utf-8")
)


class FakeUsers:
    def __init__(self, exists: bool = False) -> None:
        self.exists = exists
        self.register_calls = 0

    async def authenticate(self, username: str, password: str):
        if self.exists:
            return SimpleNamespace(id="eval-user-id", username=username)
        raise AppError(401, "INVALID_CREDENTIALS", "not registered")

    async def register(self, username: str, password: str):
        self.register_calls += 1
        self.exists = True
        return SimpleNamespace(id="eval-user-id", username=username)


class FakeDocuments:
    def __init__(self) -> None:
        self.documents: dict[str, SimpleNamespace] = {}
        self.deleted: list[str] = []

    async def upload(
        self,
        user_id: str,
        filename: str,
        document_type: str,
        content: bytes,
    ):
        document_id = f"doc-{filename}"
        document = SimpleNamespace(
            id=document_id,
            user_id=user_id,
            filename=filename,
            document_type=document_type,
            status=DocumentStatus.UPLOADED,
        )
        self.documents[document_id] = document
        return document

    async def list_documents(
        self, user_id: str, page: int, page_size: int
    ) -> list:
        return list(self.documents.values())

    async def delete_document(self, document_id: str, user_id: str) -> None:
        self.documents.pop(document_id, None)
        self.deleted.append(document_id)


class FakeKnowledge:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.ingested: list[str] = []

    async def ingest(self, document_id: str):
        self.ingested.append(document_id)
        status = DocumentStatus.FAILED if self.fail else DocumentStatus.COMPLETED
        return SimpleNamespace(id=document_id, status=status)


class FakeVectors:
    def __init__(self, page_maps: dict[str, list[int]] | None = None) -> None:
        self.page_maps = page_maps or {}

    async def fetch_document_chunks(self, document_id: str):
        key = Path(document_id.removeprefix("doc-")).stem
        pages = self.page_maps.get(key, [])
        return [
            SimpleNamespace(
                chunk_id=f"{key}:p{page}",
                content="fake",
                start_page=page,
                end_page=page,
                chunk_index=index,
            )
            for index, page in enumerate(pages)
        ]


def build_harness(
    fake_users: FakeUsers | None = None,
    fake_documents: FakeDocuments | None = None,
    fake_knowledge: FakeKnowledge | None = None,
    fake_vectors: FakeVectors | None = None,
) -> CorpusIngestionHarness:
    return CorpusIngestionHarness(
        IngestionDeps(
            documents=fake_documents or FakeDocuments(),
            knowledge=fake_knowledge or FakeKnowledge(),
            vectors=fake_vectors or FakeVectors(),
            users=fake_users or FakeUsers(),
        )
    )


def page_maps_for(entries: list[dict]) -> dict[str, list[int]]:
    return {
        entry["slug"]: list(range(1, int(entry["pages"]) + 1))
        for entry in entries
    }


def test_eval_collection_name() -> None:
    assert (
        eval_collection_name("lifeagent_text-embedding-v3_1024")
        == "lifeagent_text-embedding-v3_1024_eval"
    )


async def test_ensure_eval_user_registers_then_reuses() -> None:
    users = FakeUsers(exists=False)
    harness = build_harness(fake_users=users)
    first = await harness.ensure_eval_user()
    second = await harness.ensure_eval_user()
    assert first.id == "eval-user-id" and second.id == "eval-user-id"
    assert users.register_calls == 1


async def test_ingest_corpus_maps_slugs_and_verifies_coverage() -> None:
    entries = MANIFEST["documents"][:2]  # rental PDF + insurance PDF
    users = FakeUsers(exists=True)
    documents = FakeDocuments()
    knowledge = FakeKnowledge()
    vectors = FakeVectors(page_maps_for(entries))
    harness = build_harness(
        fake_users=users,
        fake_documents=documents,
        fake_knowledge=knowledge,
        fake_vectors=vectors,
    )
    mapping = await harness.ingest_corpus(
        {"documents": entries}, FIXTURES
    )
    assert mapping == {
        entry["slug"]: f"doc-{Path(entry['file']).name}"
        for entry in entries
    }
    assert len(knowledge.ingested) == len(entries)


async def test_coverage_mismatch_raises() -> None:
    entry = next(
        doc for doc in MANIFEST["documents"] if doc["slug"] == "rental_contract_01"
    )
    vectors = FakeVectors(
        {entry["slug"]: list(range(1, int(entry["pages"])))}  # page 9 missing
    )
    harness = build_harness(fake_vectors=vectors)
    with pytest.raises(AssertionError, match="coverage mismatch"):
        await harness.ingest_corpus({"documents": [entry]}, FIXTURES)


async def test_failed_ingestion_raises() -> None:
    entry = MANIFEST["documents"][0]
    harness = build_harness(fake_knowledge=FakeKnowledge(fail=True))
    with pytest.raises(AssertionError, match="did not complete"):
        await harness.ingest_corpus({"documents": [entry]}, FIXTURES)


async def test_reset_eval_documents_deletes_all() -> None:
    documents = FakeDocuments()
    await documents.upload("eval-user-id", "a.md", "note", b"a")
    await documents.upload("eval-user-id", "b.pdf", "manual", b"%PDF")
    harness = build_harness(fake_documents=documents)
    await harness.reset_eval_documents("eval-user-id")
    assert len(documents.deleted) == 2
    assert documents.documents == {}


def test_manifest_fixture_files_exist() -> None:
    for entry in MANIFEST["documents"]:
        assert (FIXTURES / entry["file"]).exists(), entry["file"]
