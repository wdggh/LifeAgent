# LifeAgent Frontend V1 Spec

Status: ready-for-agent

## Problem Statement

The LifeAgent backend MVP is accepted and frozen, but users still have no usable web interface. Frontend V1 must connect the real API end to end: register/login, upload personal documents and watch their processing status, create or pick a Conversation, ask natural-language questions, and see grounded Answers with their Sources. The developer is also using this project to learn Vue 3 frontend engineering, so the code must stay layered and teachable, and the frontend must never drive changes to the accepted backend.

## Solution

A Vue 3 + TypeScript + Vite web application that only consumes the frozen backend contract (base path `/api/v1`): auth register/login/me, document upload/list/delete/retry, conversation list/create/detail/delete, and synchronous chat. The user registers (and is logged in automatically), uploads PDF/TXT/Markdown Documents with a Document type, watches each Document reach `completed` or `failed`, then asks questions in a Conversation and reads the Answer with its Document-level Sources. Message history is stored by the backend and restored after refresh. The UI is Chinese, uses the project glossary vocabulary, supports a single in-flight chat at a time, switches Conversations without message cross-talk, and reports failures honestly without pretending a Message was or was not stored.

## User Stories

1. As a new user, I want to register with a username and password, so that I get an account and can build my personal knowledge base.
2. As a registering user, I want duplicate or invalid usernames and weak passwords to be rejected with a clear message, so that I can fix my input.
3. As a registering user, I want to be logged in automatically after registration, so that I do not have to log in twice.
4. As a registered user, I want to log in and have my access token saved, so that I stay signed in across requests.
5. As a logged-in user, I want to be taken back to the page I tried to open after logging in, so that I do not lose my place.
6. As a logged-in user, I want my session to survive a page refresh, so that I can come back to the app without logging in again.
7. As a user with an expired or invalid token, I want to be sent to the login page automatically, so that I never stare at a broken page.
8. As a user, I want to log out from the app, so that the token is cleared and another person on the same device is not signed in.
9. As a logged-in user, I want a sidebar listing my Conversations newest first, so that I can resume the conversation I want.
10. As a user, I want to click 新对话 to start fresh without creating anything yet, so that an abandoned attempt does not litter my Conversation list.
11. As a user, I want my first message in a new chat to create the Conversation automatically, so that I never have to name a conversation before thinking.
12. As a user, I want to open a Conversation and see its full history, so that I can continue where I left off.
13. As a user, I want to delete a Conversation after confirmation, so that I can tidy up topics I no longer need.
14. As a logged-in user, I want to upload multiple files at once while choosing one Document type, so that a batch of similar records uploads quickly.
15. As an uploading user, I want client-side checks for supported file type and size before upload, so that obvious mistakes are caught immediately.
16. As a user, I want each uploaded file to show its own state line (uploading → processing → completed/failed), so that I know what is happening without guessing.
17. As a user, I want to see Document status (`uploaded`/`processing`/`completed`/`failed`) and refresh processing state automatically while it changes, so that I know when a file becomes usable.
18. As a user, I want to expand a Document row to see its internal processing stage, file type, size, Document type, and timestamps, so that I can understand its state.
19. As a user with a failed Document, I want to see the error and retry it, so that a transient failure does not force a re-upload.
20. As a user, I want to delete a Document after confirmation and see it disappear, so that content I no longer want is removed from my knowledge base.
21. As a user, I want to ask a question in a Conversation and have the input disabled with a visible processing state while the Agent answers, so that I do not fire duplicate questions.
22. As a user, I want my question and the Agent's Answer shown as distinct user/assistant bubbles, so that I can follow the exchange.
23. As a user, I want the Answer to list the Documents it used, with relevance, so that I can judge how trustworthy it is.
24. As a user of a question the Agent answered without documents, I want a clear "本次未引用文档" note, so that I am not confused by a missing Source section.
25. As a user, I want subtle retrieval metadata (search count and duration), so that I can see the effort behind an Answer.
26. As a user, I want to switch Conversations while an Answer is still loading, and not have that Answer appear in the wrong Conversation, so that I can browse without breaking the chat.
27. As a user, I want a failed chat attempt to show an honest error and refresh the history, so that I can decide myself whether to ask again.
28. As a user, I want every empty, loading, and error state to be clear, so that the app never looks broken or silently stuck.
29. As a user, I want to reload or deep-link to a specific Conversation and still land on it, so that my place survives navigation.

