"""Agent-context funnel report over one answer-transcript file (V2.3d).

Reads the raw transcripts written by ``run_answer_transcripts`` (which carry
``retrieval_steps`` with per-call chunk ids and ``gold_chunk_ids``) and reports,
per case, whether the gold chunk reached the Agent's consumed window.

The manual half of the funnel ("did the answer use it?") is read from an
answer review when one is supplied: ``completeness == 1`` is the auditable
proxy, because it means every ``answer_requirements`` bullet was addressed.
Without a review the retrieval half is still reported and the case is labelled
``pending_review`` instead of being guessed.

Run:
    python -m tests.evaluation.reviews.funnel_report \
        --transcripts reports/answer-transcripts-v2.3d-agent-context.raw.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.domain.constants import CHUNKS_PER_ROUND

from tests.evaluation.metrics.agent_context import (
    FUNNEL_LABELS,
    classify_funnel,
)

PENDING = "pending_review"
REPORT_DIR = Path(__file__).resolve().parents[1] / "reports"


def _search_calls(transcript: dict[str, Any]) -> list[list[str]]:
    return [
        list(step.get("chunk_ids") or [])
        for step in transcript.get("retrieval_steps") or []
        if step.get("tool") == "search_knowledge"
        and step.get("error") is None
    ]


def build_rows(
    transcripts: list[dict[str, Any]],
    review: dict[str, Any] | None,
    k: int,
) -> list[dict[str, Any]]:
    by_id = {
        record["id"]: record for record in (review or {}).get("cases", [])
    }
    rows: list[dict[str, Any]] = []
    for transcript in transcripts:
        calls = _search_calls(transcript)
        gold = list(transcript.get("gold_chunk_ids") or [])
        scored = by_id.get(transcript["id"])
        if not gold:
            label = classify_funnel(
                gold_chunk_ids=[],
                per_call_chunk_ids=calls,
                k=k,
                used=False,
            )
        elif scored is None:
            label = PENDING
        else:
            label = classify_funnel(
                gold_chunk_ids=gold,
                per_call_chunk_ids=calls,
                k=k,
                returned_document_ids=set(),
                gold_document_ids=set(),
                used=bool(scored.get("completeness") == 1),
            )
        rows.append(
            {
                "id": transcript["id"],
                "category": transcript.get("category"),
                "retrievals": transcript.get("retrieval_count"),
                "calls": len(calls),
                "call_sizes": [len(call) for call in calls],
                "gold_chunks": len(gold),
                "gold_in_context": (
                    bool(set(gold) & {c for call in calls for c in call[:k]})
                    if gold
                    else None
                ),
                "label": label,
                "completeness": (
                    scored.get("completeness") if scored else None
                ),
            }
        )
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {label: 0 for label in (*FUNNEL_LABELS, PENDING)}
    for row in rows:
        counts[row["label"]] += 1
    return counts


def to_markdown(rows: list[dict[str, Any]], k: int) -> str:
    lines = [
        f"# Agent-context funnel (k={k})",
        "",
        "| case | category | retrievals | call sizes | gold chunks | "
        "gold in context | label | completeness |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['id']} | {row['category']} | {row['retrievals']} | "
            f"{row['call_sizes']} | {row['gold_chunks']} | "
            f"{row['gold_in_context']} | {row['label']} | "
            f"{row['completeness']} |"
        )
    counts = summarize(rows)
    lines += ["", "## Counts", ""]
    lines += [f"- {label}: {count}" for label, count in counts.items()]
    in_context = [
        row for row in rows if row["gold_in_context"] is not None
    ]
    if in_context:
        hits = sum(1 for row in in_context if row["gold_in_context"])
        lines += [
            "",
            f"agent_context_recall@{k} = {hits}/{len(in_context)} = "
            f"{round(hits / len(in_context), 4)}",
        ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transcripts", required=True)
    parser.add_argument(
        "--review",
        default=None,
        help="answer review JSON; supplies the 'used' half of the funnel",
    )
    parser.add_argument("--k", type=int, default=CHUNKS_PER_ROUND)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    transcripts = json.loads(
        Path(args.transcripts).read_text(encoding="utf-8")
    )["transcripts"]
    review = (
        json.loads(Path(args.review).read_text(encoding="utf-8"))
        if args.review
        else None
    )
    rows = build_rows(transcripts, review, args.k)
    report = to_markdown(rows, args.k)
    print(report)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
        print(f"funnel report written: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
