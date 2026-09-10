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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from app.core.config import get_settings
from app.agent.tools.base import ToolContext
from app.agent.tools.search_knowledge import SearchKnowledgeTool
from app.api.dependencies import get_llm_client
from app.domain.models.search_result import SearchResult
from app.infrastructure.embedding.factory import get_embedding_client
from app.rag.query.expansion import QueryExpander
from app.rag.query.rewriter import QueryRewriter
from app.rag.retrieval.retriever import Retriever
from app.rag.retrieval.sparse import (
    BM25SparseSearcher,
    RedisCorpusVersionStore,
)

from tests.evaluation.mapping.gold_mapping import (
    resolve_gold_chunks,
    union_gold_chunks,
)
from tests.evaluation.metrics.aggregate import (
    aggregate_by_category,
    average_metrics,
)
from tests.evaluation.metrics.levels import compute_query_metrics
from tests.evaluation.runners.ingest_corpus import (
    eval_collection_name,
    live_harness,
)
from tests.evaluation.datasets import paths

LEVELS = ("document", "page", "chunk")
REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"
GATE_IDS = {"reg-001", "reg-002"}
HARD_MRR_THRESHOLD = 1.0
HARD_NDCG_THRESHOLD = 0.95


@dataclass
class QueryOutcome:
    query_id: str
    category: str
    metrics: dict | None
    chunk_recall5: float | None
    dense_gap: float | None
    near_tie_reproduced: bool | None
    hard_candidate: bool = False
    hard: bool = False
    metadata: dict = field(default_factory=dict)
    gold_chunk_ids: list[str] = field(default_factory=list)
    branch_hit_ids: list[list[str]] = field(default_factory=list)


def _dense_gap_diagnostic(
    results: Sequence[SearchResult],
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
        if result.chunk_id not in gold_chunk_ids
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
    search_tool: Any | None = None,
) -> QueryOutcome:
    """Run one retrieval query through the real seams and score it."""

    gold_entries = query_record["gold"]
    metadata: dict = {}
    if search_tool is not None:
        tool_result = await search_tool.run(
            {"query": query_record["question"], "top_k": 10},
            ToolContext(user_id=user_id, remaining_chunk_budget=10),
        )
        results = tool_result.results
        metadata = tool_result.metadata
    else:
        results = await retriever.search(
            query_record["question"], user_id=user_id, top_k=10
        )
    gold_by_document = await resolve_gold_chunks(
        chunk_source, slug_to_document_id, gold_entries
    )
    gold_chunk_ids = union_gold_chunks(gold_by_document)
    gold_documents = {
        slug_to_document_id[entry["document"]]: entry["pages"]
        for entry in gold_entries
    }
    metrics = compute_query_metrics(
        results,
        gold_documents=gold_documents,
        gold_chunk_ids=sorted(gold_chunk_ids),
    )
    gap, reproduced = _dense_gap_diagnostic(
        results, gold_chunk_ids
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
        hard_candidate=bool(query_record.get("hard_candidate", False)),
        hard=bool(query_record.get("hard", False)),
        metadata=metadata,
        gold_chunk_ids=sorted(gold_chunk_ids),
        branch_hit_ids=metadata.get("branch_hit_ids")
        or [[result.chunk_id for result in results]],
    )


def write_raw_outcomes(
    outcomes: Sequence[QueryOutcome],
    path: Path = REPORTS_DIR / "triage-v2.raw.json",
) -> Path:
    """Archive per-case triage metrics (gitignored raw artifact)."""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "id": outcome.query_id,
            "category": outcome.category,
            "metrics": outcome.metrics,
            "chunk_recall@5": outcome.chunk_recall5,
            "dense_score_gap": outcome.dense_gap,
            "near_tie_reproduced": outcome.near_tie_reproduced,
            "metadata": outcome.metadata,
            "gold_chunk_ids": outcome.gold_chunk_ids,
            "branch_hit_ids": outcome.branch_hit_ids,
        }
        for outcome in outcomes
    ]
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


async def run_live_evaluation(
    *,
    queries: Sequence[dict],
    manifest: dict[str, Any],
    fixtures_root: Path,
    reset: bool,
    via_tool: bool = False,
    skip_ingest: bool = False,
    experiment_name: str | None = None,
) -> tuple[dict[str, Any], list[QueryOutcome]]:
    """Ingest the corpus, evaluate every query, return report + outcomes."""

    async with live_harness(reset=reset) as harness:
        user = await harness.ensure_eval_user()
        if skip_ingest:
            mapping = await _mapping_from_existing(harness, user, manifest)
        else:
            mapping = await harness.ingest_corpus(
                manifest, fixtures_root, reset_documents=reset
            )
        retriever = Retriever(
            get_embedding_client(),
            harness.vectors,
        )
        search_tool = None
        if via_tool:
            llm_client = await get_llm_client()
            settings = get_settings()
            sparse_searcher = (
                BM25SparseSearcher(
                    document_source=harness.documents,
                    vector_repository_provider=lambda: harness.vectors,
                    version_store=RedisCorpusVersionStore(
                        settings.redis_url
                    ),
                    settings=settings,
                )
                if settings.query_sparse_enabled
                else None
            )
            search_tool = SearchKnowledgeTool(
                retriever,
                query_rewriter=QueryRewriter(llm_client),
                query_expander=QueryExpander(llm_client),
                sparse_searcher=sparse_searcher,
            )
        outcomes = [
            await evaluate_query(
                query_record=query,
                slug_to_document_id=mapping,
                retriever=retriever,
                chunk_source=harness.vectors,
                user_id=user.id,
                search_tool=search_tool,
            )
            for query in queries
        ]
    return build_report(manifest, outcomes, experiment_name), outcomes


