"""Fast tests for the retrieval evaluation runner (V2.0-06).

No database, Chroma, or DashScope: the evaluate/build-report core is driven
with fake Retriever and fake chunk sources over the real manifest shape.
"""

from __future__ import annotations

from app.domain.models.chunk import StoredChunk
from app.domain.models.search_result import SearchResult

from tests.evaluation.runners.retrieval_eval import (
    QueryOutcome,
    build_report,
    evaluate_query,
    mark_hard_flags,
)


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

    async def search(self, query: str, user_id: str, top_k: int):
        del user_id
        return self.results.get(query, [])[:top_k]


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
