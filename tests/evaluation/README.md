# LifeAgent Evaluation (tests/evaluation)

This directory holds the synthetic evaluation assets for LifeAgent V2.0
(Evaluation & Baseline). It is **not** part of the production runtime.

## Safety rule (read before adding anything)

Any dataset's `fixtures/corpus/`, `queries.jsonl` and `answer_cases.jsonl`
must only contain **original, fictional synthetic data**. Never commit real
personal documents, names, addresses, phone numbers, ID-card numbers, or
copyrighted text. This is a public GitHub repository.

## Datasets

```text
tests/evaluation/datasets/
├── synthetic-personal-kb-v1/   FROZEN / historical (V2.0 baseline assets)
└── synthetic-personal-kb-v2/   ACTIVE (Benchmark Hardening; populated by
                                 V2.0.1-02/03)
tests/evaluation/reports/
├── baseline-v2.0.json          historical
├── baseline-v2.0.1.json        historical (superseded by v2.0.2)
└── baseline-v2.0.2.json        ACTIVE baseline (dataset revision v2.0.2)
```

The active dataset defaults to v2 (`EVAL_DATASET` overrides). Commands that
regress the frozen v1 framework pass `--dataset synthetic-personal-kb-v1`.

`synthetic-personal-kb-v2` query plan (50 cases, schema v2): simple_fact 8,
semantic_rewrite 10, exact_term 6, numeric_date 6, clause 6,
cross_paragraph 4, clause_specific 4 (`reg-001`..`reg-004`),
cross_document 6. Authored hard candidates: 16 (final `hard: true` is set by
the triage run, V2.0.1-06).

## Controlled vocabulary (8 categories)

| category | 中文 | meaning |
| --- | --- | --- |
| `simple_fact` | 简单事实 | single fact answerable from one chunk |
| `semantic_rewrite` | 语义改写 | user wording differs from document wording |
| `exact_term` | 精确术语 | question contains a unique code/model number |
| `numeric_date` | 数字/日期 | answer is a number, date, or derived date |
| `clause` | 条款规定 | answer lives in a specific clause or section |
| `cross_paragraph` | 跨段落/跨页 | evidence spans multiple chunks or pages |
| `clause_specific` | 条款定位回归 | regression: locate the semantically matching clause |
| `not_in_kb` | 知识库无答案 | answer-only; excluded from retrieval metrics |

The first 7 categories appear in `queries.jsonl` and feed retrieval metrics.
`not_in_kb` appears only in `answer_cases.jsonl` and is excluded from retrieval
metric averages.

## Distribution (queries.jsonl, 30 cases)

```text
simple_fact 6 | semantic_rewrite 5 | exact_term 5 | numeric_date 4
clause 5 | cross_paragraph 3 | clause_specific 2 (reg-001/reg-002)
```

All retrieval cases use single-document gold (`gold.document` + `gold.pages[]`).
Cross-document questions are deferred to V2.1+.

## Schema notes

- Gold never stores chunk ids or runtime document ids. The dataset stores only
  stable facts; runtime chunk mapping is derived from the manifest + current
  ingestion via page overlap.
- `answer_elements` is auxiliary annotation only; it never affects retrieval
  metrics.
- `answer_requirements` is used only by the manual answer-level review.
- `reg-001`/`reg-002` target rental page 8 (clause 4) and page 9 (clause 5)
  **without leaking the clause number** in the question, so MRR/Recall can
  measure whether the semantically matching clause outranks its near-tie decoy.

## Validation (fast mode)

No Chroma, DashScope, Redis, or API is needed:

```text
# framework regression on the frozen v1 dataset
python tests/evaluation/dataset/validate_dataset.py --dataset synthetic-personal-kb-v1
python tests/evaluation/tools/validate_corpus.py --dataset synthetic-personal-kb-v1

# active v2 dataset: schema v2 + N1-N5 / D1-D5 rules
python -m tests.evaluation.dataset.validate_v2
```

CI validates the evaluation framework itself; Live Evaluation (real ingestion +
real Retriever + DashScope embeddings) validates actual retrieval quality and
produces `reports/baseline-v2.0.json`.

Runner commands (from the repository root):

```text
# fast: schema + corpus/PDF + canned metric checks (no external services)
python -m tests.evaluation.runners.retrieval_eval fast \
    --dataset synthetic-personal-kb-v1

# live: ingest the corpus into the isolated _eval collection, evaluate all
# 30 queries with the real Retriever, enforce the regression gate, and write
# reports/baseline-v2.0.json
python -m tests.evaluation.runners.retrieval_eval live \
    --dataset synthetic-personal-kb-v1 --reset
```

