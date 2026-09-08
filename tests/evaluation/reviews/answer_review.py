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
from pathlib import Path
from typing import Any

REVIEWS_DIR = Path(__file__).resolve().parent
DATASET_DIR = REVIEWS_DIR.parent / "dataset"
ANSWER_CASES = DATASET_DIR / "answer_cases.jsonl"

AXES = ("source_correctness", "completeness", "no_hallucination")
ALLOWED_KEYS = {"id", "notes", *AXES}


def expected_case_ids() -> list[str]:
    ids: list[str] = []
    with ANSWER_CASES.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            ids.append(record["id"])
    return ids


def build_template() -> dict[str, Any]:
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
            for case_id in expected_case_ids()
        ],
    }


def validate_score_records(
    records: list[dict],
    *,
    allow_pending: bool = False,
    expected_ids: list[str] | None = None,
) -> None:
    """Validate a scored (or template) review file."""

    expected = expected_ids if expected_ids is not None else expected_case_ids()
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

    check = sub.add_parser("check")
    check.add_argument("--input", required=True)
    check.add_argument(
        "--allow-pending",
        action="store_true",
        help="accept None scores (template / work-in-progress file)",
    )
    args = parser.parse_args()

    if args.command == "template":
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(build_template(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"template written: {output}")
        return 0

    path = Path(args.input)
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    records = payload["cases"]
    validate_score_records(records, allow_pending=args.allow_pending)
    print(
        f"answer review ok: status={review_status(records)} "
        f"summary={json.dumps(summarize(records), ensure_ascii=False)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
