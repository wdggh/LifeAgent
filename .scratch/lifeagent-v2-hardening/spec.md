# LifeAgent V2.0.1 Spec — Benchmark Hardening

Status: ready-for-agent

## Problem Statement

The V2.0 baseline saturates: on `synthetic-personal-kb-v1`, document/page/chunk
Recall@5 and MRR@5 are all 1.0 and only chunk NDCG@5 (0.9973) shows any signal.
The benchmark cannot distinguish a future Query Rewrite / BM25 / Reranker
improvement. V2.0.1 hardens the benchmark so that later retrieval changes can
be proven, without optimising the Retriever itself.

## Boundary

V2.0.1 is an evaluation milestone, not a retrieval-optimisation milestone. It
does NOT implement Query Rewrite, Multi-Query, BM25, RRF, Reranker, chunker
changes, or embedding model changes.

The V2.0.1 triage/baseline runs use:

```text
Retriever implementation = V2.0 frozen
Embedding model          = V2.0 frozen (text-embedding-v3:1024)
Retrieval config         = V2.0 frozen (dense, top_k=10 for evaluation)

Corpus                   = synthetic-personal-kb-v2
Queries                  = v2 candidate set
```

The frozen retriever may ingest and search the NEW corpus; freezing applies to
the retriever code/config, not to the data it is measured on.

## Locked decisions

### Q26–Q30: cross-document evaluation constraints

- Multi-doc gold = **all mandatory** (every gold document is required to answer
  the question completely).
- V2.0.1 does **not** model optional/weighted gold; optional/background content
  goes to `decoy_documents` / `difficulty_note`, never into gold.
- `gold` becomes an array; every case carries `schema_version: 2`; single-doc
  cases are arrays of length 1.
- Dataset versions are physically isolated:

```text
tests/evaluation/datasets/
├── synthetic-personal-kb-v1/   FROZEN / historical (git mv of today's files)
└── synthetic-personal-kb-v2/   ACTIVE
tests/evaluation/reports/
├── baseline-v2.0.json          historical
└── baseline-v2.0.1.json        ACTIVE baseline
```

- Metric formulas stay unchanged; gold input generalises from one document to a
  list of documents:

```text
gold docs G_docs (all mandatory)
per-doc gold pages -> runtime G_chunks = union of page-overlap chunks

document-level: relevant = result belongs to any gold doc
                gold_total = len(G_docs); Recall = hits / gold_total
                MRR = 1 / rank(first relevant result)
page-level / chunk-level: existing formulas, applied to the union
```

### Q31–Q35: corpus and negative construction rules

Corpus v2 = 10 documents: the six v1 documents plus two product-family triads:

```text
Family A (bicycle):      purchase_record_01 (v1) + bike_warranty_01 (new)
                         + bike_service_record_01 (new)
Family B (purifier):     air_purifier_purchase_01 (new)
                         + air_purifier_warranty_01 (new)
                         + device_manual_01 (v1)
Single-doc context:      rental_contract_01, insurance_policy_01,
                         employment_contract_01, personal_notes_01
```

Auditable negative construction rules (machine-checkable where possible):

```text
N1 shared entity: decoy and gold belong to the same product family / domain
N2 shared semantic surface: decoy chunks overlap the query's topic words
N3 quantity gate: hard candidates declare >= 2 decoy documents (or >= 2 same-doc
   decoy chunks, declared in the note)
N4 position gate: gold page is not the document's first page (one cross-document
   leg may be page 1)
N5 answer uniqueness: decoys cannot fully answer the query (answer_elements are
   covered only by gold pages)
```

In-document engineering rules:

```text
D1 every product-family document >= 3 pages, at least one page > 1000 chars
   (>= 2 chunks per such page)
D2 every document has one "near-tie zone": adjacent same-topic conditions with
   >= 60% shared keywords (warranty period vs wear parts, deductible vs
   exclusions, error codes vs maintenance)
D3 cross-document gold pages live in different documents; at least one is
   non-first-page
D4 exact terms stay globally unique across the whole v2 corpus
D5 validator asserts page counts, near-tie zone size, page coverage, uniqueness
```

Query plan:

- total 50 cases; existing v1 easy cases are kept as "must not regress" anchors;
- new hard candidates >= 15, including 4–6 cross-document;
- controlled vocabulary adds `cross_document` as a retrieval category
  (`not_in_kb` remains answer-only);
- per-case `hard_candidate: true` is authored; `hard: true` is written only by
  the empirical triage run.

Diagnostic metadata (never used in metrics):

```text
decoy_documents: [slug, ...]   auditable negative source
difficulty_note: string        which N-rules apply and why
```

## Hard case lifecycle (Q34 boundary)

```text
author candidate (hard_candidate=true, decoy_documents, difficulty_note)
  -> ingest synthetic-personal-kb-v2 with frozen V2.0 dense retriever
  -> triage run: per-case MRR@5 / chunk NDCG@5
  -> hard=true iff MRR@5 < 1.0 OR chunk NDCG@5 < 0.95
  -> easy-under-hard-construction cases stay hard=false but remain in dataset
  -> baseline-v2.0.1.json reports overall + easy/hard splits
```

Triage raw per-case output is archived as `*.raw.json` (gitignored); the final
`hard: true` markings and the controlled report are committed.

## Report and comparison policy

- `reports/baseline-v2.0.json` (corpus v1) is historical and never re-run.
- `reports/baseline-v2.0.1.json` (corpus v2) is the ACTIVE baseline.
- Every later feature (V2.1 Query Rewrite, V2.2 BM25+RRF, V2.3 Reranker)
  compares only against the v2.0.1 baseline on the same dataset version.
- README lists both tables with their dataset versions and status.

## Answer-level review

Complete the 12 `answer_cases.jsonl` manual reviews (10 derived + 2
`not_in_kb`) using the V2.0-08 tooling; status READY or PARTIAL is recorded in
the v2.0.1 report and never blocks the retrieval baseline.

## Tickets

```text
V2.0.1-01 Dataset version layout migration        (blocked by: none)
V2.0.1-02 V2 corpus: 10 docs + decoy zones        (blocked by: 01)
V2.0.1-03 V2 queries: 50 cases, schema v2         (blocked by: 01, 02)
V2.0.1-04 V2 validator: schema v2 + N/D rules     (blocked by: 02, 03)
V2.0.1-05 Multi-doc mapping/metrics + runner param(blocked by: 01, 03)
V2.0.1-06 Triage run + baseline-v2.0.1            (blocked by: 04, 05)
V2.0.1-07 Answer-level 12-case review             (blocked by: none)
```

## Out of Scope

All retrieval optimisation (Query Rewrite / Multi-Query / BM25 / RRF /
Reranker), chunking changes, embedding changes, weighted/graded gold, and any
modification of the frozen v1 dataset or its baseline report.
