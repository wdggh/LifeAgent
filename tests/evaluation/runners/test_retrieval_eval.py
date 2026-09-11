"""Fast tests for the retrieval evaluation runner (V2.0-06).

No database, Chroma, or DashScope: the evaluate/build-report core is driven
with fake Retriever and fake chunk sources over the real manifest shape.
"""

from __future__ import annotations

from app.agent.tools.search_knowledge import SearchKnowledgeTool
from app.core.config import get_settings
from app.domain.models.llm import ChatMessage, LLMResponse
from app.domain.models.chunk import StoredChunk
from app.domain.models.search_result import SearchResult
from app.infrastructure.llm.base import LLMClient
from app.rag.query.rewriter import QueryRewriter

from tests.evaluation.runners.retrieval_eval import (
    QueryOutcome,
    build_report,
    evaluate_query,
    mark_hard_flags,
)
from app.domain.constants import CHUNKS_PER_ROUND
from app.agent.tools.base import ToolContext
from app.agent.tools.base import ToolResult


def stored(chunk_id: str, start: int, end: int | None = None) -> StoredChunk:
    return StoredChunk(
        chunk_id=chunk_id,
        content="x",
        start_page=start,
        end_page=end if end is not None else start,
        chunk_index=0,
    )


def hit(chunk_id: str, document_id: str, page: int, score: float) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        document_id=document_id,
        document_name=f"{document_id}.pdf",
        content="x",
        score=score,
        start_page=page,
        end_page=page,
    )


class FakeRetriever:
    def __init__(self, results: dict[str, list[SearchResult]]) -> None:
        self.results = results
        self.last_query: str | None = None

    async def search(
        self,
        query: str,
        user_id: str,
        top_k: int,
        document_type: str | None = None,
        document_id: str | None = None,
    ):
        del user_id
        del document_type
        del document_id
        self.last_query = query
        return self.results.get(query, [])[:top_k]


class RecordingTool:
    """Stands in for SearchKnowledgeTool and records how it was called."""

    def __init__(self, results: list[SearchResult]) -> None:
        self.results = results
        self.calls: list[tuple[dict, ToolContext]] = []

    async def run(
        self, arguments: dict, context: ToolContext
    ) -> ToolResult:
        self.calls.append((dict(arguments), context))
        top_k = arguments.get("top_k", 5)
        return ToolResult(
            text="", results=self.results[: int(top_k)]
        )


class FakeChunkSource:
    def __init__(self, chunks: dict[str, list[StoredChunk]]) -> None:
        self.chunks = chunks

    async def fetch_document_chunks(self, document_id: str):
        return self.chunks.get(document_id, [])


REG_001 = {
    "id": "reg-001",
    "schema_version": 2,
    "question": "合同提前退租需要承担多少违约金？",
    "category": "clause_specific",
    "gold": [{"document": "rental_contract_01", "pages": [8]}],
}
REG_002 = {
    "id": "reg-002",
    "schema_version": 2,
    "question": "合同到期后没有按时搬走要承担什么？",
    "category": "clause_specific",
    "gold": [{"document": "rental_contract_01", "pages": [9]}],
}
SLUG_MAP = {"rental_contract_01": "doc_a"}
CHUNKS = {
    "doc_a": [
        stored("rental:p8:c1", 8),
        stored("rental:p9:c1", 9),
    ]
}


async def evaluate(question: str, results: list[SearchResult]):
    query = REG_001 if question == REG_001["question"] else REG_002
    retriever = FakeRetriever({question: results})
    source = FakeChunkSource(CHUNKS)
    return await evaluate_query(
        query_record=query,
        slug_to_document_id=SLUG_MAP,
        retriever=retriever,
        chunk_source=source,
        user_id="eval-user-id",
    )


