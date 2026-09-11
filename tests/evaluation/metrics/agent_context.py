"""Agent-context funnel: retrieved -> returned -> used (V2.3d).

Retrieval metrics answer "did the corpus contain the gold chunk in the top K
of a search?". They cannot answer what the Agent actually *received*, because
the runner historically called the Tool with a 10-chunk budget while production
caps a round at ``CHUNKS_PER_ROUND``. These helpers measure the consumed set
and locate the layer where a case failed.

Everything here is pure: no Retriever, no Chroma, no LLM.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

# A case with no gold chunk (``not_in_kb``) cannot be classified on this axis.
NOT_APPLICABLE = "not_applicable"
# Nothing from the gold documents came back at all.
NOT_RETRIEVED = "not_retrieved"
# The gold document was hit, but only through non-gold chunks.
DOCUMENT_ONLY = "document_only"
# The gold chunk was returned by a call, but outside the consumed window.
FOUND_BEYOND_BUDGET = "found_beyond_budget"
# The gold chunk reached the Agent, which did not use it.
RETURNED_NOT_USED = "returned_not_used"
# The gold chunk reached the Agent and the answer used it.
USED = "used"

FUNNEL_LABELS = (
    NOT_APPLICABLE,
    NOT_RETRIEVED,
    DOCUMENT_ONLY,
    FOUND_BEYOND_BUDGET,
    RETURNED_NOT_USED,
    USED,
)


def context_hit(
    gold_chunk_ids: Iterable[str],
    returned_chunk_ids: Sequence[str],
    k: int,
) -> bool:
    """Is a gold chunk among the first ``k`` chunks returned by one call?"""

    if k <= 0:
        raise ValueError("k must be positive")
    return bool(set(gold_chunk_ids) & set(returned_chunk_ids[:k]))


def agent_context_recall(
    gold_chunk_ids: Iterable[str],
    per_call_chunk_ids: Sequence[Sequence[str]],
    k: int,
) -> bool:
    """Did any Tool call return a gold chunk within its first ``k`` positions?

    The per-round budget resets every round, so the consumed set of a
    multi-round run is the union over calls, each capped at ``k``.
    """

    return any(
        context_hit(gold_chunk_ids, call, k) for call in per_call_chunk_ids
    )


def first_call_context_recall(
    gold_chunk_ids: Iterable[str],
    per_call_chunk_ids: Sequence[Sequence[str]],
    k: int,
) -> bool:
    """Same as ``agent_context_recall`` but only the first Tool call counts."""

    if not per_call_chunk_ids:
        return False
    return context_hit(gold_chunk_ids, per_call_chunk_ids[0], k)


def classify_funnel(
    *,
    gold_chunk_ids: Iterable[str],
    per_call_chunk_ids: Sequence[Sequence[str]],
    k: int,
    gold_document_ids: Iterable[str] = (),
    returned_document_ids: Iterable[str] = (),
    used: bool,
) -> str:
    """Label where a case sat in the funnel.

    ``used`` is the manual answer-level judgement that the answer states the
    required fact (for the answer review: requirement coverage). It is never
    inferred from retrieval, so the classifier stays auditable.
    """

    gold_chunks = set(gold_chunk_ids)
    if not gold_chunks:
        return NOT_APPLICABLE
    if agent_context_recall(gold_chunks, per_call_chunk_ids, k):
        return USED if used else RETURNED_NOT_USED
    returned_ids = {
        chunk_id
        for call in per_call_chunk_ids
        for chunk_id in call
    }
    if gold_chunks & returned_ids:
        # Found, but the consumed window of every call cut it off.
        return FOUND_BEYOND_BUDGET
    if set(gold_document_ids) & set(returned_document_ids):
        return DOCUMENT_ONLY
    return NOT_RETRIEVED


def summarize_funnel(labels: Iterable[str]) -> dict[str, int]:
    """Count labels, including zeros, so reports are comparable across runs."""

    counts = {label: 0 for label in FUNNEL_LABELS}
    for label in labels:
        if label not in counts:
            raise ValueError(f"unknown funnel label: {label!r}")
        counts[label] += 1
    return counts
