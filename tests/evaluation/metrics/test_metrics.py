"""Unit tests for evaluation metrics (V2.0-04).

Fast mode: pure functions over fake SearchResult / flags; no Chroma,
DashScope, or database. Gold mapping (V2.0-03) feeds chunk ids in here.
"""

import pytest

from app.domain.models.search_result import SearchResult

from tests.evaluation.metrics.aggregate import (
    aggregate_by_category,
    average_metrics,
)
from tests.evaluation.metrics.levels import compute_query_metrics
from tests.evaluation.metrics.mrr import reciprocal_rank_at_k
from tests.evaluation.metrics.ndcg import ndcg_at_k
from tests.evaluation.metrics.recall import recall_at_k


def result(
    chunk_id: str,
    document_id: str,
    start_page: int,
    end_page: int | None = None,
) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        document_id=document_id,
        document_name=f"{document_id}.pdf",
        content="fake content",
        score=0.9,
        start_page=start_page,
        end_page=end_page if end_page is not None else start_page,
    )


def test_recall_at_k_basic() -> None:
    flags = [False, True, False]
    assert recall_at_k(flags, gold_total=2, k=5) == 0.5
    assert recall_at_k(flags, gold_total=2, k=1) == 0.0
    with pytest.raises(ValueError):
        recall_at_k(flags, gold_total=0, k=5)


def test_reciprocal_rank_at_k_basic() -> None:
    assert reciprocal_rank_at_k([False, True, True], k=5) == 0.5
    assert reciprocal_rank_at_k([False, False], k=5) == 0.0
    # Relevant result at rank 6 is out of MRR@5 but visible at K=10.
    flags = [False] * 5 + [True]
    assert reciprocal_rank_at_k(flags, k=5) == 0.0
    assert reciprocal_rank_at_k(flags, k=10) == 1.0 / 6


def test_ndcg_at_k_binary_and_saturation() -> None:
    # Gains [0,1,0,1]: DCG = 1/log2(3) + 1/log2(5).
    dcg = 1 / __import__("math").log2(3) + 1 / __import__("math").log2(5)
    idcg = 1.0 + 1 / __import__("math").log2(3)
    assert ndcg_at_k([0, 1, 0, 1], k=5) == pytest.approx(dcg / idcg)

    # 3 gold chunks, only the first of 5 retrieved -> NDCG well below 1.
    ideal = 1.0 + 1 / __import__("math").log2(3) + 0.5
    assert ndcg_at_k([1, 0, 0, 0, 0], k=5, gold_total=3) == pytest.approx(
        1.0 / ideal
    )
    assert ndcg_at_k([], k=5, gold_total=3) == 0.0


def test_levels_document_page_chunk_projection() -> None:
    gold_document = "docA"
    gold_chunks = {"a8c1", "a8c2"}
    results = [
        result("b8", "docB", start_page=8),
        result("a9c1", gold_document, start_page=9),
        result("a8c1", gold_document, start_page=8),
        result("a8c2", gold_document, start_page=8),
    ]
    metrics = compute_query_metrics(
        results,
        gold_document_id=gold_document,
        gold_pages=[8],
        gold_chunk_ids=sorted(gold_chunks),
    )
    assert metrics is not None

    # document: first docA chunk at rank 2 -> MRR 0.5; recall@5 = 1.
    assert metrics["document"]["mrr@5"] == 0.5
    assert metrics["document"]["recall@5"] == 1.0
    assert metrics["document"]["ndcg@5"] == pytest.approx(
        1 / __import__("math").log2(3)
    )

    # page: first page-8 chunk at rank 3 -> MRR 1/3; page coverage recall = 1.
    assert metrics["page"]["mrr@5"] == pytest.approx(1.0 / 3)
    assert metrics["page"]["recall@5"] == 1.0
    assert metrics["page"]["ndcg@5"] == pytest.approx(1.0)

    # chunk: both gold chunks found at ranks 3 and 4.
    assert metrics["chunk"]["mrr@5"] == pytest.approx(1.0 / 3)
    assert metrics["chunk"]["recall@5"] == 1.0
    assert metrics["chunk"]["ndcg@5"] == pytest.approx(
        (1 / __import__("math").log2(4) + 1 / __import__("math").log2(5))
        / (1.0 + 1 / __import__("math").log2(3))
    )


def test_levels_cross_page_chunk_covers_two_gold_pages() -> None:
    metrics = compute_query_metrics(
        [result("c7-9", "docA", start_page=7, end_page=9)],
        gold_document_id="docA",
        gold_pages=[8, 9],
        gold_chunk_ids=["c7-9"],
    )
    assert metrics is not None
    assert metrics["page"]["recall@5"] == 1.0
    assert metrics["page"]["mrr@5"] == 1.0
    assert metrics["chunk"]["recall@5"] == 1.0


def test_levels_dedupe_duplicate_results() -> None:
    single = compute_query_metrics(
        [result("a8c1", "docA", start_page=8)],
        gold_document_id="docA",
        gold_pages=[8],
        gold_chunk_ids=["a8c1"],
    )
    duplicated = compute_query_metrics(
        [
            result("a8c1", "docA", start_page=8),
            result("a8c1", "docA", start_page=8),
        ],
        gold_document_id="docA",
        gold_pages=[8],
        gold_chunk_ids=["a8c1"],
    )
    assert single == duplicated


def test_levels_empty_results_with_gold() -> None:
    metrics = compute_query_metrics(
        [],
        gold_document_id="docA",
        gold_pages=[8],
        gold_chunk_ids=["a8c1", "a8c2"],
    )
    assert metrics is not None
    assert metrics["document"]["recall@5"] == 0.0
    assert metrics["chunk"]["recall@5"] == 0.0
    assert metrics["chunk"]["mrr@5"] == 0.0
    assert metrics["chunk"]["ndcg@5"] == 0.0


def test_levels_no_gold_returns_none() -> None:
    metrics = compute_query_metrics(
        [result("b8", "docB", start_page=8)],
        gold_document_id="docA",
        gold_pages=[],
        gold_chunk_ids=[],
        has_gold=False,
    )
    assert metrics is None


def test_levels_gold_page_not_in_coverage() -> None:
    metrics = compute_query_metrics(
        [result("a8c1", "docA", start_page=8)],
        gold_document_id="docA",
        gold_pages=[10],
        gold_chunk_ids=["a8c1"],
    )
    assert metrics is not None
    assert metrics["page"]["recall@5"] == 0.0
    assert metrics["document"]["recall@5"] == 1.0


def test_average_and_by_category() -> None:
    record_a = {"mrr@5": 0.5, "recall@5": 1.0}
    record_b = {"mrr@5": 0.25, "recall@5": 0.0}
    assert average_metrics([record_a, record_b]) == {
        "mrr@5": 0.375,
        "recall@5": 0.5,
    }
    grouped = aggregate_by_category(
        [
            ("clause", record_a),
            ("clause", record_b),
            ("simple_fact", record_a),
        ]
    )
    assert grouped["clause"]["mrr@5"] == 0.375
    assert grouped["simple_fact"]["mrr@5"] == 0.5
