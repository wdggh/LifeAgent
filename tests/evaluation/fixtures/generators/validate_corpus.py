"""Validate synthetic corpus Markdown sources and generated PDF fixtures.

Fast mode (no Chroma / DashScope): checks page counts, per-page anchors,
chunk-splitting prerequisites, exact-term uniqueness, and the no-PII / no-gym
rules. PDF checks use pypdf ``extract_text`` on the committed fixtures.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

FIXTURES = Path(__file__).resolve().parents[1]
CORPUS = FIXTURES / "corpus"
PDF_DIR = FIXTURES / "pdf"
MANIFEST = CORPUS / "manifest.json"

PAGE_BREAK = "<!-- page-break -->"
UNIQUE_TERMS = [
    "RENT-2025-0310",
    "POL-2025-0042",
    "EMP-2024-0067",
    "PO-2025-0099",
    "INV-2025-0622",
    "ABC-2025-001",
]
MOBILE_RE = re.compile(r"1[3-9]\d{9}")
ID_RE = re.compile(r"\d{17}[\dXx]")
BANNED_WORDS = ["健身房", "健身"]


def split_pages(text: str) -> list[str]:
    parts = text.split(PAGE_BREAK)
    return [part.strip("\r\n ") for part in parts if part.strip()]


def normalized(text: str) -> str:
    return re.sub(r"\s+", "", text)


def check_manifest_structure(manifest: dict) -> None:
    assert manifest.get("corpus_version"), "missing corpus_version"
    slugs = [entry["slug"] for entry in manifest["documents"]]
    assert len(slugs) == len(set(slugs)), "duplicate document slugs"


def check_source(entry: dict) -> str:
    source = CORPUS / entry["source"]
    assert source.exists(), f"missing source: {source}"
    raw = source.read_text(encoding="utf-8")
    pages = split_pages(raw)
    expected = int(entry["pages"])
    assert len(pages) == expected, (
        f"{entry['slug']}: {len(pages)} source pages, expected {expected}"
    )
    for page_no, anchor in entry["anchors"].items():
        text = normalized(pages[int(page_no) - 1])
        assert normalized(anchor) in text, (
            f"{entry['slug']} page {page_no}: anchor not found: {anchor}"
        )
    return raw


def check_pdf(entry: dict) -> None:
    if entry["file_type"] != "pdf":
        return
    target = PDF_DIR / entry["file"].split("/")[-1]
    assert target.exists(), f"missing generated PDF: {target}"
    reader = PdfReader(str(target))
    assert len(reader.pages) == int(entry["pages"]), (
        f"{entry['slug']}: PDF has {len(reader.pages)} pages, "
        f"expected {entry['pages']}"
    )
    for page_no, anchor in entry["anchors"].items():
        page_text = normalized(reader.pages[int(page_no) - 1].extract_text() or "")
        assert normalized(anchor) in page_text, (
            f"{entry['slug']} PDF page {page_no}: anchor not found: {anchor}"
        )


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    check_manifest_structure(manifest)

    all_text = ""
    rental_p8 = None
    for entry in manifest["documents"]:
        raw = check_source(entry)
        all_text += raw
        check_pdf(entry)
        if entry["slug"] == "rental_contract_01":
            rental_p8 = split_pages(raw)[7]

    compact = re.sub(r"\s+", "", all_text)
    for term in UNIQUE_TERMS:
        count = compact.count(term)
        assert count == 1, f"exact term not globally unique ({count}x): {term}"

    assert not MOBILE_RE.search(all_text), "corpus contains a phone number"
    assert not ID_RE.search(all_text), "corpus contains an ID-card-like number"
    for word in BANNED_WORDS:
        assert word not in all_text, (
            f"corpus must not mention {word} (not_in_kb integrity)"
        )

    assert rental_p8 is not None
    p8_length = len(re.sub(r"\r\n|\n", "", rental_p8))
    assert p8_length > 1000, (
        f"rental page 8 must exceed the 1000-char chunk boundary "
        f"(got {p8_length}) to split clauses 4/5 into separate chunks"
    )
    assert "第四条" in rental_p8 and "第五条" in rental_p8
    assert "\n\n" in rental_p8, "clauses 4 and 5 must be separate paragraphs"

    page_total = sum(int(e["pages"]) for e in manifest["documents"])
    print(f"corpus ok: {len(manifest['documents'])} documents, "
          f"{page_total} pages, unique terms verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