Live requires PostgreSQL + Chroma + a DashScope key and is never run by CI.
Once synthetic-personal-kb-v2 is populated, run the same commands without the
`--dataset` override (default is v2).

## V2.0 baseline results (real run, 2026-09-09)

Source: `reports/baseline-v2.0.json` (controlled report, committed; dataset
`synthetic-personal-kb-v1`, historical).

| level | MRR@5 | NDCG@5 | Recall@5 | Recall@10 |
| --- | --- | --- | --- | --- |
| document | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| page | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| chunk | 1.0000 | 0.9973 | 1.0000 | 1.0000 |

- Regression gate: reg-001/reg-002 chunk Recall@5 = 1.0 → **PASS**.
- Near-tie diagnostic: reg-001 gap 0.0947, reg-002 gap 0.0135 (both < 0.1,
  near-tie reproduced).
- Answer-level review: `PENDING` (manual; see `reviews/answer_review_template.json`).

## V2.0.1 baseline results (historical, superseded by v2.0.2)

Source: `reports/baseline-v2.0.1.json`; dataset `synthetic-personal-kb-v2`
(10 documents / 50 queries / 16 hard candidates → 11 hard, 5
easy-under-hard-construction after empirical triage).

| level | MRR@5 | NDCG@5 | Recall@5 | Recall@10 |
| --- | --- | --- | --- | --- |
| document | 0.9167 | 0.9383 | 1.0000 | 1.0000 |
| page | 0.8873 | 0.9923 | 0.9900 | 0.9900 |
| chunk | 0.8873 | 0.8432 | 0.8933 | 0.9867 |

Difficulty split (chunk level):

| split | queries | MRR@5 | NDCG@5 | Recall@5 |
| --- | --- | --- | --- | --- |
| hard | 11 | 0.7303 | 0.5883 | 0.6667 |
| easy | 39 | 0.9316 | 0.9150 | 0.9573 |

- Regression gate: reg-001/reg-002 chunk Recall@5 = 1.0 → **PASS**
  (dense gaps 0.0947 / 0.0135, near-tie reproduced).
- reg-003/reg-004 are clause_specific hard candidates (not gates): chunk
  Recall@5 = 0.5 each, gaps 0.0134 / 0.0385 — the family near-ties are now
  measurable failures instead of saturated 1.0s.
- Answer-level review: **READY** (`reviews/answer_review_v2.json`, manual 0/1,
  user-confirmed): source_correctness 11/12, completeness 10/12,
  no_hallucination 11/12. Known failures kept as regression samples:
  `answer-007` (retrieval correct, answer incomplete) and `answer-010`
  (wrong document → wrong answer → hallucinated generic return policy).

All later V2.1/V2.2/V2.3 features must compare against this v2.0.1 baseline on
the same dataset version; the v2.0 table above stays as history only.

## V2.0.2 baseline results (ACTIVE, real run 2026-09-10)

Source: `reports/baseline-v2.0.2.json`; dataset `synthetic-personal-kb-v2`,
revision `v2.0.2-instrumentation` (warranty near-tie clauses split onto
adjacent single-chunk pages; query/answer_cases unchanged).

| level | MRR@5 | NDCG@5 | Recall@5 | Recall@10 |
| --- | --- | --- | --- | --- |
| document | 0.9207 | 0.9399 | 1.0000 | 1.0000 |
| page | 0.8373 | 0.9398 | 0.9333 | 0.9333 |
| chunk | 0.8373 | 0.8061 | 0.8500 | 0.9100 |

Difficulty split (chunk level): hard 10 queries (MRR 0.5867 / NDCG 0.4974 /
Recall@5 0.6167) vs easy 40 queries (0.9000 / 0.8832 / 0.9083).

- Gate: reg-001/reg-002 chunk Recall@5 = 1.0 → **PASS**.
- Measurement fix verified: reg-003 now Recall@5 = 1.0 with gap 0.0103
  (ordering measurable); reg-004 exposes a real ordering failure
  (Recall@5 = 0.0, gap −0.1039: the decoy outranks the target clause).
- Answer-level review: **READY** (`reviews/answer_review_v2.0.2.json`,
  user-confirmed): source_correctness 11/12, completeness 9/12,
  no_hallucination 11/12. 11 results carried forward from v2.0.1; only
  `answer-005` changed (the new answer omitted the online/mail submission
  method). Failures kept as regression samples: `answer-005`,
  `answer-007`, `answer-010`.

All V2.1/V2.2/V2.3 features compare against **this** baseline (v2.0.2) on the
same dataset revision.

## V2.1 Query Rewrite experiment (attempt 1 — criteria NOT met)

Source: `reports/experiment-v2.1-query-rewrite.json` (A run:
`experiment-v2.1-A-tool-baseline.json`).

