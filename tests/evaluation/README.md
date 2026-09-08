# LifeAgent Evaluation (tests/evaluation)

This directory holds the synthetic evaluation assets for LifeAgent V2.0
(Evaluation & Baseline). It is **not** part of the production runtime.

## Safety rule (read before adding anything)

`fixtures/corpus/`, `queries.jsonl` and `answer_cases.jsonl` must only contain
**original, fictional synthetic data**. Never commit real personal documents,
names, addresses, phone numbers, ID-card numbers, or copyrighted text. This is
a public GitHub repository.

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
python tests/evaluation/dataset/validate_dataset.py
python tests/evaluation/fixtures/generators/validate_corpus.py
```

CI validates the evaluation framework itself; Live Evaluation (real ingestion +
real Retriever + DashScope embeddings) validates actual retrieval quality and
produces `reports/baseline-v2.0.json`.

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
