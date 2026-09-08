"""Retrieval evaluation runner, fast and live (V2.0-06).

Fast mode (CI-safe, no external services): dataset schema + corpus/PDF
validations plus a canned metrics self-check through the pure metric path.

Live mode (PostgreSQL + Chroma + DashScope only): ingest the synthetic corpus
through the V2.0-05 harness, then for every query run the real V1 Retriever
(top_k=10), map gold pages to runtime chunks (V2.0-03), compute
document/page/chunk metrics (V2.0-04), enforce the reg-001/reg-002 gate, and
write the controlled ``reports/baseline-v2.0.json``.

CI validates the framework; live validates retrieval quality. The README must
never claim CI runs the live evaluation.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from app.core.config import get_settings
from app.domain.models.search_result import SearchResult
from app.infrastructure.embedding.factory import get_embedding_client
from app.rag.retrieval.retriever import Retriever

from tests.evaluation.mapping.gold_mapping import map_gold_chunks
from tests.evaluation.metrics.aggregate import (
    aggregate_by_category,
    average_metrics,
)
from tests.evaluation.metrics.levels import compute_query_metrics
from tests.evaluation.runners.ingest_corpus import (
    eval_collection_name,
    live_harness,
)

LEVELS = ("document", "page", "chunk")
REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"


@dataclass
class QueryOutcome:
    query_id: str
    category: str
    metrics: dict | None
    chunk_recall5: float | None
    dense_gap: float | None
    near_tie_reproduced: bool | None


def _dense_gap_diagnostic(
    results: Sequence[SearchResult],
    gold_document_id: str,
    gold_chunk_ids: set[str],
) -> tuple[float | None, bool | None]:
    """Score gap between the best gold chunk and the best decoy chunk.

    A gap below 0.1 marks the near-tie as reproduced; a missing decoy (not in
    the top results) yields ``None``. Diagnostic only, never a gate.
    """

    gold_scores = [
        result.score
        for result in results
        if result.chunk_id in gold_chunk_ids
    ]
    decoy_scores = [
        result.score
        for result in results
        if result.document_id == gold_document_id
        and result.chunk_id not in gold_chunk_ids
    ]
    if not gold_scores:
        return None, False
    if not decoy_scores:
        return None, None
    gap = max(gold_scores) - max(decoy_scores)
    return round(gap, 4), gap < 0.1


async def evaluate_query(
    *,
    query_record: dict[str, Any],
    slug_to_document_id: dict[str, str],
    retriever: Any,
    chunk_source: Any,
    user_id: str,
) -> QueryOutcome:
    """Run one retrieval query through the real seams and score it."""

    gold = query_record["gold"]
    document_id = slug_to_document_id[gold["document"]]
    results = await retriever.search(
        query_record["question"], user_id=user_id, top_k=10
    )
    stored_chunks = await chunk_source.fetch_document_chunks(document_id)
    gold_chunk_ids = map_gold_chunks(gold["pages"], stored_chunks)
    metrics = compute_query_metrics(
        results,
        gold_document_id=document_id,
        gold_pages=gold["pages"],
        gold_chunk_ids=sorted(gold_chunk_ids),
    )
    gap, reproduced = _dense_gap_diagnostic(
        results, document_id, gold_chunk_ids
    )
    chunk_recall5 = (
        metrics["chunk"]["recall@5"] if metrics is not None else None
    )
    return QueryOutcome(
        query_id=query_record["id"],
        category=query_record["category"],
        metrics=metrics,
        chunk_recall5=chunk_recall5,
        dense_gap=gap,
        near_tie_reproduced=reproduced,
    )


async def run_live_evaluation(
    *,
    queries: Sequence[dict],
    manifest: dict[str, Any],
    fixtures_root: Path,
    reset: bool,
) -> dict[str, Any]:
    """Ingest the corpus, evaluate every query, return the controlled report."""

    async with live_harness(reset=reset) as harness:
        user = await harness.ensure_eval_user()
        mapping = await harness.ingest_corpus(
            manifest, fixtures_root, reset_documents=reset
        )
        retriever = Retriever(
            get_embedding_client(),
            harness.vectors,
        )
        outcomes = [
            await evaluate_query(
                query_record=query,
                slug_to_document_id=mapping,
                retriever=retriever,
                chunk_source=harness.vectors,
                user_id=user.id,
            )
            for query in queries
        ]
    return build_report(manifest, outcomes)


def build_report(
    manifest: dict[str, Any],
    outcomes: Sequence[QueryOutcome],
) -> dict[str, Any]:
    """Assemble the controlled report from per-query outcomes."""

    overall: dict[str, dict] = {}
    by_category: dict[str, dict[str, dict]] = {}
    for level in LEVELS:
        records = [
            outcome.metrics[level]
            for outcome in outcomes
            if outcome.metrics is not None
        ]
        overall[level] = average_metrics(records)
        categorized = [
            (outcome.category, outcome.metrics[level])
            for outcome in outcomes
            if outcome.metrics is not None
        ]
        for category, level_metrics in aggregate_by_category(categorized).items():
            by_category.setdefault(category, {})[level] = level_metrics

    regression: dict[str, dict[str, Any]] = {}
    gate_pass = True
    for outcome in outcomes:
        if outcome.query_id.startswith("reg-"):
            passed = outcome.chunk_recall5 == 1.0
            gate_pass = gate_pass and passed
            regression[outcome.query_id] = {
                "chunk_recall@5": outcome.chunk_recall5,
                "pass": passed,
                "dense_score_gap": outcome.dense_gap,
                "near_tie_reproduced": outcome.near_tie_reproduced,
            }

    settings = get_settings()
    return {
        "experiment": "v2.0-baseline",
        "status": "PASS" if gate_pass else "FAIL",
        "dataset_version": manifest["corpus_version"],
        "retriever": {
            "type": "dense",
            "embedding_model": f"{settings.embedding_model}:"
            f"{settings.embedding_dimensions}",
            "collection": eval_collection_name(settings.chroma_collection),
        },
        "run": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "queries": len(outcomes),
        },
        "metrics": overall,
        "metrics_by_category": by_category,
        "regression": regression,
        "answer_level": {"status": "PENDING", "reference": "answer_review"},
    }


def write_report(report: dict[str, Any], path: Path = REPORTS_DIR / "baseline-v2.0.json") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def run_fast_checks() -> int:
    """CI-safe checks: dataset schema, corpus/PDF anchors, canned metrics."""

    from tests.evaluation.dataset import validate_dataset
    from tests.evaluation.fixtures.generators import validate_corpus

    dataset_ok = validate_dataset.main()
    corpus_ok = validate_corpus.main()
    if dataset_ok or corpus_ok:
        return 1

    sample = SearchResult(
        chunk_id="a8c1",
        document_id="doc_a",
        document_name="doc_a.pdf",
        content="x",
        score=0.9,
        start_page=8,
        end_page=8,
    )
    metrics = compute_query_metrics(
        [sample],
        gold_document_id="doc_a",
        gold_pages=[8],
        gold_chunk_ids=["a8c1"],
    )
    assert metrics is not None
    assert metrics["document"]["mrr@5"] == 1.0
    assert metrics["chunk"]["recall@5"] == 1.0
    print("fast checks ok: dataset, corpus/PDF, canned metrics")
    return 0


def _load_queries(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


async def _main() -> int:
    fixtures = Path(__file__).resolve().parents[1] / "fixtures"
    dataset_dir = fixtures.parent / "dataset"
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("fast")

    live = sub.add_parser("live")
    live.add_argument("--manifest", default=str(fixtures / "corpus" / "manifest.json"))
    live.add_argument("--queries", default=str(dataset_dir / "queries.jsonl"))
    live.add_argument("--fixtures", default=str(fixtures))
    live.add_argument("--reset", action="store_true")
    live.add_argument("--report", default=str(REPORTS_DIR / "baseline-v2.0.json"))
    args = parser.parse_args()

    if args.command == "fast":
        return run_fast_checks()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    queries = _load_queries(Path(args.queries))
    report = await run_live_evaluation(
        queries=queries,
        manifest=manifest,
        fixtures_root=Path(args.fixtures),
        reset=args.reset,
    )
    path = write_report(report, Path(args.report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"report written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