- A (tool path, rewrite disabled) reproduced baseline-v2.0.2 **exactly**
  (overall + hard split identical) — the tool path is a valid measurement.
- B (rewrite enabled): 43/50 queries rewritten, 7 skipped by the
  unique-identifier guard, average rewrite latency 948 ms.

| chunk metric | baseline v2.0.2 | V2.1 B | delta |
| --- | --- | --- | --- |
| overall MRR@5 | 0.8373 | 0.8273 | -0.0100 |
| overall NDCG@5 | 0.8061 | 0.7940 | -0.0121 |
| hard-10 MRR@5 | 0.5867 | 0.5667 | -0.0200 |
| hard-10 NDCG@5 | 0.4974 | 0.4591 | -0.0383 |
| easy-40 MRR@5 | 0.9000 | 0.8925 | -0.0075 |

- Pre-registered criteria: (i) hard MRR/NDCG +0.03 → **FAIL**;
  (ii) easy regression ≤0.01 → PASS; (iii) reg-001/002 gate → PASS;
  (iv) answer-010 0/0/0 → at least source=1 → **FAIL** (still 0/0/0).
- Diagnosis: the rewrite drops discriminative wording (`cd-006`, `v2-040`)
  and injects the current date into non-temporal questions (`v2-014`); the
  rewritten query also varies between runs.
- Positive side effect: `answer-005` completeness improved 0 → 1 in the
  rewrite-enabled answer run (draft review `answer_review_v2.1.draft.json`,
  11/10/11, pending user confirmation).
- Next options: targeted prompt iteration (V2.1b) or V2.2 original+rewritten
  multi-query.

### V2.1 closure (2026-09-11)

- **Status: CLOSED / FAIL.** No V2.1b A/B: the failure is structural enough
  that the next step is an architecture change, and the two implementation
  defects (date injection on non-temporal queries, discriminative-term loss)
  move into V2.2's variant generator with unit tests.
- Production default flipped to `QUERY_REWRITE_ENABLED=false`; the single-query
  rewrite stays available as an experiment switch behind configuration.
- Answer-level: `answer-005` completeness 0 → 1 was observed in a single
  rewrite-enabled run and is recorded as a structural answer difference, **not**
  as causal evidence that query rewrite works (`reviews/answer_review_v2.1.json`,
  11/10/11). Future comparisons focus on retrieval/source-level effects.
- `answer-010` is reclassified as an **ambiguous / multi-turn disambiguation**
  case and is no longer a hard single-turn success criterion; `answer-013`
  (a bike-specific version of the same question) will be added for single-turn
  retrieval regression.

## V2.2 Query Expansion experiment (2026-09-11 — CLOSED, fragile boundary pass)

Reports: `reports/experiment-v2.2-A-baseline.json`,
`reports/experiment-v2.2-query-expansion.json`; full per-case classification in
`reports/experiment-v2.2-analysis.md`.

| chunk metric | baseline v2.0.2 | B (original + 1 rewrite, equal RRF) |
| --- | --- | --- |
| overall MRR@5 | 0.8373 | 0.8433 |
| hard-10 MRR@5 | 0.5867 | **0.6167 (+0.0300)** |
| hard-10 NDCG@5 | 0.4974 | 0.5124 |
| easy-40 MRR@5 | 0.9000 | 0.9000 |

- A (expansion off, tool path) reproduced baseline-v2.0.2 exactly.
- Criteria: (i) hard +0.03 → PASS at the exact boundary; (ii) easy ≤0.01 →
  PASS; (iii) gate → PASS; (iv) `answer-013` source = 1 → **FAIL** (0/0/0).
- Failure classification (hard-10): 7 `no_new_recall`, 2
  `original_sufficient`, 1 `rank_only_gain` (cd-003), 0
  `new_recall_but_fusion_missed`, 0 `expansion_error`. The whole +0.0300 comes
  from one rank-only reorder, so the pass is fragile and expansion added no new
  hard-subset recall.
- Answer level (13 cases, `reviews/answer_review_v2.2.json`, user-confirmed):
  11/13 source, 10/13 completeness, 11/13 no-hallucination; `answer-013` is
  0/0/0 (retrieved the warranty document instead of the purchase record),
  `answer-010` remains the tracked ambiguity case.
- **Why V2.3 next (not V2.2b):** the +0.0300 came from one rank-only reorder,
  while 7/10 hard cases had no new recall at all. The bottleneck is therefore
  not prompt phrasing, RRF weighting or the tie-break; it is the dense channel's
  weak lexical recall for exact terms, numbers and document-specific wording
  ("七天退货", "整机保修", "购买记录", "刹车皮", identifiers). Adding a
  sparse/BM25 channel into the same RRF attacks that failure mode directly, so
  V2.2b multi-variant work is skipped. Query expansion code stays in the
  repository but ships disabled (`QUERY_EXPANSION_ENABLED=false`), and the
  ACTIVE comparison baseline remains `baseline-v2.0.2.json`.