async def test_regression_pass_and_near_tie_reproduced() -> None:
    # Gold chunks rank first; decoys follow within a 0.05 score gap.
    outcome_1 = await evaluate(
        REG_001["question"],
        [
            hit("rental:p8:c1", "doc_a", page=8, score=0.90),
            hit("rental:p9:c1", "doc_a", page=9, score=0.85),
        ],
    )
    outcome_2 = await evaluate(
        REG_002["question"],
        [
            hit("rental:p9:c1", "doc_a", page=9, score=0.91),
            hit("rental:p8:c1", "doc_a", page=8, score=0.88),
        ],
    )
    report = build_report({"corpus_version": "v1"}, [outcome_1, outcome_2])
    assert report["status"] == "PASS"
    assert report["regression"]["reg-001"]["chunk_recall@5"] == 1.0
    assert report["regression"]["reg-002"]["chunk_recall@5"] == 1.0
    assert report["regression"]["reg-001"]["dense_score_gap"] < 0.1
    assert report["regression"]["reg-001"]["near_tie_reproduced"] is True
    assert report["metrics"]["chunk"]["mrr@5"] == 1.0


async def test_regression_gate_fails_when_gold_outside_top5() -> None:
    decoys = [
        hit(f"other:{index}", "other_doc", page=1, score=0.99 - index / 100)
        for index in range(5)
    ]
    outcome = await evaluate(
        REG_001["question"],
        decoys + [hit("rental:p8:c1", "doc_a", page=8, score=0.50)],
    )
    report = build_report({"corpus_version": "v1"}, [outcome])
    assert report["status"] == "FAIL"
    assert report["regression"]["reg-001"]["pass"] is False
    assert report["regression"]["reg-001"]["chunk_recall@5"] == 0.0


async def test_missing_decoy_gap_is_diagnostic_only() -> None:
    outcome = await evaluate(
        REG_001["question"],
        [hit("rental:p8:c1", "doc_a", page=8, score=0.90)],
    )
    report = build_report({"corpus_version": "v1"}, [outcome])
    assert report["status"] == "PASS"  # gate is recall, not the score gap
    assert report["regression"]["reg-001"]["dense_score_gap"] is None
    assert report["regression"]["reg-001"]["near_tie_reproduced"] is None


