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