## Implementation Decisions

### Boundary: consume, do not redesign

- **Backend API contract is the source of truth.** This spec records how the frontend consumes the frozen backend; it never re-defines the API. Chat is `POST /api/v1/chat` with `{conversation_id, query}`; there is no `POST /conversations/{id}/messages`, and such a discussion is out of scope.
- V1 does not modify the backend and does not add CORS for development. Browser traffic goes Vite dev server → proxy → FastAPI on host port 8080; `VITE_API_BASE_URL` is the relative `/api/v1`. Recorded as ADR-0007. Deployment topology (Nginx same-origin or direct API origin + CORS) is deferred.

### Engineering stack and layering

- Vue 3 + TypeScript + Vite + Vue Router + Pinia + Axios + Element Plus.
- Strict layering for requests: views/components → Pinia stores → api modules → one shared Axios client. Components never call Axios directly.
- The shared client holds defaults (base URL, JSON content type, 30s timeout) and is the future home of JWT header injection, `request_id` propagation, unified errors, and 401 handling. The chat request overrides timeout to 120s per request because an Agent run can take tens of seconds.
- API modules mirror backend resource families: auth, documents, conversations, chat. Types in the frontend align with the backend schemas; nothing is invented.

### Authentication and session

- JWT stored in localStorage; on app start with a token, show the shell first and validate with `GET /auth/me`.
- `POST /auth/register` returns no token, so the register flow calls login afterwards and proceeds straight to the chat area.
- Any 401 clears the local session and routes to login with the original destination preserved as a redirect target.
- Logout is client-side only (clearing the token), because the backend exposes no logout endpoint.
- The frontend never sends a user id; identity always comes from the backend token.

### Information architecture and routing

- Public routes: login, register.
- Authenticated App Shell: sidebar (新对话, Conversation list, 我的文档, user area with username and logout) + main area.
- Main routes: `/chat` for the empty/draft state; `/chat/:conversationId` for an existing Conversation (refresh- and deep-link-safe); `/documents` for the Documents view.
- No separate Document detail route: the detail endpoint returns the same fields as the list, so row expansion inside the list suffices.

### Conversation lifecycle (ADR-0008)

- 新对话 is a New Conversation Draft, not a Conversation: it has no `conversation_id` and must not call `/chat`.
- The first user message triggers `POST /conversations` (title = truncated first query, about 30 characters), then `POST /chat`; afterwards the sidebar list refreshes.
- The draft state lives in the conversation store so the distinction between draft and active Conversation is explicit.
- State machine:

```text
点击「新对话」
      ↓
draft 状态（无 conversation_id）
      ↓
用户发送第一条消息
      ↓
POST /conversations（title = 首问截断）
      ↓
得到 conversation_id
      ↓
POST /chat
      ↓
回答返回 → 写入当前会话 → 刷新会话列表
```

### Chat interaction and rendering

- One global in-flight chat: while pending, sending is disabled with a visible processing state; the user may switch Conversations.
- If a response arrives after the user switched away, refresh the list and show a light notification; never insert content into the wrong Conversation.
- Answer text renders as plain text preserving line breaks. No Markdown rendering in V1.
- Sources render as a collapsible Document list showing name and relevance (percentage/progress). Metadata shows as a subtle line: 检索 N 次 · 用时 X.Xs. No Sources shows 本次未引用文档.
- Chat failure semantics: no automatic re-send. On failure, show an error and refresh the Conversation history, because the backend stores the user Message before the Agent run and a re-send could duplicate it.

### Documents interaction

- Upload dialog: choose one Document type first (six fixed values, Chinese labels, default other), then select multiple files; files upload one by one (one file per request), each with its own state line.
- Client pre-checks mirror the backend: supported file type set (pdf/txt/markdown) and size ≤ 50MB; server 413/415 results still map to messages.
- Documents list loads one page of up to 100; the API returns no total, so V1 does not implement load-more. Refresh only polls visible `processing` Documents every 3s until `completed`/`failed`, then stops.
- Failed rows show the error and a retry action; deletion requires confirmation; expanding a row reveals processing stage and metadata.

