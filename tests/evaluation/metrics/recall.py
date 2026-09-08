"""Recall@K over ranked relevance flags (V2.0-04)."""

from __future__ import annotations

from collections.abc import Sequence


def recall_at_k(
    relevant_flags: Sequence[bool],
    gold_total: int,
    k: int,
) -> float:
    """Fraction of gold items retrieved within the first ``k`` positions.

    ``relevant_flags`` follows the deduplicated item order of one level
    (document / page / chunk). ``gold_total`` is the number of gold items at
    that level; it must be positive (no-gold queries are excluded upstream).
    """

    if gold_total <= 0:
        raise ValueError("gold_total must be positive")
    if k <= 0:
        raise ValueError("k must be positive")
    retrieved = sum(1 for flag in relevant_flags[:k] if flag)
    return retrieved / gold_total
