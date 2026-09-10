# LifeAgent V2.0.2 Spec — Near-tie Measurement Fixture Revision

Status: ready-for-agent

## Problem

The v2.0.1 triage showed that reg-003/reg-004 (family near-tie pairs) report
`MRR@5 = 1.0` but `chunk Recall@5 = 0.5`: the two clauses of each pair still
live on the same long page, so the runtime gold set contains several chunks of
that page and clause ordering is not actually measured. This repeats the flaw
fixed earlier for the rental contract (clauses moved to separate pages).

## Boundary

This is an instrumentation / measurement-fixture revision, not a new
benchmark. The evaluation **query set and answer_cases are frozen**; only the
corpus pagination of the two warranty documents changes.

- Revised documents: `bike_warranty_01` (4 -> 5 pages), `air_purifier_warranty_01`
  (4 -> 5 pages): the "保修范围" and "非保修/流程" clauses move to adjacent
  pages (same pattern as rental clauses 4/5 on p8/p9).
- Other multi-chunk pages (purchase p2, manual p5, service p2, insurance p4)
  stay as-is: their `Recall < 1` is a legitimate page-coverage signal.
- No retrieval optimisation and no query/case changes.

## Versioning

- Dataset directory stays `synthetic-personal-kb-v2`; manifest gains
  `revision: "v2.0.2-instrumentation"`; query/answer_cases unchanged.
- New report `reports/baseline-v2.0.2.json` becomes the ACTIVE baseline;
  `baseline-v2.0.1.json` stays as historical (same dataset, earlier revision).
- Hard flags are re-derived by the triage run; reg-003/reg-004 stay
  clause_specific hard candidates (informational, not gate ids).

## Acceptance

```text
1. warranty clauses on separate pages; anchors/manifest/zones updated
2. regenerated PDFs pass validate_corpus (page counts, anchors, terms)
3. triage re-run writes hard flags and baseline-v2.0.2.json
4. reg-001/reg-002 gate still PASS; reg-003/004 now report clause ordering
   (MRR/NDCG) instead of a structural Recall=0.5 artefact
5. answer-level transcripts re-run on the revised corpus; prior 11/10/11
   carried forward unless outputs changed (then user confirms)
6. README switches ACTIVE baseline to v2.0.2, v2.0.1 marked historical
```

## Tickets

```text
V2.0.2-01 Split warranty near-tie clauses onto adjacent pages
V2.0.2-02 Re-triage and publish baseline-v2.0.2 (ACTIVE)
V2.0.2-03 Answer-level transcripts re-run and review carry-forward
```

01 -> 02 -> 03.
