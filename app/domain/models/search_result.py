"""Search result domain model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    document_id: str
    document_name: str
    content: str
    score: float
    start_page: int | None = None
    end_page: int | None = None
    document_type: str | None = None
