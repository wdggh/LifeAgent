# synthetic-personal-kb-v2

**Status: ACTIVE (being populated)**

Target: discriminative retrieval baseline for V2.0.1 Benchmark Hardening.

- 10 documents (two product-family triads + v1 single-doc context)
- 50 queries (schema v2: array gold, all mandatory, `cross_document` category)
- hard candidates >= 15 with auditable `decoy_documents` / `difficulty_note`
- rules N1-N5 (negative construction) and D1-D5 (document engineering)

Populated by tickets V2.0.1-02 (corpus) and V2.0.1-03 (queries). Until then,
active commands fail with a clear "dataset not ready" error.
