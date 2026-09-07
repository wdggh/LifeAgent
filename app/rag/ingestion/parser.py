"""Page-level document parser."""

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from app.rag.ingestion.errors import ParsingError


@dataclass(frozen=True)
class ParsedPage:
    page: int
    content: str


class DocumentParser:
    """Parse a stored file into per-page text.

    PDFs are read page by page so chunks can carry accurate page ranges.
    TXT and Markdown are treated as a single page.
    """

    def parse(self, path: Path, file_type: str) -> list[ParsedPage]:
        if file_type == "pdf":
            pages = self._parse_pdf(path)
        else:
            content = path.read_bytes().decode("utf-8", errors="replace")
            pages = [ParsedPage(page=1, content=content)]
        if not any(page.content.strip() for page in pages):
            raise ParsingError("Document contains no extractable text")
        return pages

    @staticmethod
    def _parse_pdf(path: Path) -> list[ParsedPage]:
        try:
            reader = PdfReader(str(path))
            pages = []
            for index, pdf_page in enumerate(reader.pages, start=1):
                pages.append(
                    ParsedPage(page=index, content=pdf_page.extract_text() or "")
                )
        except ParsingError:
            raise
        except Exception as exc:
            raise ParsingError(f"Failed to parse PDF: {exc}") from exc
        if not any(page.content.strip() for page in pages):
            raise ParsingError(
                "PDF contains no extractable text "
                "(possible scanned or empty document)"
            )
        return pages
