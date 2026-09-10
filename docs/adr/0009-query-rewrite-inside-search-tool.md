# Query rewrite lives inside `search_knowledge` as a single-query, fail-open step

Status: accepted

V2.1 improves retrieval by rewriting the query the Agent sends to the
knowledge base. The rewrite happens **inside the `search_knowledge` Tool**,
not in the AgentService or an HTTP middleware: the Tool is already the
retrieval boundary that owns `user_id` scoping, budgets and traces, so the
Agent loop, tool signature, API contract and `retrieval_count` semantics stay
unchanged.

The rewrite is deliberately scoped to **one query**: the rewritten query
replaces the original for that retrieval, and any failure (timeout, provider
error, empty/multi-line/over-length output) falls back to the original query
("fail-open"). Multi-query retrieval, fusion and reranking are separate,
later experiments (V2.2+); keeping them out of V2.1 preserves a single-variable
comparison against the frozen v2.0.2 baseline. Queries that contain unique
identifiers (order/policy/model numbers) skip rewriting so exact-term matching
is not damaged.

Consequences: every `search_knowledge` call may spend one LLM call and up to
`query_rewrite_timeout_seconds` of latency; `agent_runs.steps` carries the
original/rewritten query and fallback reason for replay; enabling or disabling
the feature is a configuration switch used by A/B experiments; introducing
multi-query later must revisit this decision and record a new ADR.
