"""Reciprocal Rank Fusion for multi-query retrieval (V2.2, ADR-0010)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

from app.domain.models.search_result import SearchResult


@dataclass(frozen=True)
class FusionOutcome:
    results: list[SearchResult]
    scores: dict[str, float]
    candidate_count: int


@dataclass(frozen=True)
class ReservedSlotOutcome:
    results: list[SearchResult]
    reserved_chunk_id: str | None
    reserved_sparse_rank: int | None
    dense_slot_count: int
    sparse_slot_count: int
    fallback_reason: str | None


def reserved_slot_allocation(
    dense_results: Sequence[SearchResult],
    sparse_results: Sequence[SearchResult],
    *,
    limit: int,
    reserved_slots: int = 1,
) -> ReservedSlotOutcome:
    """Take dense top (L - reserved) and reserve the last slot(s) for a chunk
    that appears in NO dense candidate (not merely an unselected dense result).
    Falls back to dense-priority fill when no true sparse-only chunk exists.
    """

    if limit <= 0:
        return ReservedSlotOutcome([], None, None, 0, 0, "empty_limit")
    reserved_slots = max(0, min(reserved_slots, limit))
    keep = max(0, limit - reserved_slots)

    dense_unique: list[SearchResult] = []
    seen_dense: set[str] = set()
    for result in dense_results:
        if result.chunk_id in seen_dense:
            continue
        seen_dense.add(result.chunk_id)
        dense_unique.append(result)
    dense_all = {result.chunk_id for result in dense_unique}

    selected = dense_unique[:keep]
    selected_ids = {result.chunk_id for result in selected}
    ordered: list[SearchResult] = list(selected)

    reserved: list[SearchResult] = []
    reserved_rank: int | None = None
    for rank, result in enumerate(sparse_results, start=1):
        if len(reserved) >= reserved_slots:
            break
        if result.chunk_id in dense_all or result.chunk_id in selected_ids:
            continue
        reserved.append(result)
        if reserved_rank is None:
            reserved_rank = rank
    ordered.extend(reserved)
    fallback_reason = (
        "no_sparse_only_chunk" if len(reserved) < reserved_slots else None
    )

    seen = {result.chunk_id for result in ordered}
    for result in list(dense_unique[keep:]) + list(sparse_results):
        if len(ordered) >= limit:
            break
        if result.chunk_id in seen:
            continue
        seen.add(result.chunk_id)
        ordered.append(result)
    return ReservedSlotOutcome(
        results=ordered[:limit],
        reserved_chunk_id=reserved[0].chunk_id if reserved else None,
        reserved_sparse_rank=reserved_rank,
        dense_slot_count=len(selected),
        sparse_slot_count=len(reserved),
        fallback_reason=fallback_reason,
    )


def dense_priority_supplement(
    dense_results: Sequence[SearchResult],
    sparse_results: Sequence[SearchResult],
    *,
    limit: int | None = None,
) -> FusionOutcome:
    """Keep the dense ordering; append sparse-only chunks to fill slots.

    Sparse never reorders dense results: it only contributes chunks the dense
    list did not already cover.
    """

    ordered: list[SearchResult] = []
    seen: set[str] = set()
    for result in list(dense_results) + list(sparse_results):
        if result.chunk_id in seen:
            continue
        seen.add(result.chunk_id)
        ordered.append(result)
    candidate_count = len(ordered)
    if limit is not None:
        ordered = ordered[: max(0, limit)]
    return FusionOutcome(
        results=ordered, scores={}, candidate_count=candidate_count
    )


def reciprocal_rank_fusion(
    result_lists: Sequence[Sequence[SearchResult]],
    *,
    k: int = 60,
    weights: Sequence[float] | None = None,
    original_tie_break: bool = True,
    limit: int | None = None,
) -> FusionOutcome:
    """Fuse ranked lists with weighted RRF.

    ``result_lists[0]`` is treated as the original-query branch. When fused
    scores tie, the chunk whose best (branch, rank) key prefers the original
    branch (branch 0) wins, then the smaller rank, then the chunk id.
    """

    if not result_lists:
        return FusionOutcome([], {}, 0)
    if weights is None:
        weights = [1.0] * len(result_lists)
    if len(weights) != len(result_lists):
        raise ValueError("weights must match the number of result lists")
    if k <= 0:
        raise ValueError("k must be positive")

    scores: dict[str, float] = defaultdict(float)
    first_key: dict[str, tuple[int, int, str]] = {}
    by_id: dict[str, SearchResult] = {}

    for branch, results in enumerate(result_lists):
        for rank, result in enumerate(results, start=1):
            chunk_id = result.chunk_id
            scores[chunk_id] += weights[branch] / (k + rank)
            by_id.setdefault(chunk_id, result)
            branch_priority = (
                0 if (original_tie_break and branch == 0) else 1
            )
            key = (branch_priority, rank, chunk_id)
            if chunk_id not in first_key or key < first_key[chunk_id]:
                first_key[chunk_id] = key

    ordered = sorted(
        scores,
        key=lambda chunk_id: (-scores[chunk_id], first_key[chunk_id]),
    )
    if limit is not None:
        ordered = ordered[: max(0, limit)]
    return FusionOutcome(
        results=[by_id[chunk_id] for chunk_id in ordered],
        scores={
            chunk_id: round(scores[chunk_id], 6) for chunk_id in ordered
        },
        candidate_count=len(scores),
    )
