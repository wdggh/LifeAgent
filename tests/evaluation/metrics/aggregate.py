"""Macro and by-category aggregation of per-query metrics (V2.0-04)."""

from __future__ import annotations

from collections.abc import Iterable, Sequence


def _metric_keys(records: Iterable[dict]) -> list[str]:
    keys: set[str] = set()
    for record in records:
        keys.update(record)
    return sorted(keys)


def average_metrics(records: Sequence[dict]) -> dict[str, float]:
    """Macro average across per-query metric dicts.

    No-gold queries are expected to be filtered out before this call; every
    record here represents one query with gold.
    """

    keys = _metric_keys(records)
    if not records or not keys:
        return {}
    return {
        key: sum(record.get(key, 0.0) for record in records) / len(records)
        for key in keys
    }


def aggregate_by_category(
    categorized: Sequence[tuple[str, dict]],
) -> dict[str, dict[str, float]]:
    """Group per-query metrics by category and macro-average each group."""

    buckets: dict[str, list[dict]] = {}
    for category, record in categorized:
        buckets.setdefault(category, []).append(record)
    return {
        category: average_metrics(records)
        for category, records in sorted(buckets.items())
    }
