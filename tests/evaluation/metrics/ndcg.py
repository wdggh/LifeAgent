"""NDCG@K with binary relevance (V2.0-04)."""

from __future__ import annotations

import math
from collections.abc import Sequence


def ndcg_at_k(
    gains: Sequence[float],
    k: int,
    gold_total: int | None = None,
) -> float:
    """Normalized discounted cumulative gain over the first ``k`` items.

    V2.0 uses binary relevance (1 = relevant, 0 = irrelevant), so gains are
    binary flags in deduplicated item order. IDCG is the ideal ordering of the
    best ``min(k, gold_total)`` relevant items, not the sorted actual gains:
    a query with 3 gold chunks and only 1 retrieved must not score 1.0.
    Returns 0.0 when nothing is relevant.
    """

    if k <= 0:
        raise ValueError("k must be positive")
    if gold_total is not None and gold_total <= 0:
        raise ValueError("gold_total must be positive")
    prefix = list(gains[:k])
    dcg = sum(
        gain / math.log2(index + 2)
        for index, gain in enumerate(prefix)
        if gain > 0
    )
    ideal_count = (
        min(k, gold_total)
        if gold_total is not None
        else sum(1 for gain in prefix if gain > 0)
    )
    idcg = sum(
        1.0 / math.log2(index + 2)
        for index in range(ideal_count)
    )
    return dcg / idcg if idcg > 0 else 0.0
