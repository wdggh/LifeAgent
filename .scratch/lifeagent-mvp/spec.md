# LifeAgent MVP Spec

Status: ready-for-agent

## Problem Statement

An individual's important life information (contracts, purchase records, warranties, manuals, notes) is scattered across documents, and ordinary keyword search or single-shot RAG cannot answer questions that require locating the right documents, digging into their contents, and combining evidence from several places. The user wants to ask questions in natural language ("Is my gym membership still worth renewing?") and get answers that are grounded in their own documents, with the sources shown.

## Solution

LifeAgent gives a registered User a private Personal knowledge base. The user uploads PDF/TXT/Markdown Documents and assigns each a Document type. A background pipeline parses the file page by page, splits it into Chunks, embeds them, and indexes them into a vector store. The user then chats with an Agent in Conversations: the Agent decides whether and how to search the user's knowledge base, may search repeatedly or read more content from a specific Document, and finally produces an Answer with Sources. All retrieval and reads are strictly scoped to the current User, and every failure is surfaced as a clear error rather than a crash or a fabricated answer.

## User Stories

1. As a new user, I want to register with a username and password, so that I get an account and can start building my personal knowledge base.
2. As a registered user, I want to log in and receive an access token, so that subsequent requests identify me without my client sending a user id.
3. As a logged-in user, I want to fetch my own profile, so that my client can restore my session after a page refresh.
4. As a logged-in user, I want to upload a PDF, TXT, or Markdown file and assign it a Document type, so that it can become part of my knowledge base.
5. As a user, I want to be told immediately that my upload was accepted, so that I do not wait on file processing inside the upload request.
6. As a user, I want to see my Documents with their processing status, so that I know whether each file is usable yet.
7. As a user, I want to see the internal processing stage and error message of a failed Document, so that I understand what went wrong.
8. As a user, I want to retry a failed Document, so that transient failures do not force me to re-upload the file.
9. As a user, I want to delete a Document, so that I can remove content that I no longer want in my knowledge base.
10. As a user, I want to be sure that deleting a Document removes its searchable content everywhere, so that deleted material never resurfaces in answers.
11. As a user, I want to create and delete Conversations, so that I can keep related questions together.
12. As a user, I want my questions and the Agent's answers to be stored in the Conversation, so that I can come back later and continue where I left off.
13. As a user, I want to ask follow-up questions in the same Conversation, so that the Agent understands references to earlier turns ("and when does that warranty expire?").
14. As a user, I want the Agent to search my knowledge base only when my question needs it, so that irrelevant questions are answered without unnecessary retrieval.
15. As a user, I want the Agent to search more than once when the first results are not enough, so that multi-source questions like "what are my monthly phone costs?" can actually be answered.
16. As a user, I want to restrict a search to a specific Document type, so that questions like "look at my gym contract" target the right Documents instead of guessing.
17. As a user, I want to restrict a search to a specific Document, so that questions like "what is the refund clause in this contract?" stay inside that Document.
18. As a user, I want the Agent to be able to read a limited amount of content from a specific Document found by search, so that it can go deeper than a short retrieval snippet.
19. As a user, I want the final Answer to list the Documents it used, so that I can judge whether the answer is trustworthy.
20. As a user, I want the system to tell me honestly when my knowledge base does not contain the information, so that I am not misled by a confident guess.
21. As a user, I want the Agent to stop after a bounded number of searches, so that a difficult question does not loop forever or burn excessive cost.
22. As a user, I want answers about expiry/dues ("is it still under warranty?") to use the actual current date, so that the reasoning is correct.
23. As a user, I want numeric answers ("how much do I pay per month?") to show the numbers and assumptions behind them, so that I can verify the arithmetic.
24. As a user, I want instructions inside my own documents never to override the Agent's rules, so that an uploaded file cannot hijack the conversation.
25. As a user, I want my Documents and Conversations to be invisible to other users, so that my personal information stays private even when someone else guesses a resource id.
26. As a user, I want malformed, oversized, or wrongly typed uploads rejected with a clear message, so that I can fix the file without digging through logs.
27. As a user, I want failures in parsing, embedding, indexing, LLM calls, and tool calls to produce a readable error instead of a crash, so that the system stays usable.
28. As a user, I want the system to recover from a worker crash, so that a Document is not stuck in "processing" forever.
29. As a maintainer, I want every answer attempt recorded with its retrieval count, iterations, and steps, so that I can replay why an answer was wrong.
30. As a maintainer, I want to run the whole stack locally with one command, so that I can develop and demo the MVP end to end.

## Implementation Decisions

### Architecture

- Five layers with strict dependency direction: API → Service → Domain / Repository → Infrastructure. Domain contains no framework dependencies. Agent never touches the database or vector store directly; it calls Tools through a ToolRegistry.
- DocumentService manages Document records and files only. KnowledgeService owns the ingestion pipeline and is the single entry point invoked by the worker.
- Agent code depends on an LLMClient interface, implemented for DeepSeek over its OpenAI-compatible chat API with tool calling. Embedding access is a Provider abstraction, implemented for Alibaba DashScope `text-embedding-v3` (OpenAI-compatible mode, dimension 1024). No agent-loop framework; no vendor lock-in in the Agent.

### API contract (base path /api/v1)

