"""V2.3 sparse/BM25 hybrid retrieval tests (ADR-0011)."""

from types import SimpleNamespace

from app.agent.tools.base import ToolContext
from app.agent.tools.search_knowledge import SearchKnowledgeTool
from app.core.config import get_settings
from app.domain.models.chunk import StoredChunk
from app.domain.models.search_result import SearchResult
from app.rag.retrieval.sparse import (
    BM25Index,
    BM25SparseSearcher,
    RedisCorpusVersionStore,
    SparseEntry,
    SparseIndexError,
    SparseSearchOutcome,
    tokenize,
)
from app.rag.retrieval.fusion import (
    dense_priority_supplement,
    reciprocal_rank_fusion,
    reserved_slot_allocation,
)


class FakeDocumentSource:
    def __init__(self, documents: dict[str, list[SimpleNamespace]]) -> None:
        self.documents = documents
        self.calls = 0

    async def list_documents(self, user_id: str, page: int, size: int):
        self.calls += 1
        return self.documents.get(user_id, [])


class FakeVectorRepository:
    def __init__(self, chunks: dict[str, list[StoredChunk]]) -> None:
        self.chunks = chunks

    async def fetch_document_chunks(self, document_id: str):
        return self.chunks.get(document_id, [])


class FakeVersionStore:
    def __init__(self, initial: int | None = 1) -> None:
        self.version = initial

    async def current(self, user_id: str) -> int | None:
        return self.version

    async def bump(self, user_id: str) -> int | None:
        if self.version is not None:
            self.version += 1
        return self.version


def stored(chunk_id: str, content: str, page: int = 1) -> StoredChunk:
    return StoredChunk(
        chunk_id=chunk_id,
        content=content,
        start_page=page,
        end_page=page,
        chunk_index=0,
    )


def entry(
    chunk_id: str,
    content: str,
    document_id: str = "doc_1",
    document_type: str = "contract",
) -> SparseEntry:
    return SparseEntry(
        chunk_id=chunk_id,
        content=content,
        document_id=document_id,
        document_name=f"{document_id}.pdf",
        document_type=document_type,
        start_page=1,
        end_page=1,
        chunk_index=0,
        tokens=tokenize(content),
    )


def result(chunk_id: str, score: float = 0.9) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        document_id="doc_1",
        document_name="doc_1.pdf",
        content="content",
        score=score,
    )


