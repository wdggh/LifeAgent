"""MRR@K: reciprocal rank of the first relevant result (V2.0-04)."""

from __future__ import annotations

from collections.abc import Sequence


def reciprocal_rank_at_k(
    relevant_flags: Sequence[bool],
    k: int,
) -> float:
    """1 / rank of the first relevant result within the first ``k`` results.

    Flags follow raw retriever result order (one flag per result). Returns 0
    when no relevant result appears within the first ``k`` positions.
    """

    if k <= 0:
        raise ValueError("k must be positive")
    for index, flag in enumerate(relevant_flags[:k]):
        if flag:
            return 1.0 / (index + 1)
    return 0.0
