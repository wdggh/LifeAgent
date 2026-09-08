"""Fast canary tests for the 9addb1a double-layer regression suite (V2.0-07).

Layer A dataset/gate facts are asserted here so reg-001/reg-002 can never be
silently edited away. Layer B (tool-level engineering test) is asserted by
static presence so it can never be removed or migrated without failing.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from tests.evaluation.datasets import paths
from tests.evaluation.runners.retrieval_eval import (
    QueryOutcome,
    build_report,
)

QUERIES = paths.queries_path(paths.V1)
TOOL_REGRESSION = Path(__file__).resolve().parents[2] / "test_review_fixes.py"

CLAUSE_LEAK = re.compile(r"第[一二三四五六七八九十\d]+条")


def load_queries() -> list[dict]:
    records = []
    with QUERIES.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def test_regression_queries_target_pages_8_and_9() -> None:
    queries = {record["id"]: record for record in load_queries()}
    assert {"reg-001", "reg-002"} <= set(queries)
    assert queries["reg-001"]["category"] == "clause_specific"
    assert queries["reg-002"]["category"] == "clause_specific"
    assert queries["reg-001"]["gold"] == {
        "document": "rental_contract_01",
        "pages": [8],
    }
    assert queries["reg-002"]["gold"] == {
        "document": "rental_contract_01",
        "pages": [9],
    }


def test_regression_questions_do_not_leak_clause_numbers() -> None:
    queries = {record["id"]: record for record in load_queries()}
    for query_id in ("reg-001", "reg-002"):
        assert not CLAUSE_LEAK.search(queries[query_id]["question"]), query_id


def test_runner_gate_flags_missing_gold_as_fail() -> None:
    passed_metrics = {
        "document": {"recall@5": 1.0},
        "page": {"recall@5": 1.0},
        "chunk": {"recall@5": 1.0},
    }
    failed_metrics = {
        "document": {"recall@5": 0.0},
        "page": {"recall@5": 0.0},
        "chunk": {"recall@5": 0.0},
    }
    passed = QueryOutcome(
        query_id="reg-001",
        category="clause_specific",
        metrics=passed_metrics,
        chunk_recall5=1.0,
        dense_gap=0.05,
        near_tie_reproduced=True,
    )
    failed = QueryOutcome(
        query_id="reg-002",
        category="clause_specific",
        metrics=failed_metrics,
        chunk_recall5=0.0,
        dense_gap=None,
        near_tie_reproduced=None,
    )
    assert build_report({"corpus_version": "v1"}, [passed, failed])[
        "status"
    ] == "FAIL"
    assert build_report({"corpus_version": "v1"}, [passed])["status"] == "PASS"


def test_tool_level_regression_still_exists_in_engineering_suite() -> None:
    source = TOOL_REGRESSION.read_text(encoding="utf-8")
    assert (
        "test_search_tool_never_retrieves_single_chunk_on_request" in source
    ), "tool-level 9addb1a regression was removed or renamed"
    assert '{"query": "第四条 系统可用性", "top_k": 1}' in source or (
        '"query": "第四条 系统可用性"' in source and '"top_k": 1' in source
    )
    assert 'retriever.calls[0]["top_k"] == 3' in source
