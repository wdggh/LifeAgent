# V2.3 Hybrid (Dense + Sparse/BM25) Experiment Analysis (2026-09-11)

Reports: `experiment-v2.3-A-baseline.json`, `experiment-v2.3-hybrid.json`
(raw per-case outputs gitignored).

## Setup validation

- A (dense-only, tool path, `--reset`) reproduced baseline-v2.0.2 **exactly**.
- B (dense top-8 + sparse/BM25 top-8, equal-weight RRF k=60, dense-priority
  tie-break) ran with 0 sparse fallbacks; index version 10; average rebuild
  31.81 ms (first build 1590.61 ms, then cache hits).

## Metrics

| chunk metric | baseline v2.0.2 | A | B | B − base |
| --- | --- | --- | --- | --- |
| overall MRR@5 | 0.8373 | 0.8373 | 0.7733 | **−0.0640** |
| overall NDCG@5 | 0.8061 | 0.8061 | 0.7516 | **−0.0545** |
| overall Recall@5 | 0.8500 | 0.8500 | 0.8300 | −0.0200 |
| hard-10 MRR@5 | 0.5867 | 0.5867 | 0.5667 | −0.0200 |
| hard-10 NDCG@5 | 0.4974 | 0.4974 | 0.4410 | **−0.0564** |
| easy-40 MRR@5 | 0.9000 | 0.9000 | 0.8250 | **−0.0750** |

Pre-registered criteria: (i) hard +0.03 → **FAIL**; (ii) easy regression ≤0.01 →
**FAIL** (regression 0.075); (iii) reg-001/002 gate → PASS; (iv) `answer-013`
source = 1 → **FAIL** (still 0/0/0).

## Attribution (hard-10)

| class | count | meaning |
| --- | --- | --- |
| dense_hit_only | 9 | the gold chunk was already in the dense candidate list; sparse added no new gold |
| sparse_new_recall | 0 | no hard case where sparse contributed gold the dense list lacked |
| sparse_hit_but_fusion_missed | 0 | (at case level; see the answer-013 deep dive below) |
| neither | 1 (`v2-039`) | neither channel retrieved the gold candidate |

## answer-013 deep dive (the important evidence)

Direct channel inspection for "自行车的整机保修期和七天退货分别是怎样规定的？":

```text
dense : purchase_record p1 rank 1, purchase_record p2 rank 8
sparse: purchase_record p2 rank 2, purchase_record p3 rank 3, p1 rank 6
fused : bike_warranty p1 rank 1, purchase_record p1 rank 2,
        purchase_record p2 rank 3, bike_warranty p4 rank 4,
        purchase_record p3 rank 6
```

- sparse **did** add new lexical recall (purchase p3 = the seven-day return rule)
  and boosted p2.
- but equal-weight RRF promoted the wrong warranty chunk to rank 1 and pushed
  purchase p3 to rank 6, outside the Agent's 4-chunk round budget.
- final answer still cites only `bike_warranty_01` and falls back to a generic
  seven-day-return sentence → 0/0/0.

## Root cause

Equal-weight RRF over **heterogeneous** channels dilutes the stronger channel:
two lists of similar length interleave, so a dense gold chunk at rank r lands
around rank 2r in the fused list; dense rank-8 gold disappears from top-5, and
chunks that appear in both lists (often the wrong document family here) get
score boosts. The V2.2 equal-weight rule was safe because the two branches
(original and paraphrase) were highly correlated; with a genuinely different
lexical channel it is not.

## Decision (no immediate retuning)

Per the agreed discipline, the sparse engine, tokenisation and RRF weights are
**not** modified in this step. The recorded failure type is
"sparse adds some lexical recall, but the fusion policy destroys dense ranking".
Next pre-registered options:

1. **V2.3b fusion-policy ablation**: dense-priority supplement (dense results
   first, sparse fills remaining slots) vs weighted RRF (dense weight 2.0,
   sparse 1.0) vs the current equal-weight baseline, on the same fixed hard-10.
2. **V2.4 reranker**: keep the wider fused candidate set and let a cross-encoder
   restore ordering — but this changes two things at once unless V2.3b is fixed
   first.

Answer-level scores are unchanged from V2.2 (11/13, 10/13, 11/13) and the
`answer_review_v2.2.json` review therefore carries forward; `answer-013` remains
the primary lexical regression target.