async def _mapping_from_existing(
    harness: Any, user: Any, manifest: dict[str, Any]
) -> dict[str, str]:
    """Resolve slug -> document id for an already-ingested eval corpus."""

    documents = await harness.documents.list_documents(user.id, 1, 100)
    by_name = {document.filename: document.id for document in documents}
    mapping: dict[str, str] = {}
    for entry in manifest["documents"]:
        filename = Path(entry["file"]).name
        if filename not in by_name:
            raise RuntimeError(
                f"{entry['slug']}: {filename} is not ingested; "
                "run once without --skip-ingest"
            )
        mapping[entry["slug"]] = by_name[filename]
    return mapping


def build_report(
    manifest: dict[str, Any],
    outcomes: Sequence[QueryOutcome],
    experiment_name: str | None = None,
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

    revision = manifest.get("revision")
    if experiment_name:
        experiment = experiment_name
    elif revision:
        experiment = f"{revision}-baseline"
    elif manifest.get("corpus_version") == "synthetic-personal-kb-v2":
        experiment = "v2.0.1-baseline"
    else:
        experiment = "v2.0-baseline"

    regression: dict[str, dict[str, Any]] = {}
    gate_pass = True
    for outcome in outcomes:
        if outcome.query_id.startswith("reg-"):
            passed = outcome.chunk_recall5 == 1.0
            is_gate = outcome.query_id in GATE_IDS
            if is_gate:
                gate_pass = gate_pass and passed
            regression[outcome.query_id] = {
                "chunk_recall@5": outcome.chunk_recall5,
                "pass": passed,
                "gate": is_gate,
                "dense_score_gap": outcome.dense_gap,
                "near_tie_reproduced": outcome.near_tie_reproduced,
            }

    difficulty: dict[str, dict] = {}
    for label, predicate in (
        ("hard", lambda outcome: outcome.hard),
        ("easy", lambda outcome: not outcome.hard),
    ):
        records = [
            outcome.metrics
            for outcome in outcomes
            if outcome.metrics is not None and predicate(outcome)
        ]
        difficulty[label] = {
            "queries": len(records),
            "metrics": {
                level: average_metrics(
                    [record[level] for record in records]
                )
                for level in LEVELS
            },
        }

    settings = get_settings()
    rewrite_stats: dict[str, Any] | None = None
    expansion_stats: dict[str, Any] | None = None
    if any(
        outcome.metadata.get("query_variants") is not None
        for outcome in outcomes
    ):
        reasons: dict[str, int] = {}
        durations: list[float] = []
        variants_generated = 0
        for outcome in outcomes:
            metadata = outcome.metadata
            if not metadata:
                continue
            variants_generated += len(metadata.get("query_variants") or [])
            if metadata.get("expansion_fallback"):
                reason = (
                    metadata.get("expansion_fallback_reason") or "unknown"
                )
                reasons[reason] = reasons.get(reason, 0) + 1
            if metadata.get("expansion_duration_ms") is not None:
                durations.append(metadata["expansion_duration_ms"])
        expansion_stats = {
            "cases": sum(1 for outcome in outcomes if outcome.metadata),
            "variants_generated": variants_generated,
            "fallback": sum(reasons.values()),
            "fallback_reasons": reasons,
            "avg_duration_ms": (
                round(sum(durations) / len(durations), 2)
                if durations
                else None
            ),
        }
    elif any(
        outcome.metadata.get("rewrite_fallback") is not None
        for outcome in outcomes
    ):
        reasons: dict[str, int] = {}
        durations: list[float] = []
        rewritten = 0
        for outcome in outcomes:
            metadata = outcome.metadata
            if not metadata:
                continue
            if metadata.get("rewrite_fallback"):
                reason = metadata.get("rewrite_fallback_reason") or "unknown"
                reasons[reason] = reasons.get(reason, 0) + 1
            else:
                rewritten += 1
            if metadata.get("rewrite_duration_ms") is not None:
                durations.append(metadata["rewrite_duration_ms"])
        rewrite_stats = {
            "cases": sum(1 for outcome in outcomes if outcome.metadata),
            "rewritten": rewritten,
            "fallback": sum(reasons.values()),
            "fallback_reasons": reasons,
            "avg_duration_ms": (
                round(sum(durations) / len(durations), 2)
                if durations
                else None
            ),
        }
    return {
            "experiment": experiment,
        "status": "PASS" if gate_pass else "FAIL",
        "dataset_version": manifest["corpus_version"],
    "dataset_revision": revision,
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
        "metrics_by_difficulty": difficulty,
        "query_expansion": expansion_stats,
        "query_rewrite": rewrite_stats,
        "regression": regression,
        "answer_level": {"status": "PENDING", "reference": "answer_review"},
    }


def is_hard_outcome(outcome: QueryOutcome) -> bool:
    """Hard = authored candidate AND empirical gate met.

    Empirical gate: MRR@5 < 1.0 or chunk NDCG@5 < 0.95. Non-candidates can
    never become hard (no manufacturing failures).
    """

    if outcome.metrics is None or not outcome.hard_candidate:
        return False
    chunk = outcome.metrics["chunk"]
    return (
        chunk.get("mrr@5", 0.0) < HARD_MRR_THRESHOLD
        or chunk.get("ndcg@5", 0.0) < HARD_NDCG_THRESHOLD
    )


def mark_hard_flags(queries_path: Path, outcomes: Sequence[QueryOutcome]) -> dict:
    """Write ``hard: true/false`` back into the v2 queries file (triage run)."""

    qualifies = {
        outcome.query_id: is_hard_outcome(outcome) for outcome in outcomes
    }
    lines: list[str] = []
    marked_hard = 0
    easy_under_construction = 0
    with queries_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record["id"] in qualifies and record.get("hard_candidate"):
                record["hard"] = bool(qualifies[record["id"]])
                if record["hard"]:
                    marked_hard += 1
                else:
                    easy_under_construction += 1
            else:
                record["hard"] = False
            lines.append(json.dumps(record, ensure_ascii=False))
    queries_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "hard": marked_hard,
        "easy_under_construction": easy_under_construction,
    }


