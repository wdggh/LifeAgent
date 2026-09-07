# Agent loop is self-implemented in the MVP; LangGraph is a later swap behind existing seams

Status: accepted

The MVP runs a hand-written Agent loop (planning → Tool call → observation → evaluation → stop) with `AgentState`, budgets, and grounding rules, so the project's core learning and interview narrative stay in our own code rather than inside a framework. LangGraph is deliberately deferred, not rejected: the `AgentService`, `ToolRegistry`, `LLMClient`, and Retriever boundaries keep it possible to swap the orchestration layer for a LangGraph StateGraph later without touching the API, data, tools, or RAG.

Trigger conditions for revisiting this decision: multi-agent topologies (planner/executor, supervisor), parallel retrieval branches, human-in-the-loop checkpoints, or checkpointed state replay. Until one of those is actually needed, the hand-written loop stays.
