"""Manual answer-level review tooling (V2.0-08).

Scoring is deliberately manual, not LLM-as-Judge. For each of the 12 answer
cases a reviewer fills three binary axes:

- ``source_correctness``: cited Sources match the expected gold document/page
  (for ``not_in_kb``: the answer must not cite any fabricated source);
- ``completeness``: all ``answer_requirements`` are addressed;
- ``no_hallucination``: no fact outside the corpus is invented.

Report status is ``READY`` only when every case has all three axes scored,
otherwise ``PARTIAL``. A partial review never blocks publishing the retrieval
baseline.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from tests.evaluation.datasets import paths

REVIEWS_DIR = Path(__file__).resolve().parent
REVIEW_DATASET = os.environ.get(
    "EVAL_ANSWER_DATASET", paths.active_dataset_name()
)

AXES = ("source_correctness", "completeness", "no_hallucination")
ALLOWED_KEYS = {"id", "notes", *AXES}

# A review file scores the transcripts of one run, so it must say which run it
# scored. ``baseline_transcripts`` is optional and names the inherited run.
PROVENANCE_KEYS = ("current_transcripts",)


class DuplicateKeyError(ValueError):
    """A review JSON file declares the same key twice."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """``object_pairs_hook`` that fails instead of silently keeping the last key.

    ``json.load`` overwrites earlier values, so a repeated ``transcripts`` key
    made every review appear to score the previous experiment's transcripts
    while silently dropping the current run's path.
    """

    payload: dict[str, Any] = {}
    for key, value in pairs:
        if key in payload:
            raise DuplicateKeyError(f"duplicate JSON key: {key!r}")
        payload[key] = value
    return payload


def load_review_payload(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle, object_pairs_hook=_reject_duplicate_keys)


def require_provenance(payload: dict[str, Any]) -> None:
    """A scored review must name the transcripts it scored."""

    missing = [key for key in PROVENANCE_KEYS if not payload.get(key)]
    assert not missing, (
        "scored answer review must declare its provenance "
        f"(missing: {missing}); set current_transcripts to the run this review "
        "scored and baseline_transcripts to the inherited run"
    )


def load_answer_cases(dataset: str | None = None) -> list[dict]:
    records: list[dict] = []
    path = paths.answer_cases_path(dataset or REVIEW_DATASET)
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def expected_case_ids(dataset: str | None = None) -> list[str]:
    return [record["id"] for record in load_answer_cases(dataset)]


def build_template(dataset: str | None = None) -> dict[str, Any]:
    return {
        "experiment": "v2.0-answer-review",
        "cases": [
            {
                "id": case_id,
                "source_correctness": None,
                "completeness": None,
                "no_hallucination": None,
                "notes": "",
            }
            for case_id in expected_case_ids(dataset)
        ],
    }


def validate_score_records(
    records: list[dict],
    *,
    allow_pending: bool = False,
    expected_ids: list[str] | None = None,
) -> None:
    """Validate a scored (or template) review file."""

    expected = (
        expected_ids
        if expected_ids is not None
        else expected_case_ids()
    )
    seen: set[str] = set()
    for record in records:
        assert set(record) <= ALLOWED_KEYS, f"{record.get('id')}: unexpected fields"
        case_id = record["id"]
        assert case_id in expected, f"unknown answer case id: {case_id}"
        assert case_id not in seen, f"duplicate answer case id: {case_id}"
        seen.add(case_id)
        for axis in AXES:
            value = record[axis]
            if value is None and allow_pending:
                continue
            assert value in (0, 1), (
                f"{case_id}: {axis} must be 0 or 1, got {value!r}"
            )
        notes = record.get("notes", "")
        assert isinstance(notes, str), f"{case_id}: notes must be a string"
    missing = [case_id for case_id in expected if case_id not in seen]
    assert not missing, f"missing answer case ids: {missing}"


def review_status(records: list[dict]) -> str:
    """READY when every axis of every case is scored, otherwise PARTIAL."""

    all_scored = all(
        all(record.get(axis) in (0, 1) for axis in AXES) for record in records
    )
    return "READY" if all_scored else "PARTIAL"


def summarize(records: list[dict]) -> dict[str, dict[str, int]]:
    """Per-axis pass/fail/pending counts for the report."""

    summary: dict[str, dict[str, int]] = {}
    for axis in AXES:
        total = len(records)
        scored = [record.get(axis) for record in records]
        passed = sum(1 for value in scored if value == 1)
        pending = sum(1 for value in scored if value is None)
        summary[axis] = {
            "pass": passed,
            "fail": total - passed - pending,
            "pending": pending,
            "total": total,
        }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    template = sub.add_parser("template")
    template.add_argument("--output", required=True)
    template.add_argument(
        "--dataset",
        default=REVIEW_DATASET,
        help="evaluation dataset whose answer_cases are reviewed",
    )

    check = sub.add_parser("check")
    check.add_argument("--input", required=True)
    check.add_argument(
        "--dataset",
        default=REVIEW_DATASET,
        help="evaluation dataset whose answer_cases are reviewed",
    )
    check.add_argument(
        "--allow-pending",
        action="store_true",
        help="accept None scores (template / work-in-progress file)",
    )
    args = parser.parse_args()
    expected = expected_case_ids(args.dataset)

    if args.command == "template":
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        template_payload = build_template(args.dataset)
        template_payload["dataset"] = args.dataset
        output.write_text(
            json.dumps(template_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"template written: {output}")
        return 0

    path = Path(args.input)
    try:
        payload = load_review_payload(path)
    except DuplicateKeyError as exc:
        print(f"answer review INVALID: {path}: {exc}")
        return 1
    records = payload["cases"]
    validate_score_records(
        records, allow_pending=args.allow_pending, expected_ids=expected
    )
    if not args.allow_pending:
        require_provenance(payload)
    print(
        f"answer review ok: status={review_status(records)} "
        f"summary={json.dumps(summarize(records), ensure_ascii=False)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
