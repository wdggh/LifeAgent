# LifeAgent V2.3d Spec — Agent-Context Recall & Evidence-Use Diagnosis

Status: closed (2026-09-12) — D2 measured, V2.4 named Agent Retrieval Scope
Safety (ADR-0013). Ticket 03 records the closure.

## Problem Statement

V2.3c closed with a targeted pass and an unresolved question: the reserved slot
put `answer-013`'s sparse gold chunk into the retrieved set and source
correctness moved 0 → 1, yet the answer still did not state the seven-day rule.
That is only describable as "the failure moved to answer synthesis" if we can
show the evidence actually reached the model. Right now we cannot, for three
concrete reasons in the current code:

1. **Evaluation grants a budget production never grants.** The eval runner
   calls the Tool with `top_k=10` and
   `ToolContext(user_id=..., remaining_chunk_budget=10)`, while the real Agent
   builds `ToolContext(user_id=...)` (budget = `CHUNKS_PER_ROUND` = 4) and the
   Tool clamps `top_k = min(max(top_k, MIN_TOP_K), remaining_chunk_budget)` = 4.
   Reported `Recall@10` therefore measures retrieval *capability* on a set the
   Agent never receives. Every "the reserved slot displaced dense rank-9/10
   gold" statement is a statement about an invisible set.
2. **The trace does not record which chunks were consumed.** `agent_runs.steps`
   stores `result_count` plus channel/fusion metadata (`dense_hit_ids`,
   `sparse_hit_ids`, slot fields) but never the returned chunk ids, and
   `AgentChatResult.sources` is `_aggregate_sources(state.results)` — a
   per-document maximum over **all** rounds. Neither artifact can separate
   "gold was retrieved" from "gold was in the Agent's context". The V2.3c
   "Agent top-4 = [p1, bike_warranty, bike_warranty, p3]" chain was
   reconstructed by hand, not read from a stored trace.
3. **The Agent is multi-round, so "top-4" is the wrong unit.** `max_retrievals`
   is 3 and the budget resets per round, so a case can consume up to 12 chunks;
   `answer-013` in V2.3c ran `retrieval_count = 3`. Context recall has to be
   defined per Tool call *and* over the union of calls.

Without fixing these, any V2.4 decision is guesswork: we cannot tell "the
ranking put the evidence out of reach" from "the evidence was in front of the
model and it did not use it".

## Solution

V2.3d is a measurement stage. It changes no prompt, no reranker, no chunking, no
fusion policy and no budget. It adds a three-level funnel per case —
**retrieved → returned (consumed) → used** — and reports it as
`agent_context_recall@4`.

```text
corpus            →  retrieved   : channel/candidate stage (existing metrics)
Tool call (cap 4) →  returned    : agent_context_recall@K        ← new
final answer      →  used        : requirement coverage          ← existing review
```

The point of the stage is the decision rule at the end, not the number itself:
if gold is routinely inside the Agent's context but answers still miss the
fact, ranking is no longer the binding constraint and V2.4 should be
evidence-aware answer synthesis instead of a cross-encoder.

## User Stories

1. As the developer, I want `agent_context_recall@4` computed from the chunk set
   the Agent actually received, so that "in context" is a measurement, not an
   inference.
2. As the developer, I want each Tool call's returned chunk ids in the run
   trace, so that a multi-round case can be attributed per call and overall.
3. As the developer, I want a budget-faithful evaluation mode, so that the
   reported recall matches the production 4-chunk budget and not a 10-chunk
   capability budget.
4. As the developer, I want the capability metrics kept alongside the
   budget-faithful ones, so that earlier experiments stay comparable.
5. As the developer, I want the 13 answer cases classified by where the chain
   broke (`not_retrieved` / `retrieved_not_returned` / `returned_not_used` /
   `used`), so that a failure names a layer.
6. As the developer, I want the interpretation threshold fixed before the run,
   so that the V2.4 direction cannot be chosen after seeing the numbers.
7. As the developer, I want the diagnosis to stay manual and auditable for the
   answer layer, so that we do not introduce LLM-as-Judge to explain the
   numbers.
8. As the user, I want the next stage to be chosen by evidence rather than by
   the previous stage's momentum, so that effort goes to the layer that is
   actually failing.
9. As the developer, I want `answer-013`'s p3 tracked through all three levels,
   so that the V2.3c claim is either confirmed or corrected by the trace.
10. As the developer, I want no production default to change in this stage, so
    that the baseline and the diagnosis cannot contaminate each other.

## Implementation Decisions

- **Trace (production, no migration).** Each `search_knowledge` step in
  `agent_runs.steps` gains the returned chunk ids in rank order
  (`chunk_ids: [...]`, ids only, no content, length ≤ the per-round cap). The
  existing `result_count` stays. This is the only production change and it is
  additive instrumentation.
- **Budget-faithful eval mode.** `retrieval_eval live` gains a mode that calls
  the Tool exactly as the Agent does — `ToolContext(user_id=...)` (default
  budget) with `top_k = CHUNKS_PER_ROUND` — instead of the current
  `top_k=10, budget=10`. The K=10 mode remains and stays the default for
  historical comparability; `agent_context_recall@4` is computed from the
  budget-faithful run.
