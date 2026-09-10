"""Fast validator for synthetic-personal-kb-v2 (V2.0.1-04).

Reads only the v2 dataset (never the frozen v1 files) and enforces:

- schema v2 structure: ``schema_version``, array ``gold`` (all mandatory),
  controlled vocabulary incl. ``cross_document``, field whitelist, unique ids;
- category distribution (50 cases) and ``reg-001..reg-004`` placement;
- N1/N3/N4 rules with machine-checkable subsets; N2 is declared through
  ``difficulty_note``; N5 (answer uniqueness) is enforced by the authoring
  convention and audited via ``answer_elements``/decoy notes;
- D1: product-family documents >= 3 pages with at least one page > 1000 chars;
- D2: product-family documents declare a manifest near-tie zone whose pages
  cover a > 1000-char page; rental/insurance zone declarations stay valid;
- D3: cross-document gold spans distinct documents and at least one leg is a
  non-first page (single-page documents are exempt for their own leg);
- D4: manifest ``unique_terms`` occur exactly once across the corpus;
- D5: source page counts and per-page anchors match the manifest.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from tests.evaluation.datasets import paths

PAGE_BREAK = "<!-- page-break -->"
CATEGORIES = {
    "simple_fact",
    "semantic_rewrite",
    "exact_term",
    "numeric_date",
    "clause",
    "cross_paragraph",
    "clause_specific",
    "cross_document",
    "not_in_kb",
}
EXPECTED_COUNTS = {
    "simple_fact": 8,
    "semantic_rewrite": 10,
    "exact_term": 6,
    "numeric_date": 6,
    "clause": 6,
    "cross_paragraph": 4,
    "clause_specific": 4,
    "cross_document": 6,
}
QUERY_FIELDS = {
    "id",
    "schema_version",
    "question",
    "category",
    "gold",
    "answer_elements",
    "hard_candidate",
    "hard",
    "decoy_documents",
    "difficulty_note",
}
REQUIRED_QUERY_FIELDS = QUERY_FIELDS - {"hard"}
PRODUCT_DOCS = {
    "purchase_record_01",
    "device_manual_01",
    "bike_warranty_01",
    "bike_service_record_01",
    "air_purifier_purchase_01",
    "air_purifier_warranty_01",
}
CLAUSE_LEAK = re.compile(r"第[一二三四五六七八九十\d]+条")


def load_manifest(dataset: str) -> dict[str, Any]:
    return json.loads(paths.manifest_path(dataset).read_text(encoding="utf-8"))


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
                raise AssertionError(f"{path.name}:{line_no}: {exc}")
    return records


def split_pages(text: str) -> list[str]:
    return [
        part.strip("\r\n ")
        for part in text.split(PAGE_BREAK)
        if part.strip()
    ]


def char_len(text: str) -> int:
    return len(re.sub(r"\r|\n", "", text))


def check_queries(queries: list[dict], manifest: dict[str, Any]) -> None:
    page_map = {doc["slug"]: int(doc["pages"]) for doc in manifest["documents"]}
    assert len(queries) == 50, f"expected 50 queries, got {len(queries)}"
    ids: set[str] = set()
    counts: dict[str, int] = {}
    for query in queries:
        assert REQUIRED_QUERY_FIELDS <= set(query) <= QUERY_FIELDS, (
            f"{query['id']}: field whitelist"
        )
        assert query["schema_version"] == 2, query["id"]
        assert query["id"] not in ids, f"duplicate id {query['id']}"
        ids.add(query["id"])
        assert query["category"] in CATEGORIES, query["id"]
        assert query["category"] != "not_in_kb", query["id"]
        counts[query["category"]] = counts.get(query["category"], 0) + 1
        assert 4 <= len(query["question"]) <= 250, query["id"]
        assert isinstance(query["answer_elements"], list) and query[
            "answer_elements"
        ], query["id"]
        assert isinstance(query["hard_candidate"], bool), query["id"]
        assert isinstance(query.get("hard", False), bool), query["id"]
        assert not (query.get("hard") and not query["hard_candidate"]), (
            f"{query['id']}: hard requires hard_candidate"
        )
        assert isinstance(query["decoy_documents"], list), query["id"]
        assert isinstance(query["difficulty_note"], str), query["id"]

        gold = query["gold"]
        assert isinstance(gold, list) and gold, query["id"]
        gold_docs: set[str] = set()
        for entry in gold:
            assert set(entry) == {"document", "pages"}, query["id"]
            slug = entry["document"]
            assert slug in page_map, f"{query['id']}: unknown doc {slug}"
            gold_docs.add(slug)
            assert isinstance(entry["pages"], list) and entry["pages"]
            for page in entry["pages"]:
                assert (
                    isinstance(page, int) and 1 <= page <= page_map[slug]
                ), f"{query['id']}: page {page} out of range for {slug}"

        if query["category"] == "clause_specific":
            assert query["id"].startswith("reg-"), query["id"]
            assert not CLAUSE_LEAK.search(query["question"]), query["id"]

        if query["category"] == "cross_document":
            assert len(gold_docs) >= 2, f"{query['id']}: cross-doc gold"

        if query["hard_candidate"]:
            assert query["difficulty_note"], f"{query['id']}: note required"
            assert re.search(r"N[1-5]", query["difficulty_note"]), query["id"]
            decoys = query["decoy_documents"]
            assert decoys, f"{query['id']}: decoys required"
            assert all(slug in page_map for slug in decoys), query["id"]
            if query["id"].startswith("reg-"):
                if set(decoys) & gold_docs:
                    assert "同文档" in query["difficulty_note"] or (
                        "近义" in query["difficulty_note"]
                    ), query["id"]
            else:
                assert len(decoys) >= 2, f"{query['id']}: N3"
                assert not (set(decoys) & gold_docs), f"{query['id']}: decoy-gold"
        else:
            assert query["decoy_documents"] == [], query["id"]
            assert query["difficulty_note"] == "", query["id"]
    assert counts == EXPECTED_COUNTS, f"counts mismatch: {counts}"


def check_negative_and_position_rules(
    queries: list[dict], page_map: dict[str, int]
) -> None:
    for query in queries:
        if not query["hard_candidate"]:
            continue
        gold = query["gold"]
        if query["category"] == "cross_document":
            non_first = any(
                any(page > 1 for page in entry["pages"])
                for entry in gold
                if page_map[entry["document"]] > 1
            )
            assert non_first, f"{query['id']}: D3 needs a non-first page leg"
        elif len(gold) == 1:
            entry = gold[0]
            if page_map[entry["document"]] > 1:
                assert not set(entry["pages"]) == {1}, (
                    f"{query['id']}: N4 first-page-only gold"
                )


def check_corpus_rules(manifest: dict[str, Any], dataset: str) -> None:
    corpus = paths.corpus_dir(dataset)
    all_text = ""
    for doc in manifest["documents"]:
        source = corpus / doc["source"]
        assert source.exists(), f"missing source {source}"
        raw = source.read_text(encoding="utf-8")
        all_text += raw
        pages = split_pages(raw)
        expected = int(doc["pages"])
        assert len(pages) == expected, (
            f"{doc['slug']}: source pages {len(pages)} != manifest {expected}"
        )
        for page_no, anchor in doc["anchors"].items():
            normalized_page = re.sub(r"\s+", "", pages[int(page_no) - 1])
            assert re.sub(r"\s+", "", anchor) in normalized_page, (
                f"{doc['slug']} page {page_no}: anchor missing"
            )

        slug = doc["slug"]
        if slug in PRODUCT_DOCS:
            assert expected >= 3, f"{slug}: D1 needs >=3 pages"
            lengths = [char_len(page) for page in pages]
            assert any(length > 1000 for length in lengths), (
                f"{slug}: D1 needs a page > 1000 chars"
            )
            zones = doc.get("near_tie_zones", [])
            assert zones, f"{slug}: D2 zone declaration required"
            zone_pages = {
                page
                for zone in zones
                for page in zone["pages"]
            }
            assert any(
                page in zone_pages and lengths[page - 1] > 1000
                for page in range(1, expected + 1)
            ), f"{slug}: D2 zone must include a >1000-char page"

    for term in manifest.get("unique_terms", []):
        assert re.sub(r"\s+", "", all_text).count(term) == 1, term


def check_answer_cases(dataset: str, page_map: dict[str, int]) -> None:
    """Validate the v2 answer-level cases (12, incl. 2 not_in_kb)."""

    records = load_jsonl(paths.answer_cases_path(dataset))
    assert len(records) == 12, f"expected 12 answer cases, got {len(records)}"
    ids: set[str] = set()
    not_in_kb = 0
    for record in records:
        assert record["id"] not in ids, record["id"]
        ids.add(record["id"])
        assert record["category"] in CATEGORIES, record["id"]
        assert record["answer_requirements"], record["id"]
        if record["category"] == "not_in_kb":
            not_in_kb += 1
            assert not record.get("expected_sources"), record["id"]
        else:
            sources = record["expected_sources"]
            assert sources, record["id"]
            for source in sources:
                slug = source["document"]
                assert slug in page_map, record["id"]
                for page in source["pages"]:
                    assert 1 <= page <= page_map[slug], record["id"]
    assert not_in_kb == 2, "exactly two not_in_kb cases required"


def main(dataset: str | None = None) -> int:
    if dataset is None:
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--dataset",
            default=paths.V2,
            help="dataset to validate (expected: synthetic-personal-kb-v2)",
        )
        dataset = parser.parse_args().dataset
    assert dataset == paths.V2, "this validator is for synthetic-personal-kb-v2"
    manifest = load_manifest(dataset)
    assert manifest["corpus_version"] == paths.V2
    assert len(manifest["documents"]) == 10

    queries = load_jsonl(paths.queries_path(dataset))
    check_queries(queries, manifest)
    page_map = {doc["slug"]: int(doc["pages"]) for doc in manifest["documents"]}
    check_negative_and_position_rules(queries, page_map)
    check_corpus_rules(manifest, dataset)
    check_answer_cases(dataset, page_map)
    hard = sum(1 for q in queries if q["hard_candidate"])
    print(
        f"v2 ok: 10 documents / 50 queries, hard_candidates={hard}, "
        "schema v2 + N/D rules passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
