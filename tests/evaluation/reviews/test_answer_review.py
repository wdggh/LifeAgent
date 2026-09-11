"""Unit tests for the manual answer-level review tooling (V2.0-08)."""

import json
from pathlib import Path

import pytest

from tests.evaluation.datasets import paths
from tests.evaluation.reviews.answer_review import (
    AXES,
    CASE_SET_REVISIONS,
    REVIEWS_DIR,
    DuplicateKeyError,
    expected_case_ids,
    expected_case_ids_for,
    load_review_payload,
    require_provenance,
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
    assert len(ids) == 13
    assert len(set(ids)) == 13
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
    path = paths.answer_cases_path(paths.V1)
    records = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) == 12  # frozen v1 dataset


def test_loader_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    """A repeated key silently drops the earlier value; refuse it instead."""

    path = tmp_path / "review.json"
    path.write_text(
        '{"current_transcripts": "reports/current.raw.json",'
        ' "current_transcripts": "reports/stale.raw.json"}',
        encoding="utf-8",
    )
    with pytest.raises(DuplicateKeyError, match="duplicate JSON key"):
        load_review_payload(path)


def test_require_provenance_rejects_missing_current_transcripts() -> None:
    with pytest.raises(AssertionError, match="provenance"):
        require_provenance({"cases": []})
    require_provenance({"current_transcripts": "reports/current.raw.json"})


def test_shipped_reviews_parse_without_duplicate_keys() -> None:
    """Regression guard on the committed provenance defect."""

    reviews = sorted(REVIEWS_DIR.glob("answer_review_*.json"))
    assert reviews
    for review in reviews:
        payload = load_review_payload(review)
        assert payload["cases"], review.name
        if payload.get("review_status", "").startswith(("READY", "DRAFT")):
            require_provenance(payload)


def test_case_set_revision_resolves_preset_ids() -> None:
    assert expected_case_ids_for("answer-cases-12") == [
        f"answer-{index:03d}" for index in range(1, 13)
    ]
    assert expected_case_ids_for("answer-cases-13")[-1] == "answer-013"
    with pytest.raises(AssertionError, match="unknown case_set_revision"):
        expected_case_ids_for("answer-cases-99")


def test_declared_case_set_revisions_revalidate_their_reviews() -> None:
    """Point-in-time reviews stay checkable against their own case set."""

    seen: set[str] = set()
    for review in sorted(REVIEWS_DIR.glob("answer_review_*.json")):
        payload = load_review_payload(review)
        revision = payload.get("case_set_revision")
        if revision is None:
            continue
        assert revision in CASE_SET_REVISIONS, review.name
        validate_score_records(
            payload["cases"], expected_ids=expected_case_ids_for(revision)
        )
        seen.add(revision)
    assert seen == set(CASE_SET_REVISIONS)
