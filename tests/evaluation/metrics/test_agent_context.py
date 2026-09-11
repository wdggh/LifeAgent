"""Tests for the V2.3d agent-context funnel (pure functions only)."""

from __future__ import annotations

import pytest

from tests.evaluation.metrics.agent_context import (
    DOCUMENT_ONLY,
    FOUND_BEYOND_BUDGET,
    NOT_APPLICABLE,
    NOT_RETRIEVED,
    RETURNED_NOT_USED,
    USED,
    agent_context_recall,
    classify_funnel,
    context_hit,
    first_call_context_recall,
    summarize_funnel,
)


def test_context_hit_respects_the_consumed_window() -> None:
    returned = ["c1", "c2", "c3", "c4", "c5"]
    assert context_hit({"c4"}, returned, 4) is True
    assert context_hit({"c5"}, returned, 4) is False
    with pytest.raises(ValueError, match="k must be positive"):
        context_hit({"c1"}, returned, 0)


def test_agent_context_recall_is_the_union_over_calls() -> None:
    # Gold only in the second call: the multi-round loop rescued the first call.
    assert agent_context_recall(
        {"c9"}, [["c1", "c2"], ["c3", "c9"]], 4
    ) is True
    assert first_call_context_recall(
        {"c9"}, [["c1", "c2"], ["c3", "c9"]], 4
    ) is False
    assert first_call_context_recall({"c9"}, [], 4) is False


def test_agent_context_recall_respects_the_cap_per_call() -> None:
    wide = ["c1", "c2", "c3", "c4", "c9"]
    assert agent_context_recall({"c9"}, [wide], 10) is True
    assert agent_context_recall({"c9"}, [wide], 4) is False


def test_classify_funnel_labels_every_layer() -> None:
    assert (
        classify_funnel(
            gold_chunk_ids=set(),
            per_call_chunk_ids=[["c1"]],
            k=4,
            used=False,
        )
        == NOT_APPLICABLE
    )
    assert (
        classify_funnel(
            gold_chunk_ids={"g1"},
            per_call_chunk_ids=[["c1", "c2"]],
            k=4,
            gold_document_ids={"doc_g"},
            returned_document_ids={"doc_other"},
            used=False,
        )
        == NOT_RETRIEVED
    )
    assert (
        classify_funnel(
            gold_chunk_ids={"g1"},
            per_call_chunk_ids=[["c1", "c2"]],
            k=4,
            gold_document_ids={"doc_g"},
            returned_document_ids={"doc_g"},
            used=False,
        )
        == DOCUMENT_ONLY
    )
    assert (
        classify_funnel(
            gold_chunk_ids={"g1"},
            per_call_chunk_ids=[["c1", "c2", "c3", "c4", "g1"]],
            k=4,
            used=False,
        )
        == FOUND_BEYOND_BUDGET
    )
    assert (
        classify_funnel(
            gold_chunk_ids={"g1"},
            per_call_chunk_ids=[["g1", "c2"]],
            k=4,
            used=False,
        )
        == RETURNED_NOT_USED
    )
    assert (
        classify_funnel(
            gold_chunk_ids={"g1"},
            per_call_chunk_ids=[["g1", "c2"]],
            k=4,
            used=True,
        )
        == USED
    )


def test_summarize_funnel_counts_every_label() -> None:
    counts = summarize_funnel([USED, USED, NOT_RETRIEVED])
    assert counts[USED] == 2
    assert counts[NOT_RETRIEVED] == 1
    assert counts[DOCUMENT_ONLY] == 0
    with pytest.raises(ValueError, match="unknown funnel label"):
        summarize_funnel(["made_up"])
