"""Generate deterministic PDF fixtures from corpus Markdown sources.

The corpus Markdown is the single source of truth. Each document is split on
the explicit ``<!-- page-break -->`` marker; every segment becomes exactly one
PDF page. Stability is asserted on ``pypdf`` text extraction (page count,
anchors) by ``validate_corpus.py``, never on PDF bytes.

Development-only dependencies: reportlab, fonttools. The OFL CJK font subset
under ``fixtures/fonts/`` is committed; the source font is not required to
regenerate (regeneration only needs the subset).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate

FIXTURES = Path(__file__).resolve().parents[1]
CORPUS = FIXTURES / "corpus"
PDF_DIR = FIXTURES / "pdf"
FONT_DIR = FIXTURES / "fonts"
MANIFEST = CORPUS / "manifest.json"

PAGE_BREAK = "<!-- page-break -->"
FONT_FILE = FONT_DIR / "NotoSansSC-Subset.ttf"
FONT_NAME = "NotoSansSC"


def load_manifest() -> dict:
    with MANIFEST.open(encoding="utf-8") as handle:
        return json.load(handle)


def split_pages(text: str) -> list[str]:
    parts = text.split(PAGE_BREAK)
    return [part.strip("\r\n ") for part in parts if part.strip()]


def build_story(pages: list[str]) -> list:
    style = ParagraphStyle(
        "corpus",
        fontName=FONT_NAME,
        fontSize=10.5,
        leading=16,
        wordWrap="CJK",
    )
    story: list = []
    for index, page in enumerate(pages):
        for block in page.split("\n\n"):
            block = block.strip("\r\n ")
            if block:
                story.append(
                    Paragraph(
                        block.replace("\n", "").replace("\u3000", " "),
                        style,
                    )
                )
        if index < len(pages) - 1:
            story.append(PageBreak())
    return story


def generate_pdf(slug: str, target: Path, pages: list[str]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(target),
        pagesize=A4,
        leftMargin=24 * mm,
        rightMargin=24 * mm,
        topMargin=22 * mm,
        bottomMargin=22 * mm,
        title=f"{slug} synthetic fixture",
        author="LifeAgent synthetic corpus",
    )
    page_count = [0]

    def count_page(_canvas, _doc) -> None:
        page_count[0] += 1

    doc.build(
        build_story(pages),
        onFirstPage=count_page,
        onLaterPages=count_page,
    )
    if page_count[0] != len(pages):
        raise RuntimeError(
            f"{slug}: generated {page_count[0]} pages, expected {len(pages)} "
            "(page content overflowed; shorten the page or adjust layout)"
        )
    print(f"generated {target.name}: {page_count[0]} pages")


def main() -> int:
    if not FONT_FILE.exists():
        print(f"missing font subset: {FONT_FILE}", file=sys.stderr)
        return 2
    pdfmetrics.registerFont(TTFont(FONT_NAME, str(FONT_FILE)))

    manifest = load_manifest()
    generated = 0
    for entry in manifest["documents"]:
        if entry["file_type"] != "pdf":
            continue
        source = CORPUS / entry["source"]
        pages = split_pages(source.read_text(encoding="utf-8"))
        expected = int(entry["pages"])
        if len(pages) != expected:
            raise RuntimeError(
                f"{entry['slug']}: source has {len(pages)} pages, "
                f"manifest says {expected}"
            )
        generate_pdf(
            slug=entry["slug"],
            target=PDF_DIR / entry["file"].split("/")[-1],
            pages=pages,
        )
        generated += 1
    print(f"done: {generated} PDFs generated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
