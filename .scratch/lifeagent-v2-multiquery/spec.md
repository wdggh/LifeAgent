# LifeAgent V2.2 Spec — Query Expansion / Multi-Query Retrieval

Status: ready-for-agent

## Problem Statement

V2.1 proved that replacing the user's query with a single LLM rewrite is
fragile: hard-10 chunk MRR@5 fell 0.5867 → 0.5667 and NDCG@5 fell
0.4974 → 0.4591, because the rewrite dropped discriminative terms and injected
dates into non-temporal questions, and the rewritten query changed between
runs. Mature systems (LangChain MultiQueryRetriever, LlamaIndex
QueryFusionRetriever, R2R hybrid search) do not bet retrieval correctness on
one transformation; they keep the original query and fuse several retrieval
lists. LifeAgent needs the same structural safety, and the `answer-010`
failure additionally showed that one answer case is ambiguous without a
product mention, so it must not be used as a single-turn retrieval criterion.

## Solution

When the Agent calls `search_knowledge`, the Tool keeps the **original query as
a first-class member** and adds **one generated query variant** (default 1)
produced by the defect-fixed variant generator. Both queries are retrieved in
parallel, results are deduplicated and fused with **equal-weight Reciprocal
Rank Fusion** (`k = 60`) where ties are broken in favour of the original
branch, and the fused list is truncated to the normal per-call output budget.
Users get the stable recall of their original wording plus the coverage of a
paraphrase, without any single LLM output being able to replace the query that
worked before.

## User Stories

1. As a user asking a colloquial question, I want my original wording to remain in the retrieval set, so that a weak paraphrase cannot remove the evidence my own words would have found.
2. As a user quoting exact terms ("刹车皮", "免赔额"), I want those terms preserved in at least one retrieval branch, so that exact matches are not lost.
3. As a user asking a merged multi-intent question, I want the variants to cover the different intents, so that the fused result contains evidence for every part.
4. As a user whose query contains a relative date ("去年买的"), I want the date resolved only when I actually said a relative date, so that unrelated questions are not polluted with today's date.
5. As a user, I want retrieval to stay fast, so that query expansion must not add unbounded latency.
6. As a user, I want an answer to be possible even when variant generation fails, so that the original query is still searched (never a dead end).
7. As a user asking a cross-document question, I want evidence from both required documents in the fused list, so that the answer can be complete.
8. As a user asking a clause-specific question, I want the semantically matching clause to rank above its near-tie neighbour, so that the cited article is correct.
9. As a user asking something my documents do not contain, I want "not found" to remain the outcome, so that expansion cannot invent evidence.
10. As the developer, I want the same `search_knowledge` call to still count as one retrieval, so that Agent budgets and existing tests keep their meaning.
11. As the developer, I want the variants, the per-variant hits and the fusion scores recorded in the AgentRun, so that every experiment can be replayed.
12. As the developer, I want one fixed, pre-registered merge rule (equal-weight RRF with original-priority tie-break), so that ordering cannot be tuned after looking at the numbers.
13. As the developer, I want a fixed hard/easy split from the v2.0.2 baseline, so that V2.2 is compared on exactly the same cases.
14. As the developer, I want a bike-specific single-turn answer case (`answer-013`) while `answer-010` stays as an ambiguity/multi-turn case, so that retrieval quality and question ambiguity are not conflated.

## Implementation Decisions

- Query expansion happens inside the `search_knowledge` Tool; the Agent loop,
  Tool signature, API contract and `retrieval_count` (one successful Tool call
  = one retrieval) are unchanged.
- The **original query is always present**; generated variants are supplemental
  and can never replace it. This is the core difference from V2.1, where a
  rewritten query replaced the original.
- Variant generator = the V2.1 rewriter with two defects fixed:
  date resolution happens only when the query contains an explicit relative
  date expression; entities, identifiers, numbers and discriminative nouns must
  be preserved (no free paraphrasing of key terms). Generation is deterministic
  (temperature 0 / provider-equivalent), so the same input yields the same
  variants.
- Variant count defaults to **1**; single-line variants, max 120 characters each;
  any generation failure (timeout, error, invalid output) yields zero variants
  and retrieval proceeds with the original query only (fail-open, never blocks).
- Retrieval: the original and each variant are searched in parallel; candidate
  budget per query defaults to 8; duplicates are removed by chunk identity.
