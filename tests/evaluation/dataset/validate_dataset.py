"""Fast schema validation for the evaluation dataset (V2.0-02).

Runs without Chroma / DashScope / Redis: checks structure, controlled
vocabulary, page bounds against the corpus manifest, category distribution,
regression placement, and the no-clause-leak rule for reg-001/reg-002.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from tests.evaluation.datasets import paths

CATEGORIES = {
    "simple_fact",
    "semantic_rewrite",
    "exact_term",
    "numeric_date",
    "clause",
    "cross_paragraph",
    "clause_specific",
    "not_in_kb",
}
EXPECTED_QUERY_COUNTS = {
    "simple_fact": 6,
    "semantic_rewrite": 5,
    "exact_term": 5,
    "numeric_date": 4,
    "clause": 5,
    "cross_paragraph": 3,
    "clause_specific": 2,
}
CLAUSE_LEAK = re.compile(r"第[一二三四五六七八九十\d]+条")
QUERY_FIELDS = {"id", "question", "category", "gold", "answer_elements"}
ANSWER_FIELDS = {
    "id",
    "question",
    "category",
    "expected_sources",
    "answer_requirements",
}


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise AssertionError(f"{path.name}:{line_no}: invalid JSON: {exc}")
    return records


def manifest_pages() -> dict[str, int]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {
        entry["slug"]: int(entry["pages"])
        for entry in manifest["documents"]
    }


def check_queries(records: list[dict], pages: dict[str, int]) -> None:
    ids: set[str] = set()
    counts: dict[str, int] = {}
    for record in records:
        assert set(record) == QUERY_FIELDS, f"{record.get('id')}: unexpected fields"
        assert record["category"] in CATEGORIES
        assert record["category"] != "not_in_kb", (
            "not_in_kb must not appear in queries.jsonl"
        )
        assert record["id"] not in ids, f"duplicate query id: {record['id']}"
        ids.add(record["id"])
        counts[record["category"]] = counts.get(record["category"], 0) + 1
        assert 4 <= len(record["question"]) <= 200
        assert isinstance(record["answer_elements"], list) and record[
            "answer_elements"
        ], f"{record['id']}: answer_elements must be a non-empty list"
        gold = record["gold"]
        assert set(gold) == {"document", "pages"}, f"{record['id']}: gold shape"
        slug = gold["document"]
        assert slug in pages, f"{record['id']}: unknown document {slug}"
        assert isinstance(gold["pages"], list) and gold["pages"], (
            f"{record['id']}: gold.pages must be a non-empty list"
        )
        for page in gold["pages"]:
            assert isinstance(page, int) and 1 <= page <= pages[slug], (
                f"{record['id']}: page {page} out of range for {slug}"
            )
        if record["category"] == "clause_specific":
            assert record["id"].startswith("reg-"), (
                f"{record['id']}: clause_specific ids must start with reg-"
            )
            assert not CLAUSE_LEAK.search(record["question"]), (
                f"{record['id']}: regression question must not leak the clause number"
            )
    assert counts == EXPECTED_QUERY_COUNTS, (
        f"category distribution mismatch: {counts}"
    )
    assert records[0]["id"] == "eval-001"
    reg_ids = [r for r in records if r["id"].startswith("reg-")]
    assert len(reg_ids) == 2
    reg_gold = {r["id"]: r["gold"] for r in reg_ids}
    assert reg_gold["reg-001"]["document"] == "rental_contract_01"
    assert reg_gold["reg-001"]["pages"] == [8]
    assert reg_gold["reg-002"]["document"] == "rental_contract_01"
    assert reg_gold["reg-002"]["pages"] == [9]


def check_answer_cases(records: list[dict], pages: dict[str, int]) -> None:
    ids: set[str] = set()
    not_in_kb = 0
    for record in records:
        assert set(record) <= ANSWER_FIELDS, f"{record.get('id')}: unexpected fields"
        assert record["category"] in CATEGORIES
        assert record["id"] not in ids, f"duplicate answer id: {record['id']}"
        ids.add(record["id"])
        assert isinstance(record["answer_requirements"], list) and record[
            "answer_requirements"
        ], f"{record['id']}: answer_requirements required"
        if record["category"] == "not_in_kb":
            not_in_kb += 1
            assert "expected_sources" not in record or not record[
                "expected_sources"
            ], f"{record['id']}: not_in_kb must have no expected_sources"
        else:
            sources = record["expected_sources"]
            assert isinstance(sources, list) and sources, (
                f"{record['id']}: expected_sources required"
            )
            for source in sources:
                slug = source["document"]
                assert slug in pages, f"{record['id']}: unknown document {slug}"
                for page in source["pages"]:
                    assert 1 <= page <= pages[slug], (
                        f"{record['id']}: page {page} out of range for {slug}"
                    )
    assert len(records) == 12, "answer_cases must contain 12 cases"
    assert not_in_kb == 2, "answer_cases must contain exactly 2 not_in_kb cases"


def _set_dataset(dataset: str) -> None:
    global MANIFEST, QUERIES, ANSWER_CASES
    MANIFEST = paths.require_manifest(dataset)
    QUERIES = paths.queries_path(dataset)
    ANSWER_CASES = paths.answer_cases_path(dataset)


def main(dataset: str | None = None) -> int:
    if dataset is None:
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--dataset",
            default=paths.active_dataset_name(),
            help="evaluation dataset directory name",
        )
        dataset = parser.parse_args().dataset
    _set_dataset(dataset)
    pages = manifest_pages()
    queries = load_jsonl(QUERIES)
    assert len(queries) == 30, f"queries.jsonl must contain 30 cases, got {len(queries)}"
    check_queries(queries, pages)
    answers = load_jsonl(ANSWER_CASES)
    check_answer_cases(answers, pages)
    print("dataset ok: 30 retrieval queries, 12 answer cases, all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
