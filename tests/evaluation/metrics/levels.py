"""Per-query, per-level retrieval metrics (V2.0-04).

Levels follow the locked definitions:

- document level: unique documents by first occurrence; gold item = the gold
  document id.
- page level: unique gold pages covered by chunks of the gold document, in
  first-covering-result order (ties by ascending page number).
- chunk level: unique chunks; relevant iff the chunk id is in the runtime gold
  set G derived by gold mapping (V2.0-03).

Recall@K and NDCG@K operate on these deduplicated level lists; MRR@5 operates
on raw retriever result order (first relevant result), matching the locked
definition.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.domain.models.search_result import SearchResult

from .mrr import reciprocal_rank_at_k
from .ndcg import ndcg_at_k
from .recall import recall_at_k

KS = (5, 10)


def _page_overlap(result: SearchResult, page: int) -> bool:
    start = result.start_page
    end = result.end_page if result.end_page is not None else start
    if start is None:
        return False
    return start <= page <= end


def compute_query_metrics(
    results: Sequence[SearchResult],
    gold_documents: Mapping[str, Sequence[int]],
    gold_chunk_ids: Sequence[str],
    *,
    has_gold: bool = True,
) -> dict | None:
    """Compute document/page/chunk metrics for one query (schema v2 gold).

    ``gold_documents`` maps every mandatory gold document id to its gold pages.
    Returns ``None`` for no-gold queries (``has_gold=False``): such queries are
    counted upstream but excluded from every metric average.
    """

    if not has_gold:
        return None
    docs_pages = {
        document_id: sorted(set(pages))
        for document_id, pages in gold_documents.items()
    }
    if not docs_pages or any(not pages for pages in docs_pages.values()):
        raise ValueError("gold documents and pages must not be empty")
    gold_docs = set(docs_pages)
    gold_chunks = set(gold_chunk_ids)

    # --- deduplicated level item lists --------------------------------
    doc_items: list[bool] = []
    page_items: list[bool] = []
    chunk_items: list[bool] = []
    seen_docs: set[str] = set()
    seen_pages: set[tuple[str, int]] = set()
    seen_chunks: set[str] = set()

    for result in results:
        if result.document_id not in seen_docs:
            seen_docs.add(result.document_id)
            doc_items.append(result.document_id in gold_docs)
        if (
            result.document_id in docs_pages
            and result.start_page is not None
        ):
            for page in docs_pages[result.document_id]:
                key = (result.document_id, page)
                if _page_overlap(result, page) and key not in seen_pages:
                    seen_pages.add(key)
                    page_items.append(True)
        if result.chunk_id not in seen_chunks:
            seen_chunks.add(result.chunk_id)
            chunk_items.append(result.chunk_id in gold_chunks)

    # --- raw-order relevance flags for MRR ----------------------------
    doc_relevant = [r.document_id in gold_docs for r in results]
    page_relevant = [
        r.document_id in docs_pages
        and r.start_page is not None
        and any(
            _page_overlap(r, page) for page in docs_pages[r.document_id]
        )
        for r in results
    ]
    chunk_relevant = [r.chunk_id in gold_chunks for r in results]

    level_items = {
        "document": (doc_items, len(gold_docs)),
        "page": (
            page_items,
            sum(len(pages) for pages in docs_pages.values()),
        ),
        "chunk": (chunk_items, len(gold_chunks)),
    }
    level_relevant = {
        "document": doc_relevant,
        "page": page_relevant,
        "chunk": chunk_relevant,
    }

    metrics: dict[str, dict] = {}
    for level, (flags, gold_total) in level_items.items():
        entry: dict[str, float] = {}
        for k in KS:
            entry[f"recall@{k}"] = recall_at_k(flags, gold_total, k)
        entry["mrr@5"] = reciprocal_rank_at_k(level_relevant[level], 5)
        entry["ndcg@5"] = ndcg_at_k(
            [1.0 if flag else 0.0 for flag in flags],
            5,
            gold_total=gold_total,
        )
        metrics[level] = entry
    return metrics