- Fusion: **equal-weight Reciprocal Rank Fusion** (`score = Σ 1 / (k + rank)`,
  `k = 60`) with a deterministic **original-priority tie-break**: when two
  chunks have equal fused score, the chunk from the original branch wins. With
  exactly two branches this neutralizes the V2.1 dilution counterexample
  (original rank-1 correct vs rewrite rank-1 wrong are tied and the original
  wins). Weighted RRF (e.g. 1.5) is deliberately **out of scope for V2.2** and
  belongs to the multi-variant/multi-channel stage (V2.2b or V2.3), where it
  will be pre-registered before that experiment.
- Output: the fused list is truncated to 10 for evaluation and to the remaining
  per-round chunk budget (currently 4) for the Agent; `MIN_TOP_K` behaviour is
  unchanged.
- Configuration: `query_expansion_enabled` (default false until the experiment
  passes), `query_expansion_variants`, `query_expansion_candidate_k`,
  `query_expansion_rrf_k`, `query_expansion_timeout_seconds`,
  `query_expansion_max_tokens`. (`query_expansion_original_weight` exists with
  default 1.0 for the later multi-variant stage; V2.2 always uses 1.0.)
- Trace (`agent_runs.steps`, JSONB, no migration): `query_original`,
  `query_variants`, `expansion_fallback`, `expansion_fallback_reason`,
  `expansion_duration_ms`, `per_variant_hits`, `fusion_candidates`,
  `fusion_top`, `rrf_k`, `original_weight`.
- The V2.1 single-query rewrite switch stays available but disabled; V2.2
  supersedes it as the default expansion mechanism.
- V2.3 will add the sparse/BM25 channel into the same fusion step; V2.4 adds
  the cross-encoder reranker on top of the fused candidates.

## Testing Decisions

- What makes a good test: external behaviour at the Tool seam — the retrieval
  branches actually issued, the fused order, the trace, and the disabled-mode
  equivalence, all with scripted fakes.
- Modules under test: variant generator (date-only-when-explicit, entity
  preservation, determinism, fail-open), expansion retrieval (original always
  present, parallel candidates, dedupe), fusion (equal-weight RRF,
  original-priority tie-break, truncation to budget), and the AgentRun trace
  fields.
- Mandatory regression test: the two-branch tie counterexample — original
  rank-1 correct chunk vs rewrite rank-1 wrong chunk produces equal RRF scores
  and the **original branch must win the tie**; the test also documents that
  multi-variant weighting is a separate, later experiment.
- Prior art: `tests/test_query_rewrite.py` (fake LLM + recording retriever at
  the Tool seam) and the evaluation fake seams in `tests/evaluation`. No real
  LLM calls in unit tests.

## Experiment Protocol

```text
A  baseline   query_expansion_enabled=false, tool path -> must equal baseline-v2.0.2
B  expansion  original + 1 rewrite, equal-weight RRF + original tie-break
             -> reports/experiment-v2.2-query-expansion.json

pass if:
  (i)   hard-10 chunk MRR@5 or NDCG@5 improves >= 0.03 vs baseline-v2.0.2
  (ii)  easy-40 regression <= 0.01
  (iii) reg-001/reg-002 gate stays PASS
  (iv)  answer-013 (bike-specific single-turn case) reaches
        source_correctness = 1 in the rewrite-enabled answer run;
        answer-010 is tracked as an ambiguity/multi-turn case and is NOT a
        pass criterion
```

## Out of Scope

- Sparse/BM25 retrieval and hybrid fusion (V2.3); cross-encoder reranking
  (V2.4); HyDE and query decomposition as separate transformations; chunking,
  embedding or index changes; API/frontend changes; rewriting the frozen
  v2.0.2 dataset beyond adding `answer-013`; **multiple variants and RRF weight
  tuning** (V2.2b or V2.3).

## Further Notes

- Comparison baseline: `reports/baseline-v2.0.2.json` (dataset
  `synthetic-personal-kb-v2`, revision `v2.0.2-instrumentation`); answer-level
  reference: `reviews/answer_review_v2.0.2.json` (12 cases, 11/9/11) and
  `reviews/answer_review_v2.1.json` (12 cases, 11/10/11, non-causal note).
- Architecture decision: `docs/adr/0010-query-expansion-original-first-class-rrf.md`.
- `answer-010` remains frozen as an ambiguous question; `answer-013` is the
  bike-specific, single-turn version of the same information need.
- Tickets: 01 end-to-end expansion with equal-weight RRF + original tie-break,
  02 live A/B (single treatment) and 13-case answer rerun, 03
  ADR/README/glossary sync. Multi-variant/weight work is explicitly deferred.
