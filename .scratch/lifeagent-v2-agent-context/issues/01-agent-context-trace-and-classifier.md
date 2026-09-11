# 01: Agent-context trace, budget-faithful runner mode, funnel classifier

**What to build:** the instrumentation that makes "检索到了 → Agent 看到了 →
Agent 用到了" measurable, without touching retrieval quality.

1. Record the returned chunk ids (rank order, ids only, no content) in every
   `agent_runs.steps` entry written by `Agent.run`, so a stored run says what
   the Agent actually received. Additive; JSONB, no migration.
2. Add a budget-faithful mode to `retrieval_eval live` that calls the Tool the
   way the Agent does (`ToolContext(user_id=...)` with the production
   `CHUNKS_PER_ROUND` budget and the same `top_k`), so the measured set equals
   the consumed set. The existing `top_k=10, budget=10` capability mode stays
   the default for historical comparability.
3. Add `tests/evaluation/metrics/agent_context.py`: the pure
   `agent_context_recall` metric (`per_call_context_recall@K`,
   `first_call_context_recall@K`, union over calls) and the four-label funnel
   classifier (`not_retrieved` / `retrieved_not_returned` /
   `returned_not_used` / `used`, plus `not_applicable` for gold-less cases).
4. Report `agent_context_recall@4` overall / hard-10 / easy-40 in the live
   report and per case in the raw artifact.

**Blocked by:** None

**Status:** resolved

- [x] `agent_runs.steps` carries `chunk_ids` in rank order for a search step
- [x] budget-faithful mode clamps to `CHUNKS_PER_ROUND`; capability mode unchanged
- [x] pure metric + classifier with union / first-call / cap-boundary tests
- [x] report and raw artifact expose agent-context recall per query
- [x] no retrieval, prompt, budget or default-config change; disabled paths identical

## Comments

## Answer

Instrumentation is in; nothing about retrieval, prompts or budgets changed.

- **Trace.** `Agent.run` writes `chunk_ids` (rank order, ids only) into every
  `agent_runs.steps` entry next to `result_count`. JSONB, no migration; `steps`
  are not part of the API response, so no contract change.
- **Budget-faithful mode.** `retrieval_eval live --via-tool --agent-budget`
  calls the Tool exactly as the Agent does — `ToolContext(user_id=...)`
  (budget = `CHUNKS_PER_ROUND` = 4) with `top_k = CHUNKS_PER_ROUND` — so the
  measured set is the consumed set. Without the flag the historical
  `top_k=10, budget=10` capability path is byte-identical; the flag without
  `--via-tool` is rejected.
- **Metric + classifier.** `tests/evaluation/metrics/agent_context.py` holds
  `context_hit` (cap boundary), `agent_context_recall` (union over calls),
  `first_call_context_recall`, `classify_funnel` and `summarize_funnel`. Pure
  functions, no Retriever/Chroma/LLM.
- **Refinement disclosed:** the funnel grew one label while implementing. The
  spec said four labels; "the document was hit but not the gold chunk" and "the
  gold chunk came back but fell outside the consumed window" need different
  next steps, so they are now `document_only` and `found_beyond_budget`
  (plus `not_retrieved`, `returned_not_used`, `used`, `not_applicable`).
  The spec was updated to match.
- **Report.** `report["agent_context"]` = `{mode, k, queries, recall@4,
  by_difficulty}`; raw per-case artifacts carry `context_recall@4` and
  `context_chunk_ids`. Both are `None`/absent unless the budget-faithful mode
  ran, so old reports stay readable.
- **Tests.** New: `tests/evaluation/metrics/test_agent_context.py`,
  runner-mode tests in `tests/evaluation/runners/test_retrieval_eval.py`
  (gold at rank 5 = capability hit but not context), and a trace test in
  `tests/test_review_fixes.py`. Full `pytest` green (exit 0, three runs).
- **Known limitation handed to 02:** `get_document` delivers page text, not
  chunks, so it contributes no `chunk_ids`. A case whose trace contains a
  `get_document` read of the gold document must be read manually (document_id
  and page are already in `args_summary`) instead of being auto-labelled
  `not_retrieved`.
