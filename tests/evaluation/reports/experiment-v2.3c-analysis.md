# V2.3c Reserved-Sparse-Slot Experiment Analysis (2026-09-11)

Reports: `experiment-v2.3c-A-baseline.json`,
`experiment-v2.3c-reserved-slot.json` (raw per-case outputs gitignored).

## Setup validation

- A (dense-only, tool path, `--reset`) reproduced baseline-v2.0.2 **exactly**.
- B (`reserved_slot`: dense top (L−1) + the highest-ranked sparse chunk that is
  in NO dense candidate), expansion/rewrite off, sparse candidate width 8.

## Metrics (chunk level)

| metric | baseline v2.0.2 | B reserved slot | delta |
| --- | --- | --- | --- |
| overall MRR@5 | 0.8373 | 0.8373 | 0.0000 |
| overall NDCG@5 | 0.8061 | 0.8061 | 0.0000 |
| overall Recall@5 | 0.8500 | 0.8500 | 0.0000 |
| overall Recall@10 | 0.9100 | **0.8767** | **−0.0333** |
| hard-10 MRR@5 | 0.5867 | 0.5867 | 0.0000 |
| hard-10 NDCG@5 | 0.4974 | 0.4974 | 0.0000 |
| easy-40 MRR@5 | 0.9000 | 0.9000 | 0.0000 |

Pre-registered criteria: (i) FAIL (no MRR/NDCG gain; Recall@10 actually falls
0.0333 because the reserved slot displaces dense rank-9/10 gold chunks);
(ii) PASS on the pre-registered easy MRR metric; (iii) reg-001/002 gate PASS;
(iv) **PASS — `answer-013` source_correctness = 1** (first criterion pass in the
V2.1→V2.3c sequence).

## Reserved-slot diagnostics (50 queries)

- reserved slot used: **49/50**; sparse-unavailable fallback: 1; the reserved
  chunk was a gold chunk in **1** case.
- The MRR@5/NDCG@5 metrics are structurally blind to this intervention: a change
  confined to the final consumed slot (rank 10 in evaluation, rank 4 for the
  Agent) cannot move a top-5 metric. Recall@10 does see it and shows the
  displacement cost.

## answer-013 chain (the hypothesis test)

```text
sparse channel:      purchase p3 (seven-day return) sparse rank 3
reserved slot:       p3 selected (dense rank 4 correctly NOT eligible)
Agent top-4 (L=4):   p1, bike_warranty, bike_warranty, p3
answer:              cites purchase_record_01, states 24-month warranty  -> source = 1
                     but says the seven-day rule is "not directly mentioned"
                     and falls back to a generic consumer-law sentence
                     -> completeness = 0, no_hallucination = 0
```

The retrieval-level hypothesis is confirmed (sparse new evidence now reaches the
Agent budget), and the failure has **moved from retrieval to answer synthesis**:
the model had purchase p3 in context yet did not quote its seven-day rule.

## Draft answer review (13 cases, pending user confirmation)

`reviews/answer_review_v2.3c.draft.json`: source 12/13 (answer-013 improved
0 → 1), completeness 10/13, no_hallucination 11/13; `answer-010` remains the
tracked ambiguity case.

## Conclusions and next options

1. **Instrumentation gap (recommended next)**: current metrics cannot measure an
   intervention that only changes the final consumed set. Add a pre-registered
   agent-context metric (gold chunk inside the Agent's top-4, i.e.
   `agent_context_recall@4`) and re-read V2.3c with it; also diagnose why the
   answer did not use the retrieved p3 (answer-side evidence use, not ranking).
2. **V2.4 reranker**: would improve ordering inside a wider candidate pool, but
   V2.3c has already put the missing evidence into the Agent budget; a reranker
   alone does not address the observed answer-synthesis failure.

Recommendation: do (1) before V2.4, so the next stage measures the layer where
V2.3c actually operates.