class FakeSparseSearcher:
    def __init__(
        self,
        results: list[SearchResult] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.results = results or []
        self.error = error
        self.calls: list[dict] = []

    async def search(self, **kwargs) -> SparseSearchOutcome:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return SparseSearchOutcome(
            results=self.results,
            index_version=1,
            rebuild_ms=3.5,
            cache_hit=False,
        )


class FakeDenseRetriever:
    def __init__(self, results: list[SearchResult]) -> None:
        self.results = results
        self.calls: list[dict] = []

    async def search(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        document_type: str | None = None,
        document_id: str | None = None,
    ) -> list[SearchResult]:
        self.calls.append({"query": query, "top_k": top_k})
        return self.results[:top_k]


def test_tokenize_keeps_identifiers_and_chinese_terms() -> None:
    tokens = tokenize("订单 PO-2025-0099 七天无理由退货 4500元")
    assert "po-2025-0099" in tokens
    assert "4500" in tokens
    assert "退货" in tokens


def test_bm25_index_prefers_lexical_match_and_filters() -> None:
    index = BM25Index(
        [
            entry("warranty", "整机保修期为二十四个月", document_id="w"),
            entry("returns", "签收之日起七日内可无理由退货", document_id="r"),
        ],
        k1=1.5,
        b=0.75,
    )
    results = index.search("七天无理由退货", top_k=5)
    assert [r.document_id for r in results][:1] == ["r"]

    filtered = index.search("七天无理由退货", top_k=5, document_id="w")
    assert filtered == []


async def test_sparse_searcher_isolates_users_and_caches() -> None:
    documents = {
        "user_a": [SimpleNamespace(id="a1", filename="a.pdf", document_type="note")],
        "user_b": [SimpleNamespace(id="b1", filename="b.pdf", document_type="note")],
    }
    source = FakeDocumentSource(documents)
    vectors = FakeVectorRepository(
        {
            "a1": [stored("a1:c1", "七天无理由退货")],
            "b1": [stored("b1:c1", "整机保修二十四个月")],
        }
    )
    searcher = BM25SparseSearcher(
        document_source=source,
        vector_repository_provider=lambda: vectors,
        version_store=FakeVersionStore(1),
        settings=get_settings(),
    )
    first = await searcher.search(
        user_id="user_a", query="七天退货", top_k=5
    )
    assert first.results[0].chunk_id == "a1:c1"
    second = await searcher.search(
        user_id="user_a", query="七天退货", top_k=5
    )
    assert second.cache_hit is True
    assert source.calls == 1  # cached, no rebuild

    other = await searcher.search(
        user_id="user_b", query="保修", top_k=5
    )
    assert other.results[0].chunk_id == "b1:c1"
    assert source.calls == 2


async def test_sparse_index_rebuilds_when_version_changes() -> None:
    source = FakeDocumentSource(
        {
            "u": [
                SimpleNamespace(
                    id="d1", filename="d.pdf", document_type="note"
                )
            ]
        }
    )
    vectors = FakeVectorRepository({"d1": [stored("d1:c1", "保修")]})
    versions = FakeVersionStore(1)
    searcher = BM25SparseSearcher(
        document_source=source,
        vector_repository_provider=lambda: vectors,
        version_store=versions,
        settings=get_settings(),
    )
    first = await searcher.search(user_id="u", query="保修", top_k=5)
    assert first.cache_hit is False
    await versions.bump("u")
    second = await searcher.search(user_id="u", query="保修", top_k=5)
    assert second.cache_hit is False
    assert source.calls == 2


async def test_sparse_index_ttl_fallback_when_version_unavailable() -> None:
    source = FakeDocumentSource(
        {
            "u": [
                SimpleNamespace(
                    id="d1", filename="d.pdf", document_type="note"
                )
            ]
        }
    )
    vectors = FakeVectorRepository({"d1": [stored("d1:c1", "保修")]})
    settings = get_settings()
    searcher = BM25SparseSearcher(
        document_source=source,
        vector_repository_provider=lambda: vectors,
        version_store=FakeVersionStore(None),
        settings=settings,
    )
    searcher._settings.query_sparse_version_ttl_seconds = 0  # type: ignore[attr-defined]
    await searcher.search(user_id="u", query="保修", top_k=5)
    await searcher.search(user_id="u", query="保修", top_k=5)
    assert source.calls == 2  # TTL 0 forces rebuild when version unknown


async def test_tool_hybrid_fuses_dense_and_sparse(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "query_sparse_enabled", True)
    monkeypatch.setattr(settings, "query_sparse_candidate_k", 8)
    monkeypatch.setattr(settings, "query_sparse_rrf_k", 60)
    dense = FakeDenseRetriever([result("dense_hit")])
    sparse = FakeSparseSearcher([result("sparse_hit")])
    tool = SearchKnowledgeTool(
        dense,  # type: ignore[arg-type]
        sparse_searcher=sparse,  # type: ignore[arg-type]
    )
    outcome = await tool.run(
        {"query": "七天退货"},
        ToolContext("user_1", remaining_chunk_budget=10),
    )
    assert [r.chunk_id for r in outcome.results] == [
        "dense_hit",
        "sparse_hit",
    ]
    metadata = outcome.metadata
    assert metadata["dense_hit_ids"] == ["dense_hit"]
    assert metadata["sparse_hit_ids"] == ["sparse_hit"]
    assert metadata["per_channel_hits"] == [1, 1]
    assert metadata["rrf_k"] == 60
    assert metadata["sparse_fallback"] is False


async def test_tool_sparse_failure_falls_back_to_dense(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "query_sparse_enabled", True)
    dense = FakeDenseRetriever([result("dense_hit")])
    sparse = FakeSparseSearcher(error=SparseIndexError("index down"))
    tool = SearchKnowledgeTool(
        dense,  # type: ignore[arg-type]
        sparse_searcher=sparse,  # type: ignore[arg-type]
    )
    outcome = await tool.run(
        {"query": "七天退货"},
        ToolContext("user_1", remaining_chunk_budget=10),
    )
    assert [r.chunk_id for r in outcome.results] == ["dense_hit"]
    assert outcome.metadata["sparse_fallback"] is True
    assert outcome.metadata["sparse_fallback_reason"] == "SparseIndexError"


async def test_tool_sparse_disabled_equals_baseline(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "query_sparse_enabled", False)
    dense = FakeDenseRetriever([result("dense_hit")])
    sparse = FakeSparseSearcher([result("sparse_hit")])
    tool = SearchKnowledgeTool(
        dense,  # type: ignore[arg-type]
        sparse_searcher=sparse,  # type: ignore[arg-type]
    )
    outcome = await tool.run(
        {"query": "七天退货"},
        ToolContext("user_1", remaining_chunk_budget=10),
    )
    assert [r.chunk_id for r in outcome.results] == ["dense_hit"]
    assert outcome.metadata == {}
    assert sparse.calls == []


def test_dense_priority_supplement_never_reorders_dense() -> None:
    outcome = dense_priority_supplement(
        [result("a"), result("b"), result("c")],
        [result("c"), result("d"), result("e")],
        limit=4,
    )
    assert [r.chunk_id for r in outcome.results] == ["a", "b", "c", "d"]
    assert outcome.candidate_count == 5


def test_weighted_rrf_protects_dense_rank_one() -> None:
    outcome = reciprocal_rank_fusion(
        [[result("correct")], [result("wrong")]],
        k=60,
        weights=[2.0, 1.0],
        original_tie_break=True,
    )
    assert [r.chunk_id for r in outcome.results] == ["correct", "wrong"]
    assert outcome.scores["correct"] > outcome.scores["wrong"]


async def test_tool_uses_configured_fusion_mode(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "query_sparse_enabled", True)
    monkeypatch.setattr(settings, "query_sparse_fusion_mode", "dense_priority")
    dense = FakeDenseRetriever([result("dense_hit")])
    sparse = FakeSparseSearcher([result("sparse_hit")])
    tool = SearchKnowledgeTool(
        dense,  # type: ignore[arg-type]
        sparse_searcher=sparse,  # type: ignore[arg-type]
    )
    outcome = await tool.run(
        {"query": "七天退货"},
        ToolContext("user_1", remaining_chunk_budget=10),
    )
    assert outcome.metadata["fusion_mode"] == "dense_priority"
    assert [r.chunk_id for r in outcome.results] == [
        "dense_hit",
        "sparse_hit",
    ]

    monkeypatch.setattr(settings, "query_sparse_fusion_mode", "weighted_rrf")
    outcome = await tool.run(
        {"query": "七天退货"},
        ToolContext("user_1", remaining_chunk_budget=10),
    )
    assert outcome.metadata["fusion_mode"] == "weighted_rrf"
    assert [r.chunk_id for r in outcome.results] == [
        "dense_hit",
        "sparse_hit",
    ]


def test_reserved_slot_ignores_unselected_dense_candidates() -> None:
    outcome = reserved_slot_allocation(
        [result("d1"), result("d2"), result("d3"), result("d4")],
        [result("d4"), result("s1"), result("s2")],
        limit=4,
        reserved_slots=1,
    )
    assert [r.chunk_id for r in outcome.results] == ["d1", "d2", "d3", "s1"]
    assert outcome.reserved_chunk_id == "s1"
    assert outcome.reserved_sparse_rank == 2  # d4 was skipped (dense candidate)
    assert outcome.dense_slot_count == 3
    assert outcome.sparse_slot_count == 1
    assert outcome.fallback_reason is None


def test_reserved_slot_falls_back_when_no_true_sparse_only_chunk() -> None:
    outcome = reserved_slot_allocation(
        [result("d1"), result("d2"), result("d3"), result("d4")],
        [result("d2"), result("d3")],
        limit=4,
        reserved_slots=1,
    )
    assert [r.chunk_id for r in outcome.results] == [
        "d1",
        "d2",
        "d3",
        "d4",
    ]
    assert outcome.reserved_chunk_id is None
    assert outcome.fallback_reason == "no_sparse_only_chunk"


def test_reserved_slot_respects_limit_and_dedupe() -> None:
    dense = [result(f"d{i}") for i in range(1, 9)]
    sparse = [result("d8"), result("s1"), result("s2")]
    outcome = reserved_slot_allocation(
        dense, sparse, limit=10, reserved_slots=1
    )
    ids = [r.chunk_id for r in outcome.results]
    assert len(ids) == 10
    assert len(set(ids)) == 10
    assert ids[:8] == [f"d{i}" for i in range(1, 9)]
    assert ids[8] == "s1"


async def test_tool_reserved_slot_metadata(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "query_sparse_enabled", True)
    monkeypatch.setattr(settings, "query_sparse_fusion_mode", "reserved_slot")
    monkeypatch.setattr(settings, "query_sparse_reserved_slots", 1)
    dense = FakeDenseRetriever(
        [result("d1"), result("d2"), result("d3"), result("d4")]
    )
    sparse = FakeSparseSearcher([result("d4"), result("s1")])
    tool = SearchKnowledgeTool(
        dense,  # type: ignore[arg-type]
        sparse_searcher=sparse,  # type: ignore[arg-type]
    )
    outcome = await tool.run(
        {"query": "七天退货"},
        ToolContext("user_1", remaining_chunk_budget=4),
    )
    assert [r.chunk_id for r in outcome.results] == [
        "d1",
        "d2",
        "d3",
        "s1",
    ]
    metadata = outcome.metadata
    assert metadata["slot_policy"] == "reserved_slot"
    assert metadata["reserved_slot_chunk_id"] == "s1"
    assert metadata["reserved_slot_sparse_rank"] == 2
    assert metadata["dense_slot_count"] == 3
    assert metadata["sparse_slot_count"] == 1
    assert metadata["reserved_slot_fallback_reason"] is None
