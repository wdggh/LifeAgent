"""Unit tests for the manual answer-level review tooling (V2.0-08)."""

import json

import pytest

from tests.evaluation.reviews.answer_review import (
    AXES,
    expected_case_ids,
    review_status,
    summarize,
    validate_score_records,
)


def scored(case_id: str, values: tuple[int | None, ...] = (1, 1, 1)) -> dict:
    return {
        "id": case_id,
        **dict(zip(AXES, values)),
        "notes": "",
    }


def test_expected_cases_match_dataset() -> None:
    ids = expected_case_ids()
    assert len(ids) == 12
    assert len(set(ids)) == 12
    assert any(case_id.startswith("answer-") for case_id in ids)


def test_validate_requires_all_expected_ids() -> None:
    with pytest.raises(AssertionError, match="missing answer case ids"):
        validate_score_records(
            [scored("answer-001"), scored("answer-002")],
            expected_ids=["answer-001", "answer-002", "answer-003"],
        )


def test_validate_rejects_unknown_and_duplicate_ids() -> None:
    expected = ["answer-001"]
    with pytest.raises(AssertionError, match="unknown answer case id"):
        validate_score_records([scored("answer-999")], expected_ids=expected)
    with pytest.raises(AssertionError, match="duplicate answer case id"):
        validate_score_records(
            [scored("answer-001"), scored("answer-001")],
            expected_ids=expected,
        )


def test_validate_rejects_invalid_scores_and_fields() -> None:
    expected = ["answer-001"]
    with pytest.raises(AssertionError, match="must be 0 or 1"):
        validate_score_records(
            [scored("answer-001", (2, 1, 1))],
            expected_ids=expected,
        )
    with pytest.raises(AssertionError, match="unexpected fields"):
        validate_score_records(
            [{"id": "answer-001", "extra": 1}],
            expected_ids=expected,
        )


def test_pending_allowed_only_when_allow_pending() -> None:
    expected = ["answer-001"]
    pending = [scored("answer-001", (None, None, None))]
    with pytest.raises(AssertionError, match="must be 0 or 1"):
        validate_score_records(pending, expected_ids=expected)
    validate_score_records(
        pending, expected_ids=expected, allow_pending=True
    )


def test_review_status_ready_vs_partial() -> None:
    assert review_status([scored("answer-001"), scored("answer-002")]) == "READY"
    partial = [
        scored("answer-001"),
        scored("answer-002", (1, None, 0)),
    ]
    assert review_status(partial) == "PARTIAL"


def test_summarize_counts() -> None:
    records = [
        scored("answer-001", (1, 1, 0)),
        scored("answer-002", (0, None, 1)),
    ]
    summary = summarize(records)
    assert summary["source_correctness"] == {
        "pass": 1,
        "fail": 1,
        "pending": 0,
        "total": 2,
    }
    assert summary["completeness"] == {
        "pass": 1,
        "fail": 0,
        "pending": 1,
        "total": 2,
    }


def test_real_dataset_jsonl_is_parseable() -> None:
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[1]
        / "dataset"
        / "answer_cases.jsonl"
    )
    records = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) == 12
