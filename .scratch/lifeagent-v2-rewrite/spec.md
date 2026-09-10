# LifeAgent V2.1 Spec — Single-Query Rewrite

Status: ready-for-agent

## Problem

On the hardened benchmark (baseline v2.0.2), 11 hard cases and the
end-to-end sample `answer-010` (wrong document → wrong answer → hallucinated
generic return policy) show that the agent's raw query wording is a retrieval
limiter. V2.1 must improve retrieval by **rewriting the retrieval query**, as a
single-variable experiment on a stable baseline.

## Boundary

- Scope: **single-query rewrite only**. The rewrite replaces the original query
  for retrieval; on failure the original query is used (fail-open).
- No multi-query, no result fusion, no BM25/sparse, no reranker
  (V2.2/V2.3/V2.4).
- Rewrite happens **inside `search_knowledge`**; Agent loop, tool signature,
  API, frontend, `retrieval_count` semantics and budgets are unchanged.
- `agent_runs.steps` gains rewrite trace fields (JSONB, no migration).
- Baseline for comparison: `baseline-v2.0.2.json` on the same dataset/retriever
  config; query/answer_cases sets stay frozen.

## Locked decisions (Q36–Q48)

```text
scope            single rewritten query replaces the original
fallback         timeout/error/empty/multiline/over-length -> original query,
                 reason recorded (fail-open)
exact-term       skip rewrite when the query contains a unique id
                 (regex: [A-Z]{2,}-\\d{4}-\\d{4} style codes)
rewrite content  colloquial->formal, synonym/business-term expansion,
                 relative date resolution using backend-injected now,
                 keep proper nouns/ids verbatim, merge multi-intent into ONE
                 query, single line, <= 120 chars, no explanations
model            existing LLMClient; query_rewrite_timeout_seconds=8;
                 max_tokens=200; no cache in V2.1
config           query_rewrite_enabled (default true; experiments set false)
observability    steps: query_original, query_rewritten, rewrite_model,
                 rewrite_fallback, rewrite_fallback_reason, rewrite_duration_ms
tests            ScriptedFakeLLM only; no real LLM in unit tests
```

## Experiment protocol (success criteria fixed in advance)

```text
run A (baseline)  QUERY_REWRITE_ENABLED=false  -> baseline-v2.0.2.json
run B (V2.1)      QUERY_REWRITE_ENABLED=true   -> experiment-v2.1-query-rewrite.json

pass if:
  (i)   hard subset chunk MRR@5 or NDCG@5 improves >= 0.03
  (ii)  easy subset metric regression <= 0.01
  (iii) reg-001/reg-002 gate PASS unchanged
  (iv)  answer-010 improves from 0/0/0 to at least source_correctness=1,
        and the 12-case answer review is re-run
```

## ADR

`docs/adr/0009-query-rewrite-inside-search-tool.md` records the placement,
single-query scope and fail-open semantics.

## Tickets

```text
V2.1-01 QueryRewriter module + prompt + guards + fake-LLM tests
V2.1-02 Wire into search_knowledge + config + steps trace + integration tests
V2.1-03 Experiment runs, comparison report, answer-level re-run
V2.1-04 ADR/README/glossary sync and resolution
```

01 -> 02 -> 03 -> 04. All blocked on V2.0.2 completion.
