"""Unit tests for runtime gold mapping (V2.0-03).

Fast mode: fake StoredChunk values only; no Chroma, Embedding, Retriever, or
database. Metrics (Recall/MRR/NDCG) are deliberately out of scope here.
"""

import pytest

from app.domain.models.chunk import StoredChunk
from tests.evaluation.mapping.gold_mapping import (
    GoldMappingError,
    map_gold_chunks,
    resolve_document_gold,
    resolve_gold_chunks,
    union_gold_chunks,
)


def chunk(
    chunk_id: str,
    start_page: int,
    end_page: int | None = None,
    chunk_index: int = 0,
) -> StoredChunk:
    return StoredChunk(
        chunk_id=chunk_id,
        content=f"content of {chunk_id}",
        start_page=start_page,
        end_page=end_page if end_page is not None else start_page,
        chunk_index=chunk_index,
    )


def test_single_page_gold_single_chunk() -> None:
    chunks = [
        chunk("rental:p8:c1", start_page=8, chunk_index=0),
        chunk("rental:p7:c1", start_page=7, chunk_index=1),
        chunk("rental:p9:c1", start_page=9, chunk_index=2),
    ]
    assert map_gold_chunks([8], chunks) == {"rental:p8:c1"}


def test_single_page_gold_multiple_chunks() -> None:
    chunks = [
        chunk("rental:p8:c1", start_page=8, chunk_index=0),
        chunk("rental:p8:c2", start_page=8, chunk_index=1),
        chunk("rental:p9:c1", start_page=9, chunk_index=2),
    ]
    assert map_gold_chunks([8], chunks) == {
        "rental:p8:c1",
        "rental:p8:c2",
    }


def test_cross_page_chunk_overlap() -> None:
    chunks = [
        chunk("rental:7-9:c1", start_page=7, end_page=9, chunk_index=0),
        chunk("rental:10:c1", start_page=10, chunk_index=1),
    ]
    assert map_gold_chunks([8], chunks) == {"rental:7-9:c1"}


def test_multiple_gold_pages_union() -> None:
    chunks = [
        chunk("rental:p8:c1", start_page=8, chunk_index=0),
        chunk("rental:p9:c1", start_page=9, chunk_index=1),
        chunk("rental:p10:c1", start_page=10, chunk_index=2),
    ]
    assert map_gold_chunks([8, 10], chunks) == {
        "rental:p8:c1",
        "rental:p10:c1",
    }


def test_overlapping_chunks_deduped() -> None:
    stored = chunk("rental:p8:c1", start_page=8, chunk_index=0)
    # Defensive: a duplicate entry for the same chunk must collapse to one id.
    assert map_gold_chunks([8], [stored, stored]) == {"rental:p8:c1"}


async def test_different_document_never_enters_gold() -> None:
    class FakeChunkSource:
        def __init__(self) -> None:
            self.calls: list[str] = []
            self.by_document = {
                "doc_a": [chunk("a:p8:c1", start_page=8, chunk_index=0)],
                "doc_b": [chunk("b:p8:c1", start_page=8, chunk_index=0)],
            }

        async def fetch_document_chunks(self, document_id: str):
            self.calls.append(document_id)
            return self.by_document.get(document_id, [])

    source = FakeChunkSource()
    gold = await resolve_document_gold(source, "doc_a", [8])
    assert gold == {"a:p8:c1"}
    assert "b:p8:c1" not in gold
    assert source.calls == ["doc_a"]


async def test_document_not_found_raises() -> None:
    class EmptySource:
        async def fetch_document_chunks(self, document_id: str):
            return []

    with pytest.raises(GoldMappingError, match="no stored chunks"):
        await resolve_document_gold(EmptySource(), "missing_doc", [8])


def test_gold_page_out_of_coverage_raises() -> None:
    chunks = [chunk("rental:p8:c1", start_page=8, chunk_index=0)]
    with pytest.raises(GoldMappingError, match="do not overlap"):
        map_gold_chunks([10], chunks)


def test_empty_chunks_raises() -> None:
    with pytest.raises(GoldMappingError, match="no stored chunks"):
        map_gold_chunks([8], [])


def test_empty_gold_pages_raises() -> None:
    chunks = [chunk("rental:p8:c1", start_page=8, chunk_index=0)]
    with pytest.raises(GoldMappingError, match="must not be empty"):
        map_gold_chunks([], chunks)


async def test_resolve_multi_document_gold_returns_union() -> None:
    class FakeChunkSource:
        async def fetch_document_chunks(self, document_id: str):
            return {
                "doc_a": [chunk("a:p8:c1", start_page=8, chunk_index=0)],
                "doc_b": [chunk("b:p1:c1", start_page=1, chunk_index=0)],
            }[document_id]

    gold_entries = [
        {"document": "slug_a", "pages": [8]},
        {"document": "slug_b", "pages": [1]},
    ]
    per_document = await resolve_gold_chunks(
        FakeChunkSource(),
        {"slug_a": "doc_a", "slug_b": "doc_b"},
        gold_entries,
    )
    assert per_document == {"doc_a": {"a:p8:c1"}, "doc_b": {"b:p1:c1"}}
    assert union_gold_chunks(per_document) == {"a:p8:c1", "b:p1:c1"}


async def test_resolve_multi_document_gold_fails_when_one_leg_missing() -> None:
    class PartialSource:
        async def fetch_document_chunks(self, document_id: str):
            if document_id == "doc_a":
                return [chunk("a:p8:c1", start_page=8, chunk_index=0)]
            return []

    gold_entries = [
        {"document": "slug_a", "pages": [8]},
        {"document": "slug_b", "pages": [1]},
    ]
    with pytest.raises(GoldMappingError, match="no stored chunks"):
        await resolve_gold_chunks(
            PartialSource(),
            {"slug_a": "doc_a", "slug_b": "doc_b"},
            gold_entries,
        )