## Answers review

`answer_cases.jsonl` holds 12 manual answer-level cases (10 derived from
retrieval queries + 2 `not_in_kb`). Scoring axes are binary (0/1):

```text
source_correctness | completeness | no_hallucination
```

How to run a review:

```text
python tests/evaluation/reviews/answer_review.py template \
    --output reports/answer-review.raw.json
# fill the three 0/1 axes per case by hand against a real chat transcript
python tests/evaluation/reviews/answer_review.py check \
    --input reports/answer-review.raw.json
```

The check reports `READY` (all 12 cases fully scored) or `PARTIAL` (some axes
still pending). Definitions:

- `source_correctness`: cited Sources match the expected gold document/page.
  For `not_in_kb`, this means the answer must not cite any fabricated source
  and must clearly say the information was not found.
- `completeness`: every `answer_requirements` bullet is addressed.
- `no_hallucination`: nothing outside the corpus is invented.

No LLM-as-Judge in V2.0. A partial review never blocks publishing the
retrieval baseline: `Retrieval READY + Answer PARTIAL` is a valid report state.

## V2.3 Hybrid Retrieval experiment (2026-09-11 — criteria NOT met)

Reports: `reports/experiment-v2.3-A-baseline.json`,
`reports/experiment-v2.3-hybrid.json`; full attribution in
`reports/experiment-v2.3-analysis.md`.

| chunk metric | baseline v2.0.2 | B (dense + sparse, equal RRF) |
| --- | --- | --- |
| overall MRR@5 | 0.8373 | 0.7733 |
| hard-10 MRR@5 | 0.5867 | 0.5667 |
| hard-10 NDCG@5 | 0.4974 | 0.4410 |
| easy-40 MRR@5 | 0.9000 | 0.8250 |

- A (dense-only, tool path) reproduced baseline-v2.0.2 exactly.
- Criteria: (i) FAIL, (ii) FAIL (easy regression 0.075), (iii) gate PASS,
  (iv) `answer-013` still 0/0/0 → FAIL.
- Attribution: 9/10 hard cases `dense_hit_only`, 1 `neither`, 0
  `sparse_new_recall`; equal-weight RRF halved the effective dense depth and
  diluted the stronger channel. The `answer-013` deep dive shows sparse *did*
  add new lexical recall (purchase p3 = seven-day return) but fused it to rank
  6, outside the 4-chunk round budget, while promoting the wrong warranty chunk
  to rank 1.
- Conclusion: adding the lexical channel is data-supported, but the
  **fusion policy**, not the sparse engine, is the binding constraint. Next is a
  pre-registered V2.3b fusion-policy ablation (dense-priority supplement vs
  weighted RRF 2.0/1.0 vs equal weights); no prompt/engine changes in this step.
- Answer level: unchanged from V2.2 → `reviews/answer_review_v2.2.json` carries
  forward (11/13, 10/13, 11/13).

## V2.3b Fusion-policy ablation (2026-09-11 — fusion alone insufficient)

Reports: `reports/experiment-v2.3b-{equal_rrf,dense_priority,weighted_rrf}.json`;
full analysis in `reports/experiment-v2.3b-analysis.md`.

| arm (chunk) | hard-10 MRR@5 | hard-10 NDCG@5 | easy-40 MRR@5 |
| --- | --- | --- | --- |
| baseline | 0.5867 | 0.4974 | 0.9000 |
| equal RRF 1:1 | 0.5667 | 0.4410 | 0.8250 |
| dense-priority supplement | 0.5867 | 0.4974 | 0.9000 |
| weighted RRF 2:1 | 0.5833 | 0.4778 | 0.8333 |

- All three arms fail (i) hard +0.03 and (iv) `answer-013` source = 1; only
  dense-priority avoids the easy-40 regression, but it is a **no-op** for
  metrics because sparse only fills slots beyond the dense top-8 / agent top-4.
- answer-013 diagnostic: the sparse channel does retrieve the seven-day-return
  chunk (purchase p3, sparse rank 3), but no fusion policy brings it into the
  agent's 4-chunk budget (fused rank 6 / 6 / 9 for equal / weighted /
  dense-priority).
- Conclusion: the binding constraint is the interaction of fusion depth with the
  agent budget, not the fusion paradigm. Next pre-registered options: V2.3c
  reserved sparse slot (dense top-3 + one sparse-only slot) or V2.4 reranker
  over a wider candidate set.
