# LifeAgent V2.3 Spec — Dense + Sparse/BM25 with RRF

Status: ready-for-agent

## Problem Statement

V2.2 showed that query expansion does not fix the hard cases: 7 of 10 hard
queries produced **no new recall** (the variants paraphrase the original),
2 were already fully solved by the original query, and the entire +0.0300 gain
came from one rank-only reorder. The remaining failures are lexical: exact
terms, numbers and document-specific wording ("七天退货", "整机保修",
"购买记录", "刹车皮", identifiers) where dense embeddings match the wrong
document family. `answer-013` is the cleanest example: the question names the
bicycle, yet retrieval returns the bike warranty document instead of the
purchase record that contains the 24-month warranty and the seven-day return
rule. The dense channel alone is not sensitive enough to those lexical
constraints.

## Solution

Add a sparse/BM25 lexical channel beside the dense channel and fuse the two
ranked lists with the same equal-weight Reciprocal Rank Fusion used in V2.2
(`k = 60`, dense-priority tie-break). The sparse channel is built per user from
the user's stored chunks, tokenised with jieba for Chinese, filtered by the same
`user_id`/`document_type`/`document_id` scoping as dense retrieval, and kept in
a lazy per-user cache invalidated when the user's corpus version changes.
Query expansion stays disabled for this stage so the experiment changes exactly
one thing: the presence of the lexical channel. Users get both semantic recall
and exact-term recall, and the Agent/API contract is unchanged.

## User Stories

1. As a user asking with exact wording ("七天无理由退货"), I want the lexical channel to match the document's exact phrasing, so that the right document is retrieved even when the embedding prefers another one.
2. As a user asking with a number or identifier, I want that token matched literally, so that order numbers, policy numbers and amounts are not lost.
3. As a user asking about a specific document ("我的自行车购买记录"), I want the sparse channel to respect document scoping, so that the correct document family wins.
4. As a user asking colloquially, I want the dense channel to keep providing semantic recall, so that paraphrase questions still work.
5. As a user, I want the two channels fused into one ranked list, so that I never have to know which retrieval method answered my question.
6. As a user, I want retrieval to stay fast, so that the sparse index must be cached rather than rebuilt on every search.
7. As a user, I want newly ingested documents to become searchable, so that the sparse cache invalidates when my corpus changes.
8. As a user, I want deleted documents to disappear from lexical search too, so that deletion remains complete.
9. As a user, I want sparse retrieval to fail open, so that an index problem degrades to dense-only instead of breaking search.
10. As the developer, I want the channels, per-channel hits and fusion scores recorded in the AgentRun, so that any gain can be attributed.
11. As the developer, I want dense-only, sparse-only and hybrid variants distinguishable in the trace, so that the four attribution classes (dense hit, sparse new recall, sparse hit but not fused, neither) can be measured.
12. As the developer, I want the fusion rule and weights fixed before the experiment, so that results cannot be tuned afterwards.
13. As the developer, I want the same fixed hard-10/easy-40 split and the same thresholds as previous experiments, so that comparisons stay valid.
14. As the developer, I want `answer-013` as the lexical regression target while `answer-010` stays an ambiguity case, so that lexical retrieval quality is measured on a well-posed question.

## Implementation Decisions

- A sparse/BM25 channel runs inside `search_knowledge` beside the dense channel;
  the Agent loop, Tool signature, API and `retrieval_count` semantics are
  unchanged. Query expansion is **disabled** during the V2.3 experiment.
- Engine: `rank_bm25` (BM25Okapi) with `jieba` tokenisation; ASCII tokens are
  lower-cased, Chinese text is segmented, numbers and identifiers are kept
  verbatim. BM25 parameters default `k1 = 1.5`, `b = 0.75`.
- Index scope and filters: one in-memory index per user, built from that user's
  stored chunks (document id, document type, page range, content) via the
  existing repository read seam; queries apply the same `document_type` and
  `document_id` filters as dense retrieval.