- **Metric definition (locked).**

  ```text
  per_call_context_recall@K =
      gold chunk present in the first K chunks returned by that Tool call
  agent_context_recall@4 =
      gold chunk present in ANY Tool call's returned set (union, deduped)
  first_call_context_recall@4 =
      gold chunk present in the FIRST Tool call's returned set
  ```

  K = `CHUNKS_PER_ROUND` = 4. Both the union and first-call variants are
  reported; a gap between them measures how much the multi-round loop is
  rescuing the first call.
- **Answer-side funnel.** `run_answer_transcripts` stores, per case, the
  per-call returned chunk ids (and the gold chunk ids for the case's expected
  sources), so the review can classify each case. Classification is a pure
  function over (gold ids, per-call returned ids, requirement coverage).
  Refined during ticket 01: the layer between "not retrieved" and "in context"
  splits, because "the document was hit but not the gold chunk" and "the gold
  chunk was returned but fell outside the consumed window" call for completely
  different next steps. Labels: `not_retrieved`, `document_only`,
  `found_beyond_budget`, `returned_not_used`, `used`, plus `not_applicable`
  for gold-less (`not_in_kb`) cases.
- **No tuning.** `CHUNKS_PER_ROUND`, `max_retrievals`, `MIN_TOP_K`,
  `top_k_default`, retrieval configuration and every feature flag keep their
  current values; the stage runs with production defaults
  (`QUERY_SPARSE_ENABLED=false`, `QUERY_EXPANSION_ENABLED=false`,
  `QUERY_REWRITE_ENABLED=false`) and, as a diagnostic arm only, with the V2.3c
  reserved slot enabled.
- The answer review criteria (`source_correctness`, `completeness`,
  `no_hallucination`) are unchanged; the funnel is added *beside* them, and
  `case_set_revision` remains `answer-cases-13`.

## Testing Decisions

- What makes a good test: the classifier and the metric are pure functions and
  are tested against hand-built gold/returned sets, including the multi-round
  cases (gold only in the second call), the capped case (gold at rank 5 of a
  wide result list is *not* in context), and empty/`not_in_kb` cases.
- Trace test: a Tool result yields `chunk_ids` in the step metadata in rank
  order, id-only, and the disabled-mode run is otherwise byte-identical to
  today's steps.
- Runner test: the budget-faithful mode clamps to `CHUNKS_PER_ROUND` with a
  fake retriever/Tool; the K=10 mode is unchanged.
- Transcript test: the recorded per-call ids round-trip, and a transcript with
  no steps is rejected rather than silently classified as `not_retrieved`.
- Prior art: `tests/evaluation/reviews/test_answer_review.py`,
  `tests/test_hybrid_retrieval.py`, and the fake seams in
  `tests/evaluation`.
- No real LLM or external service is needed in unit tests; only the live
  diagnosis run needs PostgreSQL + Chroma + DashScope.

## Experiment Protocol (pre-registered)

No A/B arm: this stage measures the existing system. The pre-registration is
the interpretation rule.

```text
live run 1 (budget-faithful, production defaults)
    -> agent_context_recall@4, first_call_context_recall@4,
       overall / hard-10 / easy-40, plus existing capability metrics
live run 2 (identity re-read of V2.3c: reserved_slot enabled)
    -> same metrics, to state how much context recall the slot actually buys
13-case answer rerun (budget-faithful, defaults)
    -> per-case funnel classification

decision (fixed before the run):
  D1  hard-10 agent_context_recall@4 >= 0.90
      AND at least one tracked case classified returned_not_used
      -> the binding constraint is evidence utilization;
         V2.4 = evidence-aware answer synthesis, reranker deferred
  D2  hard-10 agent_context_recall@4 < 0.90
      -> the binding constraint is still what reaches the Agent;
         V2.4 = ranking / reranking, synthesis work deferred
sanity: no production default changes; the capability metrics must reproduce
        the recorded baseline values, otherwise the run is void
```

The 0.90 threshold is fixed now, before any measurement. If the value lands
near the boundary, both numbers and the funnel are reported and no stage
starts without a fresh user decision.

## Out of Scope

- Prompt / system-message changes, answer-synthesis strategies, evidence
  citation prompts; cross-encoder reranking; chunk size/format changes;
  widening `CHUNKS_PER_ROUND` or `max_retrievals`; new fusion policies; dataset
  or answer-case changes; any change to production defaults; LLM-as-Judge.

## Further Notes

- Evidence base: `reports/experiment-v2.3c-analysis.md` (headline result plus
  the R@10 displacement cost), `reports/experiment-v2.3b-analysis.md`,
  `docs/adr/0012-reserved-sparse-slot.md`.
- Known measurement caveats this stage must correct or record: the eval
  runner's 10-chunk budget (item 1 above), the id-less step trace (item 2), the
  multi-round `sources` aggregate, and `source_correctness` being judged partly
  on that aggregate rather than on grounding.
- Draft tickets (to be published on approval): 01 trace `chunk_ids` +
  budget-faithful runner mode + funnel classifier + tests; 02 live
  budget-faithful runs + 13-case answer rerun + diagnosis report; 03 closure
  (ADR/README/CONTEXT) with the D1/D2 decision recorded.
