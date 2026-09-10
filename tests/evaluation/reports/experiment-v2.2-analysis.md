# V2.2 Query Expansion Experiment Analysis (2026-09-11)

Reports: `experiment-v2.2-A-baseline.json`, `experiment-v2.2-query-expansion.json`
(raw per-case outputs are gitignored).

## Setup validation

- A (tool path, expansion disabled, `--reset`) reproduced baseline-v2.0.2
  **exactly** (overall and hard/easy splits) → the tool path is a valid
  measurement of the same retrieval.
- B (expansion enabled): 43/50 queries produced 1 variant; 7 were skipped by
  the unique-identifier guard; 0 fallbacks; average expansion latency 931.7 ms.

## Metrics

| chunk metric | baseline v2.0.2 | A | B | B − base |
| --- | --- | --- | --- | --- |
| overall MRR@5 | 0.8373 | 0.8373 | 0.8433 | +0.0060 |
| overall NDCG@5 | 0.8061 | 0.8061 | 0.8097 | +0.0036 |
| hard-10 MRR@5 | 0.5867 | 0.5867 | 0.6167 | **+0.0300** |
| hard-10 NDCG@5 | 0.4974 | 0.4974 | 0.5124 | +0.0150 |
| easy-40 MRR@5 | 0.9000 | 0.9000 | 0.9000 | 0.0000 |

Pre-registered criteria: (i) hard MRR/NDCG +0.03 → **technically PASS, exactly at
the boundary**; (ii) easy regression ≤0.01 → PASS; (iii) reg-001/002 gate →
PASS; (iv) `answer-013` source_correctness = 1 → **FAIL** (0/0/0).

## Failure classification (per the agreed discipline)

For every hard case we compared the A per-case branch hits with the B per-case
branch hits (original branch + variant branch) and the runtime gold chunk set:

| class | count (hard-10) | meaning |
| --- | --- | --- |
| no_new_recall | 7 | the variant branch added no gold chunk that the original branch had not already retrieved |
| original_sufficient | 2 | A was already Recall@5=1 and MRR@5=1; expansion could only disturb it |
| rank_only_gain | 1 (`cd-003`) | no new gold chunk, but fusion reordered existing results higher |
| new_recall_but_fusion_missed | 0 | no case of "variant found new gold that RRF failed to rank in" |
| expansion_error | 0 | no timeout / error / entity-loss / empty variant in this run |

**Interpretation:** the entire +0.0300 hard-MRR gain comes from one case
(`cd-003`, +0.3 MRR) where RRF promoted an already-retrieved chunk; expansion
added **no new recall** in the hard subset. The threshold pass is therefore
fragile and does not demonstrate the intended mechanism. The dominant failure
type is "variant produced no effective new recall" — not a ranking bug and not
an execution error.

## Answer level (13 cases, expansion enabled)

- `answer-001..012` carry forward the v2.1 scores (11/12 source, 10/12
  completeness, 11/12 no-hallucination).
- `answer-013` (bike-specific single-turn) scored **0/0/0**: retrieval returned
  `bike_warranty_01` instead of `purchase_record_01` p2/p3, the seven-day return
  rule was not answered, and a generic return-policy sentence was produced.
- `answer-010` remains the frozen ambiguity/multi-turn case and is tracked only.

## Decision (no prompt tweaking in this step)

Per the agreed discipline, the expansion prompt is **not** modified now. The
recorded failure type is "no effective new recall", which points to the next
pre-registered experiments:

1. **V2.2b — complementary variants** (decomposition / document-vocabulary
   expansion / exact-term anchors) with the same equal-weight RRF and
   tie-break, evaluated on the same fixed hard-10.
2. **V2.3 — add the sparse/BM25 channel** into the same fusion; lexical
   evidence ("整机保修期", "七天退货", "购买记录") is the most plausible fix for
   `answer-013` and the exact-term/numeric failures.

Any variant-mix or weighting change must be pre-registered before its
experiment, exactly as this one was.
