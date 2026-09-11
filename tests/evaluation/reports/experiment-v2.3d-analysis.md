# V2.3d Agent-Context Measurement Analysis (2026-09-11)

Reports: `experiment-v2.3d-capability-reproduction.json`,
`experiment-v2.3d-B-agent-budget-defaults.json`,
`experiment-v2.3d-C-agent-budget-reserved-slot.json`;
funnel tables `funnel-v2.3d-defaults.md`, `funnel-v2.3d-reserved-slot.md`
(raw per-case outputs gitignored).

## Setup validation

The capability arm (`top_k=10`, budget 10, defaults) reproduced
baseline-v2.0.2 **exactly** — `metrics` and `metrics_by_difficulty` compare
equal — so the run is valid before any agent-context number is read.

## The measurement defect this stage fixes

`retrieval_eval` used to call the Tool with `top_k=10` and a 10-chunk
`ToolContext`, while the Agent builds `ToolContext(user_id=...)` with
`CHUNKS_PER_ROUND = 4`. Every recorded "Recall@10" was therefore a capability
number for a set the Agent never receives. `--agent-budget` removes the gap: the
Tool is called exactly as the Agent calls it, so the measured set **is** the
consumed set.

## Chunk metrics at the production budget

| metric | baseline-v2.0.2 (capability, k=10) | B defaults (consumed, k=4) | C reserved slot (consumed, k=4) |
| --- | --- | --- | --- |
| overall MRR@5 / NDCG@5 | 0.8373 / 0.8061 | 0.8333 / 0.8013 | 0.8333 / 0.7973 |
| overall chunk recall | 0.8500 (@5) / 0.9100 (@10) | 0.8400 | 0.8333 |
| hard-10 MRR@5 / NDCG@5 | 0.5867 / 0.4974 | 0.5667 / 0.4737 | 0.5667 / **0.4535** |
| hard-10 chunk recall | 0.85 (@5) | 0.5667 | **0.5333** |
| easy-40 chunk recall | 0.9000 | 0.9083 | 0.9083 |
| `agent_context_recall@4` | not measurable | **0.90** (hard **0.70**, easy 0.95) | **0.90** (hard 0.70, easy 0.95) |

Two things stand out.

1. **The Agent sees materially less than the reports claimed.** hard-10
   consumption recall is 0.5667 and `agent_context_recall@4` on hard cases is
   0.70: in 3 of 10 hard cases the gold chunk never reaches the consumed
   window, so no answer can be right for the right reason.
2. **The reserved slot buys nothing here and costs a little.** It filled 49/50
   slots, was gold only once (`v2-019`, already in context), rescued **zero**
   context misses, and left hard-10 recall 0.0333 and NDCG 0.0202 lower. The
   V2.3c "displacement" story holds at the production budget too — it just
   shows up as a hard-case cost rather than an R@10 artefact.

Strictness check (any-gold vs all-gold, since 16 queries have multi-chunk
gold): `agent_context_recall@4` = 0.90 any-hit, 0.78 all-hit. The
pre-registered D1/D2 rule uses the generous any-hit definition, so the outcome
below is not an artefact of the choice.

## 13-case answer funnel

| arm | gold in context | answer-013 | answer-010 |
| --- | --- | --- | --- |
| defaults (run 1) | 10/11 | not in context | in context |
| defaults (run 2, enriched trace) | 9/11 | not in context | not in context |
| reserved slot (run 1) | 9/11 | not in context | not in context |
| reserved slot (run 2, enriched trace) | 8/11 | not in context | not in context |

At n=13 the retrieval half of the funnel is **noisy run to run** (±1–2 cases);
single-case narratives are not safe evidence.

### answer-013: the failure is upstream of retrieval

The enriched trace gives the actual Tool arguments for the first time:

```text
args  {"query": "自行车 整机保修期 七天退货", "top_k": 3,
       "document_type": "warranty"}
got   3 chunks, all warranty documents; sparse rank-3 chunk reserved
gold  purchase_record_01 p1-p3 — a purchase record, excluded by the filter
```

The Agent narrows the search to `document_type="warranty"`, and the seven-day
return rule lives in the purchase record. Sparse/BM25 runs under the same
filter, so the reserved slot can only return warranty documents. Both V2.3d
runs reproduce this identically.

This **revises the V2.3c conclusion**. V2.3c recorded "the evidence was in
context and the model did not use it → the failure moved to answer synthesis".
What the trace shows is that in these runs the evidence never arrived, because
the Agent's own tool argument excluded the gold document. Neither fusion nor a
reranker nor a synthesis prompt can fix that.

A second, quieter finding: the Agent asked for `top_k=3` in every call of both
runs, so the effective consumption window is 3, not the 4 the budget allows.
`MIN_TOP_K = 3` makes 3 the floor the model gravitates to.

## Decision applied (pre-registered)

```text
D1  hard-10 agent_context_recall@4 >= 0.90 AND a returned_not_used case
D2  hard-10 agent_context_recall@4 <  0.90

measured hard-10 agent_context_recall@4 = 0.70  ->  D2
```

**D2: the binding constraint is what reaches the Agent, not what the Agent does
with what it has.** V2.4 is therefore ranking / delivery work, and
evidence-aware synthesis work stays deferred.

The funnel also produced a third failure layer the pre-registration did not
anticipate — **agent tool-argument filtering** — which is neither ranking nor
synthesis. Its scope decision belongs to the user, not to this analysis.

## Open items

- The manual half of the funnel (did the answer *use* the evidence) is
  `pending_review`: the four V2.3d transcripts are new runs and have not been
  scored. D2 does not depend on them.
- `get_document` delivers page text, not chunks; no case here used it, but a
  future run must read those steps manually (`args` are recorded).