### Error mapping

Unified error body is `{"error": {"code", "message", "request_id"}}`; the frontend maps by code:

- 401 `UNAUTHENTICATED` / `INVALID_TOKEN`: clear session, go to login with redirect.
- 401 `INVALID_CREDENTIALS`: login form error (用户名或密码错误).
- 409 `USERNAME_TAKEN`: register form error (用户名已被使用).
- 409 `DOCUMENT_NOT_RETRYABLE`: current state cannot be retried; refresh.
- 413 `FILE_TOO_LARGE`: file exceeds 50MB.
- 415 `UNSUPPORTED_FILE_TYPE` / `INVALID_FILE_CONTENT`: type unsupported or content/type mismatch.
- 404 `DOCUMENT_NOT_FOUND` / `CONVERSATION_NOT_FOUND`: content missing or deleted; refresh list / return to empty state.
- 500 `DOCUMENT_DELETE_FAILED`: deletion failed, retry.
- 503 `LLM_UNAVAILABLE` / `SERVICE_UNAVAILABLE`: service temporarily unavailable; chat uses the failure semantics above.
- Unknown codes fall back to the backend-provided message.

### State and component shape

- Stores: auth (token/user/login/register/logout/session restore), conversation (list, active id, draft, messages, in-flight, send flow, delete), document (list, upload queue, processing polling, delete/retry, expanded row).
- Views: login, register, chat workspace, documents.
- Reusable components keep to a small set (sidebar, message bubble, source list, upload dialog, document list) so the layer boundary stays visible.

### UI copy and glossary

- Chinese UI labels follow the project glossary: Conversation=对话, Document=文档, Message=消息, Source=来源, sidebar entry 我的文档.
- Document type labels: contract=合同, purchase_record=购买记录, warranty=保修凭证, manual=说明书, note=笔记, other=其他.
- Status labels: uploaded=已上传, processing=处理中, completed=已完成, failed=处理失败; internal stages parsing/chunking/embedding/indexing = 解析中/切分中/向量化中/索引中.

## Testing Decisions

- What makes a good test here is a user-visible outcome, not implementation detail. The user confirmed the seam: V1 uses a human browser walkthrough against the real backend through the Vite proxy as the single acceptance seam, with `npm run build` (type check + build) as the gate.
- Coverage is expressed as per-ticket acceptance checklists that follow this spec: auth/shell flow; documents upload/status/retry/delete flow; conversation + chat flow including the draft state machine; and a final full-chain walkthrough plus error-path pass.
- Prior art: the backend MVP verifies through its public HTTP API seam with automated tests. The frontend has no prior automated test seam, so V1 deliberately adds none; Vitest/Playwright are follow-up candidates rather than V1 scope.

## Out of Scope

- Any backend change, including CORS, new/changed endpoints, idempotency keys, or message deletion.
- Markdown rendering of Answers; document download/preview; conversation rename; >100-document pagination; message pagination; chat streaming/SSE; refresh tokens or a server-side logout endpoint.
- Automated frontend tests (Vitest/Playwright), multi-user concerns, settings pages, and non-Chinese UI.
- Follow-up candidates are recorded in ticket 04 rather than implemented here.

## Further Notes

- Backend facts that shape the frontend are verified against the running contract: register returns no token; Conversation title is nullable and unrenameable; `/chat` is synchronous; a failed Agent run leaves the user Message stored; document/conversation lists return arrays with no totals.
- Vocabulary lives in the repo glossary (Chinese labels included); ADR-0007 and ADR-0008 record the proxy/no-CORS decision and the create-on-first-message decision.
- Tickets: 01 auth + App Shell, 02 documents, 03 conversations + chat, 04 polish and final acceptance; they are published in the tracker under this feature with blocking edges.
- Implementation order inside each ticket is api layer → store → view so the layering lesson stays intact; the backend stays untouched.