- Auth: POST /auth/register, POST /auth/login, GET /auth/me. JWT access token; user identity always derived server-side from the token.
- Documents: POST /documents (multipart file + document_type), GET /documents (paged list), GET /documents/{id}, DELETE /documents/{id}, POST /documents/{id}/retry. Upload returns immediately with a processing Document.
- Conversations: POST /conversations, GET /conversations, GET /conversations/{id}, DELETE /conversations/{id}.
- Chat: POST /chat with {conversation_id, query}, executed synchronously, returning {answer, sources, metadata}.
- Health: GET /health.
- Unified error body {code, message, request_id}. Status codes: 400/401/404/413/415/422/503. Resource lookups always filter by the current user; another user's resource behaves as 404.

### Data model

- users: id, username, password_hash, timestamps.
- documents: id, user_id, filename, file_type, file_path, file_size, document_type, status, processing_stage, error_message, embedding_model (nullable), timestamps.
- conversations: id, user_id, title, timestamps.
- messages: id, conversation_id, role (user|assistant only), content, agent_run_id (nullable), created_at. System prompts are configuration and are never stored.
- agent_runs: id, user_id, conversation_id, query, status, iterations, retrieval_count, duration_ms, error_message, steps (JSONB), created_at. `steps` holds one entry per Tool call: iteration, tool, summarized arguments, result count, duration, error.
- Chroma stores one record per Chunk: id, embedding, content, metadata {user_id, document_id, document_name, document_type, start_page, end_page, chunk_index, embedding_model}. No Chunk table in PostgreSQL.

### Document lifecycle

- User-facing Document status: uploaded, processing, completed, failed. Internal Processing stage: parsing, chunking, embedding, indexing.
- Ingestion runs on a dedicated ARQ + Redis worker: max_retries 2 with backoff; on exhaustion the Document becomes failed with error_message. Before re-running a failed/retried Document, any partial vectors from earlier attempts are cleared.
- A Document in processing whose updated_at is older than 15 minutes is stale and treated as retryable; the worker can sweep stale Documents on startup.
- Deletion order: remove Chroma vectors by document_id, then the stored file, then the PostgreSQL row. Any failure keeps the row and returns an error so the delete can be retried; all steps are idempotent.

### Agent behavior

- Tools: search_knowledge(query, top_k default 5, optional document_type, optional document_id) and get_document(document_id, optional page, optional max_chars). user_id is never a Tool parameter; the backend injects it as a mandatory vector-store filter. Both Tools return structured results (document identity, page range, content excerpt, score).
- get_document returns a limited context window of a specific Document, never the whole file.
- Budgets: max 5 iterations, max 3 retrievals, per-chunk context cap ~1000 tokens, per-round cap 4 chunks, LLM max_tokens 1500. Stop when: no hits, no new material across repeated searches, budget exhausted (answer only what is confirmed or say the knowledge base cannot answer), or the question is fully answered.
- Every chat turn stores the user Message, the assistant Message, and one AgentRun. Context injection includes the most recent 10 Messages of the Conversation, truncated by token budget.
- Guardrails: current date and timezone injected by the backend; numeric answers show their numbers, sources, and assumptions; retrieved content is marked as data and document instructions are never treated as system instructions.
- Sources are surfaced at Document level in the API response; chunk/page-level references are retained in the AgentRun steps.

### Deployment

- Docker Compose services: postgres, redis, chroma (standalone), api, worker, and a one-shot migrate service. The migrate service runs after postgres is healthy; api and worker start after migrate completes. An uploads volume is shared by api and worker. All configuration comes from environment variables (see .env.example); Chroma collection name embeds the embedding model and dimension.

## Testing Decisions

- The primary test seam is the public HTTP API: tests drive real vertical flows (register → upload → document completes → chat with sources) through FastAPI's test client. What makes a good test is external behavior: a documented user-visible outcome, not implementation details.
- Infrastructure inside tests: PostgreSQL test database isolated per test, ephemeral Chroma, and Fake LLM / Fake Embedding clients injected through configuration. Real external APIs are never called by the test suite. The Fake LLM can script multi-iteration tool-call scenarios so Agent loop behavior is verified through the HTTP seam.
- A narrow second seam covers worker crash/recovery corner cases (retry exhaustion, stale processing recovery) by invoking the worker handler directly with fakes, since those states cannot be produced naturally through HTTP.
- Modules under test: auth, document upload and validation, ingestion state machine, retry and stale recovery, deletion cascade and cross-user isolation (404 matrix), conversation persistence, Agent loop budgets and stop rules, multi-iteration retrieval, document-scoped search, and the chat end-to-end response.
- Prior art: none; this is a greenfield repository. The first ticket establishes the test harness and seam conventions that later tickets follow.

## Out of Scope

- Frontend (Vue 3): the backend MVP is verified through the API seam; UI becomes a separate ticket stream after the backend MVP is stable.
- MCP, multi-Agent, calendars, reminders, automated execution (cancel/pay/buy), email/WeChat/voice integrations.
- OCR/scan support, Word/Excel, images, video.
- Hybrid search, BM25, reranking, query rewriting, knowledge graphs, retrieval evaluation framework.
- Refresh tokens, logout, password change, email verification.
- Message pagination and auto-generated Conversation titles; Document download/preview endpoints.
- Token usage accounting; per-run streaming (SSE).
- Multi-context domain layout; per-user Chroma collections (single shared collection with enforced user_id filter).

## Further Notes

- Vocabulary is defined in CONTEXT.md; architecture decisions that need recorded rationale live in docs/adr/ (0001–0005). Both must be respected while implementing.
- Development order follows the baseline: skeleton/health → auth → documents → ingestion → retrieval isolation → chat/Agent → hardening → full-stack local boot.
- DEEPSEEK_MODEL is a placeholder until the developer confirms the model id available on their account; tests never depend on a real key.