def test_mark_hard_flags(tmp_path) -> None:
    import json

    queries_path = tmp_path / "queries.jsonl"
    queries_path.write_text(
        "\n".join(
            json.dumps(record, ensure_ascii=False)
            for record in [
                {
                    "id": "v2-001",
                    "hard_candidate": True,
                    "question": "q1",
                },
                {
                    "id": "v2-002",
                    "hard_candidate": True,
                    "question": "q2",
                },
                {
                    "id": "v2-003",
                    "hard_candidate": False,
                    "question": "q3",
                },
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    qualifying = QueryOutcome(
        query_id="v2-001",
        category="semantic_rewrite",
        metrics={"chunk": {"mrr@5": 0.5, "ndcg@5": 0.9}},
        chunk_recall5=1.0,
        dense_gap=0.2,
        near_tie_reproduced=False,
        hard_candidate=True,
    )
    easy_under_construction = QueryOutcome(
        query_id="v2-002",
        category="semantic_rewrite",
        metrics={"chunk": {"mrr@5": 1.0, "ndcg@5": 1.0}},
        chunk_recall5=1.0,
        dense_gap=0.3,
        near_tie_reproduced=False,
        hard_candidate=True,
    )
    counts = mark_hard_flags(
        queries_path, [qualifying, easy_under_construction]
    )
    assert counts == {"hard": 1, "easy_under_construction": 1}
    records = {
        json.loads(line)["id"]: json.loads(line)
        for line in queries_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    assert records["v2-001"]["hard"] is True
    assert records["v2-002"]["hard"] is False
    assert records["v2-003"]["hard"] is False


class RewriteOnlyLLM(LLMClient):
    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        return LLMResponse(content="提前退租 违约金 一个月租金")


async def test_evaluate_query_via_search_tool_uses_rewritten_query(
    monkeypatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "query_rewrite_enabled", True, raising=False)
    retriever = FakeRetriever(
        {
            "提前退租 违约金 一个月租金": [
                hit("rental:p8:c1", "doc_a", page=8, score=0.9),
                hit("rental:p9:c1", "doc_a", page=9, score=0.85),
            ]
        }
    )
    tool = SearchKnowledgeTool(
        retriever,  # type: ignore[arg-type]
        query_rewriter=QueryRewriter(RewriteOnlyLLM(), settings),
    )
    outcome = await evaluate_query(
        query_record=REG_001,
        slug_to_document_id=SLUG_MAP,
        retriever=retriever,
        chunk_source=FakeChunkSource(CHUNKS),
        user_id="eval-user-id",
        search_tool=tool,
    )
    assert retriever.last_query == "提前退租 违约金 一个月租金"
    assert outcome.metadata["rewrite_fallback"] is False
    assert outcome.metadata["query_rewritten"] == "提前退租 违约金 一个月租金"
    assert outcome.chunk_recall5 == 1.0


async def test_agent_budget_mode_uses_the_production_consumption_set() -> None:
    """Gold at rank 5 is a capability hit but NOT agent context."""

    wide = [
        hit(f"other:p1:c{index}", "other_doc", page=1, score=0.9 - index / 100)
        for index in range(4)
    ] + [hit("rental:p8:c9", "doc_a", page=8, score=0.4)]
    tool = RecordingTool(wide)
    outcome = await evaluate_query(
        query_record=REG_001,
        slug_to_document_id=SLUG_MAP,
        retriever=FakeRetriever({}),
        chunk_source=FakeChunkSource(CHUNKS),
        user_id="eval-user-id",
        search_tool=tool,
        agent_budget=True,
    )
    arguments, context = tool.calls[0]
    assert arguments["top_k"] == CHUNKS_PER_ROUND
    assert context.remaining_chunk_budget == CHUNKS_PER_ROUND
    assert outcome.context_recall is False
    assert outcome.context_chunk_ids == [
        f"other:p1:c{index}" for index in range(4)
    ]


async def test_agent_budget_mode_hits_when_gold_is_consumed() -> None:
    results = [
        hit("rental:p8:c1", "doc_a", page=8, score=0.9),
        hit("rental:p8:c2", "doc_a", page=8, score=0.8),
    ]
    outcome = await evaluate_query(
        query_record=REG_001,
        slug_to_document_id=SLUG_MAP,
        retriever=FakeRetriever({}),
        chunk_source=FakeChunkSource(CHUNKS),
        user_id="eval-user-id",
        search_tool=RecordingTool(results),
        agent_budget=True,
    )
    assert outcome.context_recall is True


async def test_capability_mode_leaves_agent_context_unmeasured() -> None:
    outcome = await evaluate_query(
        query_record=REG_001,
        slug_to_document_id=SLUG_MAP,
        retriever=FakeRetriever({}),
        chunk_source=FakeChunkSource(CHUNKS),
        user_id="eval-user-id",
        search_tool=RecordingTool(
            [hit("rental:p8:c1", "doc_a", page=8, score=0.9)]
        ),
    )
    assert outcome.context_recall is None
    report = build_report({"corpus_version": "v1"}, [outcome])
    assert report["agent_context"] is None


def test_report_exposes_agent_context_recall_by_difficulty() -> None:
    def outcome(query_id: str, hard: bool, context_recall: bool) -> QueryOutcome:
        return QueryOutcome(
            query_id=query_id,
            category="clause",
            metrics=None,
            chunk_recall5=1.0,
            dense_gap=None,
            near_tie_reproduced=None,
            hard=hard,
            context_recall=context_recall,
        )

    report = build_report(
        {"corpus_version": "v1"},
        [
            outcome("v2-001", True, True),
            outcome("v2-002", True, False),
            outcome("v2-003", False, True),
        ],
        agent_budget=True,
    )
    block = report["agent_context"]
    assert block["mode"] == "agent_budget"
    assert block["k"] == CHUNKS_PER_ROUND
    assert block["recall@4"] == 0.6667
    assert block["by_difficulty"]["hard"]["recall@4"] == 0.5
    assert block["by_difficulty"]["easy"]["recall@4"] == 1.0
