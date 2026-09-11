# Measure the agent-context funnel, then fix retrieval scope before ranking

Status: accepted (2026-09-12)

V2.3c ended with a claim we could not actually verify: "the reserved slot put the
seven-day-return chunk into the Agent's context and the model still did not use
it, so the remaining bottleneck is answer synthesis". Re-reading the code showed
three measurement defects behind that claim. The evaluation runner called the
Tool with `top_k=10` and a 10-chunk `ToolContext`, while the Agent builds
`ToolContext(user_id=...)` with `CHUNKS_PER_ROUND = 4`, so every recorded
`Recall@10` described a set the Agent never receives. `agent_runs.steps`
recorded `result_count` and channel/fusion ids but never the returned chunk ids,
and `AgentChatResult.sources` is a per-document maximum over all rounds, so
nothing stored could separate "gold was retrieved" from "gold was in the
Agent's context". And because `max_retrievals` resets the budget per round, a
case can consume up to 12 chunks, so "top-4" was never the right unit.

V2.3d therefore measured instead of optimising. It adds
`agent_context_recall@K` (K = `CHUNKS_PER_ROUND`) computed from the chunks a
Tool call actually returned, recorded per call in the run trace
(`steps[].chunk_ids`, ids only), a budget-faithful evaluation mode
(`--agent-budget`) that calls the Tool exactly as the Agent does, and a
three-level funnel per answer case — retrieved → returned (consumed) → used —
with labels `not_retrieved`, `document_only`, `found_beyond_budget`,
`returned_not_used`, `used` and `not_applicable` for gold-less cases. The
interpretation rule was pre-registered: D1 (hard-10 `agent_context_recall@4`
≥ 0.90 **and** a `returned_not_used` case) means the constraint is evidence
utilisation; D2 (< 0.90) means it is still what reaches the Agent.

The measurement returned **D2**: hard-10 `agent_context_recall@4` = 0.70
(overall 0.90, easy 0.95; all-gold variant 0.78), while the capability arm
reproduced baseline-v2.0.2 exactly. The reserved slot filled 49/50 slots, was
gold once and rescued **zero** context misses, leaving hard-10 recall 0.0333 and
NDCG 0.0202 lower — so the V2.3c hypothesis is not supported at the production
budget. The same trace revised V2.3c's attribution directly: for `answer-013`
the Agent calls `search_knowledge` with `document_type="warranty"`, and the
seven-day-return rule lives in the purchase record, which that argument
excludes; sparse/BM25 runs under the same filter, so the reserved slot could
never have delivered it. Across four scored answer runs the one *stable*
`returned_not_used` case is `answer-007` (consequence of a breach not stated),
and the one case that flipped from 0/0/0 to 1/1/1 (`answer-010`) did so in the
single run where the purchase record reached the context.

V2.4 is therefore named **Agent Retrieval Scope Safety**: fix the Agent's own
over-narrowing of the search space and build the evaluation that catches it,
before adding ranking machinery. Priority order:

1. tool argument validation / calibration;
2. inappropriate hard-filter detection;
3. fallback / scope widening;
4. evaluation coverage for tool-argument shapes;
5. re-assess retrieval and reranking with the funnel in place.

The cross-encoder reranker is **deferred, not cancelled**: it addresses ordering
inside a candidate pool, while D2 shows the pool the Agent asks for is the
binding constraint.

Consequences: `steps[].chunk_ids` and `input.args_summary` are the audit trail
for any future retrieval claim, and a claim about what the Agent "had" without
them is not evidence. `source_correctness` is known to be weaker than it looks
(it reads the aggregated retrieved sources, not grounding), which is why the
funnel reports it beside the trace rather than instead of it. The reserved-slot
policy stays non-default. Any future V2.x proposal must state which funnel layer
it moves, and the budget-faithful mode — not the capability mode — is the
authority for agent-visible numbers.
