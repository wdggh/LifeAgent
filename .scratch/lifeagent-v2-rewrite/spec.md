# LifeAgent V2.1 Spec — Single-Query Rewrite

Status: ready-for-agent

## Problem Statement

On the hardened baseline (v2.0.2, real run), 10 of 50 retrieval queries are
hard: hard-subset chunk MRR@5 is 0.5867 and NDCG@5 is 0.4974, while the
answer-level review shows real end-to-end failures (`answer-005`,
`answer-007`, `answer-010`, the last being 0/0/0: wrong document retrieved →
wrong answer → hallucinated generic return policy). In every case the Agent
sends the user's raw wording straight to the embedding model, so colloquial
phrasing, unresolved relative dates and merged multi-intent questions limit
retrieval quality.

## Solution

When the Agent calls `search_knowledge`, the Tool first rewrites the retrieval
query into one retrieval-optimised query (colloquial → formal, synonym and
business-term expansion, relative dates resolved with the backend's current
date, proper nouns and identifiers preserved, multiple intents merged into one
query). Retrieval then runs on that rewritten query. If the rewrite fails for
any reason, retrieval falls back to the original query. The user-visible
behaviour of the Agent, API and budgets is unchanged; users simply get better
evidence on hard and multi-intent questions, with every rewrite step
replayable from the AgentRun trace.

## User Stories

1. As a user asking colloquially ("水管爆了把家里泡了"), I want the system to translate my wording into the document's own terms, so that the insurance clause is actually retrieved.
2. As a user referring to relative dates ("我去年买的…"), I want the system to resolve them against today's date, so that the right year is searched.
3. As a user asking a merged multi-intent question ("整机保修期和七天退货分别怎么规定"), I want both intents represented in one retrieval query, so that the answer is not built from only half the evidence.
4. As a user quoting an order/policy/model number, I want that identifier kept exactly as written, so that exact-term matching keeps working.
5. As a user describing a clause in everyday words ("提前走要赔多少"), I want the semantically matching clause to outrank near-tie clauses, so that the answer cites the right article.
6. As a user asking cross-document questions ("什么时候买的、保修到什么时候"), I want both documents' evidence retrieved, so that the combined answer is complete.
7. As a user whose question cannot be rewritten (provider timeout or bad output), I want the system to still search with my original question, so that a rewrite failure never turns into "no answer".
8. As a user, I want rewriting to respect a bounded timeout, so that chat latency does not balloon.
9. As a user asking about something not in my documents, I want the system to keep saying "not found" rather than inventing content from a rewrite.
10. As the developer, I want to enable/disable rewriting by configuration, so that A/B experiments run against the frozen baseline without code changes.
11. As the developer, I want the original query, rewritten query, fallback reason and rewrite latency recorded in the AgentRun, so that any experiment result can be replayed.
12. As the developer, I want rewriting to keep `retrieval_count` and per-round budgets unchanged, so that existing Agent behaviour and tests stay valid.
13. As the developer, I want the experiment success criteria fixed in advance, so that a result cannot be chosen by picking a favourable metric afterwards.
14. As the developer, I want the existing answer-level failures (`answer-005`, `answer-007`, `answer-010`) re-checked after the change, so that retrieval improvements are proven end-to-end.

## Implementation Decisions

- The rewrite happens inside the `search_knowledge` Tool (see ADR-0009); the
  Agent loop, Tool signature, API contract, frontend and budgets are unchanged.
- Exactly one rewritten query replaces the original for that retrieval; on any
  failure the original query is used (fail-open) with a recorded reason.
- Failure cases: provider timeout (default 8s), provider error, empty output,
  multi-line output, output over the length limit.
- Queries containing a unique identifier pattern skip rewriting entirely so
  exact-term retrieval is not damaged.
- Prompt rules: convert colloquial wording to document vocabulary, expand
  synonyms/business terms, resolve relative dates using the backend-injected
  current date, keep proper nouns and identifiers verbatim, merge multiple
  intents into one query, output a single line of at most 120 characters with
  no explanations.
- The existing `LLMClient` is reused (qwen-max/deepseek per configuration);
  rewrite max tokens 200; no caching in V2.1 (cost/latency measured first).
- Configuration: `query_rewrite_enabled` (default true for the shipped
  feature; experiments set false to reproduce the baseline),
  `query_rewrite_timeout_seconds`, `query_rewrite_max_tokens`.
- Trace: `agent_runs.steps` gains `query_original`, `query_rewritten`,
  `rewrite_model`, `rewrite_fallback`, `rewrite_fallback_reason`,
  `rewrite_duration_ms` (JSONB, no migration).
- `retrieval_count` and the per-round chunk budget semantics are unchanged.
- Multi-query retrieval, fusion/RRF, sparse retrieval and reranking are
  deliberately excluded (V2.2+); adding them later requires a new ADR.

## Testing Decisions

- What makes a good test: external behaviour at the Tool seam — given a
  scripted rewrite, the query actually handed to retrieval is the rewritten
  one; given a rewrite failure, it is the original; nothing about internal
  prompt plumbing is asserted.
- Modules under test: the query rewriter (guards + fallback), the
  `search_knowledge` integration (rewrite → retrieval → trace fields), and the
  experiment harness argument/flag handling.
- Prior art: `tests/test_review_fixes.py` already uses ScriptedFakeLLM and
  RecordingRetriever at the Tool seam; the evaluation fake seams
  (`tests/evaluation`) are the precedent for A/B harness tests.
- No real LLM is called by unit tests; live effect measurement is the
  experiment run (A/B) plus the 12 answer-level transcripts.

## Experiment Protocol

```text
run A (baseline)  query_rewrite_enabled=false -> baseline-v2.0.2.json
run B (V2.1)      query_rewrite_enabled=true  -> experiment-v2.1-query-rewrite.json

pass if:
  (i)   hard-subset chunk MRR@5 or NDCG@5 improves >= 0.03
  (ii)  easy-subset metric regression <= 0.01
  (iii) reg-001/reg-002 gate stays PASS
  (iv)  answer-010 improves from 0/0/0 to at least source_correctness=1,
        and the 12-case answer review is re-run
```

## Out of Scope

- Multi-query retrieval, result fusion/RRF, BM25/sparse retrieval, cross-encoder
  reranking (V2.2+).
- Chunking, embedding-model or index changes.
- Rewrite caching and history-aware rewriting (the Tool receives only the
  query; conversation history is intentionally not plumbed through).
- Any change to the evaluation dataset, query set or answer_cases.
- Any change to the Agent loop, Tools signature, API schemas or frontend.

## Further Notes

- ACTIVE comparison baseline: `reports/baseline-v2.0.2.json` (dataset
  `synthetic-personal-kb-v2`, revision `v2.0.2-instrumentation`);
  answer-level reference: `reviews/answer_review_v2.0.2.json` (11/9/11).
- Architecture decision: `docs/adr/0009-query-rewrite-inside-search-tool.md`.
- Tickets: 01 end-to-end rewrite in the Tool, 02 live A/B + answer re-run,
  03 ADR/README/glossary sync. `CONTEXT.md` is expected to stay unchanged
  (rewriting is an implementation concept, not a product-domain term); the
  ticket records that decision explicitly.