def write_report(report: dict[str, Any], path: Path = REPORTS_DIR / "baseline-v2.0.json") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def run_fast_checks(dataset: str | None = None) -> int:
    """CI-safe checks: dataset schema, corpus/PDF anchors, canned metrics."""

    from tests.evaluation.dataset import validate_dataset, validate_v2
    from tests.evaluation.tools import validate_corpus

    name = dataset or paths.active_dataset_name()
    if name == paths.V2:
        dataset_ok = validate_v2.main(dataset=name)
    else:
        dataset_ok = validate_dataset.main(dataset=name)
    corpus_ok = validate_corpus.main(dataset=name)
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
        gold_documents={"doc_a": [8]},
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
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    fast = sub.add_parser("fast")
    fast.add_argument(
        "--dataset",
        default=paths.active_dataset_name(),
        help="evaluation dataset directory name",
    )

    live = sub.add_parser("live")
    live.add_argument(
        "--dataset",
        default=paths.active_dataset_name(),
        help="evaluation dataset directory name",
    )
    live.add_argument("--manifest", default=None)
    live.add_argument("--queries", default=None)
    live.add_argument("--fixtures", default=None)
    live.add_argument("--reset", action="store_true")
    live.add_argument(
        "--via-tool",
        action="store_true",
        help="evaluate through SearchKnowledgeTool (query rewrite path)",
    )
    live.add_argument(
        "--skip-ingest",
        action="store_true",
        help="reuse the already-ingested eval corpus",
    )
    live.add_argument(
        "--experiment-name",
        default=None,
        help="override the experiment label in the report",
    )
    live.add_argument(
        "--mark-hard",
        action="store_true",
        help="write triage hard flags back into the v2 queries file",
    )
    live.add_argument("--report", default=str(REPORTS_DIR / "baseline-v2.0.json"))
    live.add_argument(
        "--raw", default=str(REPORTS_DIR / "triage-v2.raw.json")
    )
    args = parser.parse_args()

    if args.command == "fast":
        return run_fast_checks(dataset=args.dataset)

    manifest_path = Path(args.manifest) if args.manifest else paths.manifest_path(
        args.dataset
    )
    queries_path = Path(args.queries) if args.queries else paths.queries_path(
        args.dataset
    )
    fixtures_root = Path(args.fixtures) if args.fixtures else paths.fixtures_dir(
        args.dataset
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    queries = _load_queries(queries_path)
    report, outcomes = await run_live_evaluation(
        queries=queries,
        manifest=manifest,
        fixtures_root=fixtures_root,
        reset=args.reset,
        via_tool=args.via_tool,
        skip_ingest=args.skip_ingest,
        experiment_name=args.experiment_name,
    )
    path = write_report(report, Path(args.report))
    raw_path = write_raw_outcomes(outcomes, Path(args.raw))
    if args.mark_hard:
        counts = mark_hard_flags(queries_path, outcomes)
        print(f"hard flags updated: {counts}")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"report written: {path}")
    print(f"raw triage written: {raw_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
