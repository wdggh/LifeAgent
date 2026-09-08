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
    rental_pages = None
    for entry in manifest["documents"]:
        raw = check_source(entry)
        all_text += raw
        check_pdf(entry)
        if entry["slug"] == "rental_contract_01":
            rental_pages = split_pages(raw)

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

    assert rental_pages is not None and len(rental_pages) == 9
    clause4, clause5 = rental_pages[7], rental_pages[8]
    heading4 = normalized("第四条　提前退租的违约责任")
    heading5 = normalized("第五条　逾期腾退的违约责任")
    assert heading4 in normalized(clause4) and heading5 not in normalized(clause4), (
        "clause 4 must live on page 8 only"
    )
    assert heading5 in normalized(clause5) and heading4 not in normalized(clause5), (
        "clause 5 must live on page 9 only"
    )
    shared = "违约金金额为一个月的租金"
    assert shared in clause4 and shared in clause5, (
        "clauses 4/5 must stay a near-tie pair (shared wording)"
    )

    page_total = sum(int(e["pages"]) for e in manifest["documents"])
    print(f"corpus ok: {len(manifest['documents'])} documents, "
          f"{page_total} pages, unique terms verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
