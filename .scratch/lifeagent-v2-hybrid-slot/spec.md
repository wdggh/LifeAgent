# LifeAgent V2.3c Spec — Reserved Sparse Slot

Status: ready-for-review (no implementation before review approval)

## Problem Statement

V2.3b established that the sparse/BM25 channel does retrieve evidence the dense
channel misses — for `answer-013`, the seven-day-return rule (purchase p3) is
sparse rank 3 — but every fusion policy tested (equal RRF, dense-priority
supplement, weighted RRF 2:1) leaves that chunk outside the Agent's 4-chunk
round budget (fused rank 6 / 9 / 6 respectively). Dense-priority is a no-op
because sparse can only fill slots beyond the dense top-8; the equal and
weighted policies dilute dense ordering and regress easy-40. The binding
constraint is therefore **candidate-budget allocation**, not recall capability
or the fusion paradigm.

## Solution

Reserve one slot of the final output for the highest-ranked sparse chunk that
the dense list does not already cover. With a limit of L (10 for evaluation,
≤4 for the Agent), the Tool takes the dense top (L−1) in order, then appends
the best sparse-only chunk as the reserved slot. If the sparse channel has no
uncovered chunk (or is unavailable), the output falls back to the normal
dense-priority fill. Users get the dense ranking they already trust, plus a
guaranteed chance for the lexical evidence that dense missed — inside the
existing 4-chunk Agent budget and without changing any retrieval engine.

## User Stories

1. As a user asking a question whose key evidence is lexical ("七天退货"), I want lexical evidence to have a guaranteed place in the Agent's context, so that the answer is not assembled from semantic near-misses only.
2. As a user, I want my normal dense ranking preserved, so that adding the reserved slot does not shuffle the results I already get right.
3. As a user asking a question the dense channel fully covers, I want the reserved slot to be harmless, so that easy questions never regress.
4. As a user asking a cross-document question, I want one lexical-only chunk to be able to enter the context, so that both evidence families can be represented.
5. As a user, I want the reserved slot only used when the sparse channel actually found something new, so that we never waste a slot on a duplicate.
6. As a user, I want retrieval to stay bounded, so that the reserved slot must not increase the chunk budget.
7. As a user, I want sparse failures to degrade gracefully to the dense ordering, so that retrieval never breaks because of the lexical channel.
8. As the developer, I want the reserved chunk and the slot policy recorded in the AgentRun, so that the experiment can be attributed per case.
9. As the developer, I want the allocation policy fixed before running, so that slot count and ordering cannot be tuned after the fact.
10. As the developer, I want the same fixed hard-10/easy-40 split and thresholds as previous experiments, so that comparisons remain valid.
11. As the developer, I want `answer-013`'s purchase p3 tracked from sparse rank → reserved slot → Agent context → final citation, so that the hypothesis is verifiable end to end.
12. As the developer, I want the experiment to fail loudly if easy-40 regresses, so that a budget reallocation that hurts common questions is rejected.

## Implementation Decisions

- Add a fourth fusion mode, `reserved_slot`, to the existing sparse-channel
  configuration. Query expansion and single-query rewrite stay disabled; the
  dense retriever, BM25 index, tokenisation and candidate width (8 per channel)
  are unchanged. This experiment changes only the final allocation of slots.
- Allocation for final limit L: dense results in order, but the last slot is
  reserved for the best sparse result whose `chunk_id` is not already covered
  by the selected dense slots. Selection is deterministic (sparse rank, then
  chunk id). If no sparse-only chunk exists, the behaviour degrades to the
  dense-priority supplement already implemented in V2.3b.
- The reserved slot count is configurable (`query_sparse_reserved_slots`,
  default 1) but the pre-registered arm uses exactly 1; changing the count is a
  new experiment.
- Trace (`agent_runs.steps`, JSONB, no migration) adds `slot_policy`,
  `reserved_slot_chunk_id`, `reserved_slot_sparse_rank`, `dense_slot_count`,
  `sparse_slot_count` alongside the existing channel/fusion fields.
- Failure behaviour: sparse unavailable or no uncovered chunk → dense-priority
  fill with no reserved slot; the reason is recorded.
- `retrieval_count`, Tool signature, budgets and API contract stay unchanged;
  with the mode disabled the behaviour equals baseline-v2.0.2.

## Testing Decisions

- What makes a good test: external behaviour at the Tool seam with fake dense
  and sparse sources — dense order preserved, the reserved slot filled by the
  best sparse-only chunk, duplicates skipped, no-sparse case degrading to dense
  fill, and the budget (L=4 and L=10) respected.
- Modules under test: the reserved-slot allocator (pure function), the
  `search_knowledge` integration and trace fields, and the disabled-mode
  equivalence.
- Prior art: `tests/test_hybrid_retrieval.py` (dense-priority and weighted-RRF
  tests, fake channels) and the evaluation fake seams.
- No real LLM or external service is needed in unit tests.

## Experiment Protocol (pre-registered)

```text
A  dense-only      query_sparse_enabled=false            -> must equal baseline-v2.0.2
B  reserved slot   query_sparse_enabled=true, fusion_mode=reserved_slot,
                   reserved_slots=1, expansion/rewrite off
                   -> reports/experiment-v2.3c-reserved-slot.json

pass if:
  (i)   hard-10 chunk MRR@5 or NDCG@5 improves >= 0.03 vs baseline-v2.0.2
  (ii)  easy-40 regression <= 0.01
  (iii) reg-001/reg-002 gate stays PASS
  (iv)  answer-013 source_correctness = 1 (answer-010 remains ambiguity-only)

diagnostics:
  reserved_slot_used_count, reserved_slot_hit_gold_count,
  answer-013 purchase p3: sparse rank -> fused rank -> agent top-4?
```

## Out of Scope

- Cross-encoder reranking (V2.4); changes to BM25 parameters, tokenisation or
  index lifecycle; multi-variant query expansion; more than one reserved slot;
  any API/frontend/dataset change.

## Further Notes

- Evidence base: `reports/experiment-v2.3b-analysis.md` (three-arm ablation) and
  `reports/experiment-v2.3-analysis.md` (answer-013 channel deep dive).
- Architecture decision: `docs/adr/0012-reserved-sparse-slot.md`.
- If the reserved slot still fails the criteria, the next pre-registered step
  is V2.4 (wider candidates + cross-encoder reranking ordered down to the
  budget); if it succeeds, the slot policy becomes the default hybrid
  allocation and the reranker is evaluated on top of it.
- Tickets: 01 reserved-slot allocator + Tool integration + tests, 02 live
  A/B + 13-case answer rerun + analysis, 03 ADR/README/glossary closure.