- Cache lifecycle: a Redis `kb:{user_id}:corpus_version` counter is bumped by
  the ingestion worker on successful ingest and by the API on document delete;
  the API lazily rebuilds a user's index when its cached version differs. If
  Redis is unavailable the reader falls back to a short TTL rebuild. (This is
  the recommended mechanism and is recorded for confirmation in the ticket.)
- Retrieval: dense top-8 and sparse top-8 per query (implementation constant),
  deduplicated by chunk id, fused with equal-weight RRF (`k = 60`) and a
  **dense-priority tie-break** (ties keep the dense branch's ordering), then
  truncated to the normal per-call budget (10 for evaluation, ≤ per-round chunk
  budget for the Agent).
- Failure behaviour: if the index cannot be built or the sparse query fails,
  the Tool proceeds dense-only and records the reason; retrieval never fails
  because of the sparse channel.
- Configuration: `query_sparse_enabled` (default false until the experiment
  passes), `query_sparse_candidate_k`, `query_sparse_bm25_k1`,
  `query_sparse_bm25_b`, `query_sparse_rrf_k`, `query_sparse_version_ttl_seconds`.
- Trace (`agent_runs.steps`, JSONB, no migration): `dense_hit_ids`,
  `sparse_hit_ids`, `per_channel_hits`, `sparse_index_version`,
  `sparse_index_rebuild_ms`, `sparse_fallback`, `sparse_fallback_reason`,
  `fusion_candidates`, `fusion_top`, `rrf_k`.
- Dependencies `rank_bm25` and `jieba` are added to production requirements
  (the sparse index is part of the retrieval path, not of the evaluation
  tooling).
- V2.4 will add a cross-encoder reranker on top of the fused candidates;
  query expansion remains available but disabled.

## Testing Decisions

- What makes a good test: external behaviour at the Tool seam with fake dense
  and fake sparse sources — the two channel queries are actually issued, the
  fused order follows RRF with the dense-priority tie-break, the filters and
  per-user isolation hold, and disabling the channel reproduces the baseline.
- Modules under test: tokenisation (Chinese segmentation, identifier/number
  preservation), BM25 ranking over a small in-memory corpus, per-user index
  isolation and filter handling, cache invalidation on version change,
  fail-open when the index cannot be built, and RRF fusion with dense-priority
  tie-break.
- Prior art: `tests/test_query_expansion.py` (fake LLM/retriever at the Tool
  seam, RRF tie test) and the evaluation fake seams in `tests/evaluation`.
- No new external service is introduced for tests; Redis interactions are
  faked.

## Experiment Protocol

```text
A  dense-only         query_sparse_enabled=false, expansion off -> must equal baseline-v2.0.2
B  dense + sparse     query_sparse_enabled=true,  expansion off -> reports/experiment-v2.3-hybrid.json

pass if:
  (i)   hard-10 chunk MRR@5 or NDCG@5 improves >= 0.03 vs baseline-v2.0.2
  (ii)  easy-40 regression <= 0.01
  (iii) reg-001/reg-002 gate stays PASS
  (iv)  answer-013 source_correctness = 1 (answer-010 tracked as ambiguity only)

attribution classes per case (recorded in the analysis report):
  dense_hit_only | sparse_new_recall | sparse_hit_but_fusion_missed | neither
```

## Out of Scope

- Cross-encoder reranking (V2.4); multi-variant query expansion (V2.2b);
  HyDE; query decomposition as a separate transformation; chunking, embedding
  or index-model changes; API/frontend changes; dataset changes beyond the
  already-added `answer-013`.

## Further Notes

- Comparison baseline: `reports/baseline-v2.0.2.json` (ACTIVE); answer-level
  references: `reviews/answer_review_v2.0.2.json` (12 cases), 
  `reviews/answer_review_v2.1.json`, `reviews/answer_review_v2.2.json`
  (13 cases, 11/10/11).
- Architecture decision: `docs/adr/0011-hybrid-dense-sparse-rrf.md`.
- The sparse channel is expected to help the exact-term / numeric / document
  scoping failures; this is a hypothesis to be tested, not a promised outcome.
- Tickets: 01 sparse channel + index lifecycle + fusion end-to-end, 02 live
  A/B with attribution and 13-case answer rerun, 03 ADR/README/glossary sync.
