# V2.3b Fusion-Policy Ablation Analysis (2026-09-11)

Reports: `experiment-v2.3b-equal_rrf.json`,
`experiment-v2.3b-dense_priority.json`, `experiment-v2.3b-weighted_rrf.json`
(raw per-case outputs gitignored). Same dataset, same dense retriever, same
BM25 index, same candidate width (8 per channel); only the fusion policy
changed.

## Metrics (chunk level)

| arm | overall MRR@5 | overall NDCG@5 | hard-10 MRR@5 | hard-10 NDCG@5 | easy-40 MRR@5 |
| --- | --- | --- | --- | --- | --- |
| baseline v2.0.2 | 0.8373 | 0.8061 | 0.5867 | 0.4974 | 0.9000 |
| A equal RRF 1:1 | 0.7733 | 0.7516 | 0.5667 | 0.4410 | 0.8250 |
| B dense-priority supplement | 0.8373 | 0.8061 | 0.5867 | 0.4974 | 0.9000 |
| C weighted RRF 2:1 | 0.7833 | 0.7632 | 0.5833 | 0.4778 | 0.8333 |

Pre-registered criteria per arm: (i) hard +0.03 → all FAIL; (ii) easy
regression ≤0.01 → only B passes (0.0000); A and C FAIL; (iii) reg-001/002 gate
→ all PASS; (iv) `answer-013` source = 1 → all FAIL (0/0/0).

## Attribution (hard-10, per arm)

All three arms: `dense_hit_only` 9, `neither` 1 (`v2-039`),
`sparse_new_recall_kept` 0, `sparse_new_recall_dropped` 0. In the 50-query
benchmark, no hard case gains new gold recall from the sparse channel in any
arm.

## answer-013 diagnostic (per arm)

```text
arm               purchase ranks (fused)                  agent top-4
equal RRF         2, 3, 6                                  warranty, p1, p2, warranty
dense-priority    1, 8, 9                                  p1, warranty, warranty, warranty
weighted RRF 2:1  2, 3, 9                                  warranty, p1, p2, warranty
```

- `dense-priority` is a no-op for metrics because the dense top-8 already fills
  the evaluation top-10 and the agent top-4; sparse can only occupy slots
  beyond the budget. It is the only arm with no easy regression.
- The seven-day return chunk (purchase p3, sparse rank 3) never enters the
  agent's 4-chunk context under any arm.
- The dense-priority answer-level rerun still yields `answer-013` = 0/0/0
  (source `bike_warranty_01`, generic seven-day-return sentence); the other 12
  scores are unchanged (carry-forward 11/13, 10/13, 11/13).

## Conclusion

Fusion policy alone cannot fix the binding constraint. The evidence chain is:

```text
dense: p1 rank1, p2 rank8
sparse: p2 rank2, p3 rank3 (new lexical recall)
fusion: no policy puts p3 into the 4-chunk agent budget
  - dense-priority: sparse only fills slots 9-10 (no-op)
  - equal/weighted RRF: p3 lands at rank 6/9 and dense ordering is diluted
```

Next pre-registered options:

1. **V2.3c reserved sparse slot**: dense top-3 + the best sparse-only chunk in
   slot 4 (one reserved slot), same candidate width; tests whether reserving
   space for lexical evidence fixes `answer-013` without hurting easy-40.
2. **V2.4 reranker**: widen candidates (dense 8 + sparse 8) and let a
   cross-encoder order them down to the agent budget; this is the natural next
   step once fusion-policy variants are exhausted.

Both options must be pre-registered before running; no engine/tokenisation
changes are made in this step.
