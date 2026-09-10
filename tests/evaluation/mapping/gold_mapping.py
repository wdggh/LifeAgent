"""Runtime gold mapping: dataset pages -> current stored chunks (V2.0-03).

The evaluation dataset stores stable facts only (document slug + pages), never
chunk ids. At runtime the runner maps a query's gold pages to the chunks the
current ingestion produced for that document, using the overlap rule
``chunk.start_page <= p <= chunk.end_page``.

Scope discipline:
- ``map_gold_chunks`` is pure and assumes ``chunks`` were fetched for exactly
  one document via ``VectorRepository.fetch_document_chunks``.
- ``resolve_document_gold`` performs that fetch through the repository seam and
  then maps, so cross-document contamination is impossible by construction.
- No Retriever, Embedding, or vector search is involved here; that belongs to
  the retrieval runner (V2.0-06).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from app.domain.models.chunk import StoredChunk


class GoldMappingError(RuntimeError):
    """Raised when gold pages cannot be mapped to current chunks."""


def map_gold_chunks(
    gold_pages: Sequence[int],
    chunks: Sequence[StoredChunk],
) -> set[str]:
    """Return the deduplicated chunk ids overlapping any gold page.

    Explicit failure modes:
    - empty gold pages: dataset mistake, no gold can be derived;
    - empty chunks: document not indexed (or not found) for this document id;
    - no overlap: gold pages lie outside the document's chunk page coverage.
    """

    pages = sorted(set(gold_pages))
    if not pages:
        raise GoldMappingError("gold pages must not be empty")
    if not chunks:
        raise GoldMappingError(
            f"document has no stored chunks (not found or not indexed): "
            f"gold pages {pages}"
        )
    gold = {
        chunk.chunk_id
        for chunk in chunks
        if any(chunk.start_page <= page <= chunk.end_page for page in pages)
    }
    if not gold:
        raise GoldMappingError(
            f"gold pages {pages} do not overlap any chunk of the document"
        )
    return gold


async def resolve_document_gold(
    chunk_source: Any,
    document_id: str,
    gold_pages: Sequence[int],
) -> set[str]:
    """Fetch one document's chunks via the repository seam and map gold pages.

    ``chunk_source`` must provide ``fetch_document_chunks(document_id)`` (the
    ``VectorRepository`` seam); only that document's chunks are ever mapped.
    """

    chunks = await chunk_source.fetch_document_chunks(document_id)
    return map_gold_chunks(gold_pages, chunks)


async def resolve_gold_chunks(
    chunk_source: Any,
    slug_to_document_id: Mapping[str, str],
    gold_entries: Sequence[Mapping],
) -> dict[str, set[str]]:
    """Map a schema-v2 gold array (all mandatory) to per-document chunk sets.

    Returns ``{document_id: gold_chunk_ids}``; the union of the values is the
    query's runtime ``G_chunks``. Every entry must resolve to at least one
    chunk, otherwise the mapping fails loudly (same rules as
    ``map_gold_chunks``).
    """

    gold_by_document: dict[str, set[str]] = {}
    for entry in gold_entries:
        document_id = slug_to_document_id[entry["document"]]
        chunks = await chunk_source.fetch_document_chunks(document_id)
        gold_by_document[document_id] = map_gold_chunks(
            entry["pages"], chunks
        )
    return gold_by_document


def union_gold_chunks(gold_by_document: Mapping[str, set[str]]) -> set[str]:
    union: set[str] = set()
    for chunk_ids in gold_by_document.values():
        union |= chunk_ids
    return union
