# LifeAgent V2 Spec — V2.0: Evaluation & Baseline

Status: ready-for-agent

## Problem Statement

V1 can retrieve and answer, but there is no way to prove whether a retrieval
change makes LifeAgent better. V2.0 freezes V1's Retriever as a repeatable
Baseline, builds a public, safe, regression-able Evaluation Dataset, and gives
every later V2 stage (Query Rewrite, Multi-Query, BM25/RRF, Reranker) a
measurable starting point. Principle: measure V1 first, then optimise.

## Solution

V2.0 delivers an Evaluation Harness only. It does not change the behaviour of
the production Retriever, Agent, or AgentService. The harness:

1. ingests a deterministic, synthetic personal corpus through the real V1
   ingestion pipeline (parse → chunk → embed → index) into an isolated
   evaluation collection;
2. runs queries through the real V1 `Retriever` (never an "evaluation
   retriever");
3. computes document/page/chunk-derived Recall, MRR, NDCG against runtime gold;
4. enforces the `9addb1a` regression gate;
5. supports an answer-level manual review that never blocks the retrieval
   baseline;
6. emits one controlled `baseline-v2.0.json` report.

## Boundaries

- V2.0 does not implement Query Rewrite, Multi-Query, BM25, RRF, Reranker,
  Context Optimization, or Retrieval Trace UI.
- Production retrieval/Agent code is not modified for evaluation purposes. The
  single allowed additive code change is `VectorRepository.fetch_document_chunks()`
  plus the `StoredChunk` domain type (needed for runtime gold mapping now and
  the sparse index later).
- Gold never stores chunk ids or document ids from a running system. The
  dataset stores only stable facts: document slug + pages (+ answer elements).
- No real personal documents, names, addresses, phone numbers, or copyrighted
  text may be committed. All corpus content is original and fictional.

## Controlled vocabulary (8 categories)

```text
simple_fact        semantic_rewrite   exact_term     numeric_date
clause             cross_paragraph    clause_specific    not_in_kb
```

- The first 7 categories appear in `queries.jsonl` and feed retrieval metrics.
- `not_in_kb` appears only in `answer_cases.jsonl` (answer-level review) and is
  excluded from retrieval metric averages.

## Corpus design (locked Q14/Q15)

Six synthetic documents, all original Chinese content, no PII:

| slug | file | document_type | pages | purpose |
| --- | --- | --- | --- | --- |
| `rental_contract_01` | PDF | contract | 9 | clauses, deposit, renewal, dates; page 8 clause 4 vs page 9 clause 5 as the cross-page near-tie pair |
| `insurance_policy_01` | PDF | contract | 6 | deductible, term, exclusions, claims materials across paragraphs |
| `employment_contract_01` | PDF | contract | 5 | probation, annual leave, non-compete, resignation notice |
| `purchase_record_01` | PDF | purchase_record | 4 | order id, invoice, returns, warranty period |
| `device_manual_01` | PDF | manual | 6 | model `ABC-2025-001`, error codes, FAQ |
| `personal_notes_01` | txt/markdown | note | 1 | renewal/return/subscription dates |

`queries.jsonl` contains 30 retrieval queries (regression included):
simple_fact 6, semantic_rewrite 5, exact_term 5, numeric_date 4, clause 5,
cross_paragraph 3, clause_specific 2 (`reg-001` on rental page 8, `reg-002`
on rental page 9).

Every query uses single-document gold: `gold.document` + `gold.pages[]`.
Cross-document questions are deferred to V2.1+.

`answer_cases.jsonl` contains 12 answer-level cases: 10 derived from retrieval
queries plus 2 `not_in_kb` cases.

## Directory layout (locked)

```text
tests/evaluation/
├── README.md                 # vocabulary CN/EN, privacy rules, usage
├── fixtures/
│   ├── corpus/               # markdown sources + manifest.json
│   ├── pdf/                  # committed generated PDFs
│   └── generators/           # PDF generator + font subset tooling
├── dataset/
│   ├── queries.jsonl
│   └── answer_cases.jsonl
├── mapping/gold_mapping.py
├── metrics/{recall,mrr,ndcg}.py
├── runners/retrieval_eval.py
└── reports/baseline-v2.0.json
```

## PDF determinism (locked Q18)

- Markdown is the single source of truth. Page boundaries come from explicit
  markers that the generator consumes and never renders into the PDF text.
- `reportlab` and `fonttools` are development dependencies only
  (`requirements-dev.txt`); the committed corpus PDFs and an OFL-licensed
  subset CJK font are committed under `fixtures/`.
- Stability is asserted on `pypdf.extract_text()` output, never on PDF bytes:
  page count, per-page anchor presence, and gold-page bounds. A drift check
  regenerates PDFs from markdown and compares extracted text with the
  committed PDFs.

## Dataset schema and validation

`queries.jsonl` (one case per line, `additionalProperties: false`):

```json
{"id": "eval-001", "question": "我的租房合同什么时候到期？", "category": "numeric_date",
 "gold": {"document": "rental_contract_01", "pages": [3]},
 "answer_elements": ["2027-02-28", "租期"]}
{"id": "reg-001", "question": "合同提前退租需要承担多少违约金？", "category": "clause_specific",
 "gold": {"document": "rental_contract_01", "pages": [8]},
 "answer_elements": ["提前退租", "一个月租金", "4500元"]}
{"id": "reg-002", "question": "合同到期后没有按时搬走要承担什么？", "category": "clause_specific",
 "gold": {"document": "rental_contract_01", "pages": [9]},
 "answer_elements": ["逾期腾退", "占有使用费", "一个月租金"]}
```

`answer_cases.jsonl` (12 cases):

```json
{"id": "answer-001", "question": "提前退租要付多少违约金？", "category": "clause",
 "expected_sources": [{"document": "rental_contract_01", "pages": [8]}],
 "answer_requirements": ["给出违约金金额", "说明来自第四条", "不得编造其他条款"]}
{"id": "answer-011", "question": "我的健身会员卡什么时候到期？", "category": "not_in_kb",
 "answer_requirements": ["明确说资料中没有找到", "不得给出日期"]}
```

Field semantics:

- `answer_elements`: semantic description / auxiliary annotation only; never
  used by retrieval metrics.
- `answer_requirements`: manual answer-level judgement conditions only.
- No chunk-level or id-level fields are allowed in the dataset.

Validation (fast mode): ids unique and `reg-` prefixed for clause_specific
regressions; category in the controlled vocabulary; question non-empty and
bounded; `document` exists in the manifest; every page is within the manifest
page count and has an anchor.

## Gold mapping (locked Q17)

For a query with gold pages P of document D:

```text
manifest slug
  → ingest-run document map (slug → real document id)
  → VectorRepository.fetch_document_chunks(document_id)
  → overlap rule: chunk.start_page <= p <= chunk.end_page for any p in P
  → G = deduplicated runtime gold chunk id set
```

`StoredChunk` (domain type, no embedding / user_id / vector metadata):

```text
chunk_id | content | start_page | end_page | chunk_index
```

The overlap rule (not equality) keeps the dataset valid across future chunker
changes, including cross-page chunks.

## Metrics (locked Q17)

For each query, run `Retriever.search(query, top_k=10)` and compute three
levels. Relevance:

```text
chunk-level: relevant iff chunk_id ∈ G
doc-level:   relevant iff the chunk belongs to gold document D
page-level:  chunk covers p ∈ P via the overlap rule; each gold page counted once
```

Level lists are deduplicated by first occurrence (document id / gold page /
chunk id respectively). Formulas per query:

```text
Recall@K = retrieved gold items / total gold items   (K = 5, 10)
MRR@5    = 1 / rank of the first relevant result; 0 if none
NDCG@5   = DCG@5 / IDCG@5 with binary relevance (rel ∈ {0,1})
           DCG = Σ rel_i / log2(i+1), IDCG = ideal top min(5, gold items)
```

- Queries without gold (`not_in_kb`) are counted but excluded from averages.
- Reported metrics are macro averages across queries, plus per-category
  breakdowns.
- Document/page-level metrics are diagnostics; chunk-level is the primary
  analysis level.

Regression gate: `reg-001`/`reg-002` must satisfy chunk-level Recall@5 = 1, or
the live report is FAIL. The dense score gap between the target clause and its
decoy is diagnostic only: `< 0.1` = near-tie reproduced; `>= 0.1` = noted as
not reproduced. Recall is the behaviour gate; score gap is information.

## Harness: fast / live (locked Q19)

- Fast: no Chroma, DashScope, Redis, or API. Runs schema validation, manifest /
  anchor / gold-bounds checks, metric unit tests, PDF text drift checks, and the
  `9addb1a` tool-level regression (kept in `tests/test_review_fixes.py`). CI:
  `pytest tests/evaluation/`.
- Live: PostgreSQL + Chroma + DashScope embedding only (no Redis, no ARQ
  worker, no FastAPI). Ingests the synthetic corpus by calling the real
  `KnowledgeService` pipeline directly under a dedicated evaluation user, in an
  isolated Chroma collection (name suffix `_eval`), then runs the real
  `Retriever` through the runner.

CI validates the evaluation framework; Live Evaluation validates real retrieval
quality. The README must never claim CI runs the full RAG evaluation.

## Answer-level review (locked Q16/Q17)

Twelve cases, manual, three binary axes:

```text
source_correctness | completeness | no_hallucination   (each 0/1)
```

No LLM-as-Judge in V2.0. Report status is `READY` when all 12 are reviewed,
otherwise `PARTIAL`. A partial answer-level review never blocks publishing the
retrieval baseline (retrieval READY + answer PARTIAL is a valid report state).

## Reports and commit policy

- `reports/baseline-v2.0.json` is the only controlled report committed to the
  repo (experiment, dataset version, retriever config, commit, three-level
  metrics, by-category metrics, regression results, near-tie diagnostic,
  answer-level status).
- `*.raw.json`, `*.log`, `*.tmp.json` are gitignored.
- No experimental number is hard-coded in source or README before a real run;
  placeholders read `TBD` / `baseline: pending`.

## Ticket plan and dependencies (locked)

```text
V2.0-01 Synthetic corpus & deterministic fixtures        (blocked by: none)
V2.0-02 Evaluation dataset & controlled vocabulary       (blocked by: 01)
V2.0-03 Gold mapping spec + StoredChunk + repository API (blocked by: 02)
V2.0-04 Evaluation metrics                               (blocked by: 03)
V2.0-05 Real ingestion & isolated evaluation harness     (blocked by: 01)
V2.0-06 Retrieval evaluation runner (fast/live)          (blocked by: 03, 04, 05)
V2.0-07 9addb1a regression suite                         (blocked by: 02)
V2.0-08 Answer-level evaluation dataset                  (blocked by: 02)
V2.0-09 V1 baseline experiment & report                  (blocked by: 06; 07 gate
                                                          effective through 06;
                                                          08 non-blocking)
```

## Out of Scope for V2.0

- Any change to retrieval quality or Agent behaviour (V2.1–V2.4 stages).
- Cross-document gold, graded relevance (3/2/1/0), LLM-as-Judge.
- New report tables or trace UI; `agent_runs` schema changes.
- Real personal data of any kind in the repository.
