# LifeAgent

LifeAgent is a personal information and decision assistant. Users upload their
personal documents (PDF / TXT / Markdown), the system builds a private
knowledge base (parse → chunk → embed → Chroma), and an agent answers
natural-language questions by searching that knowledge base, reading deeper
into documents when needed, and returning grounded answers with sources.

## Stack

- FastAPI + SQLAlchemy (async) + PostgreSQL + Alembic
- ARQ + Redis worker for async document ingestion
- Chroma (standalone service) as the vector store
- DashScope `text-embedding-v3` for embeddings (OpenAI-compatible API)
- DeepSeek chat API through an `LLMClient` abstraction (Agent loop is
  self-implemented, see `docs/adr/0006`)

## Quick start (Docker Compose)

Prerequisites: Docker with Compose v2.

1. Configure providers (optional for boot; required for chat):

   ```bash
   cp .env.example .env
   # fill in DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DASHSCOPE_API_KEY
   ```

2. Build and start the whole stack:

   ```bash
   docker compose up -d --build
   ```

   Compose starts postgres → runs `migrate` (Alembic) → starts `api` and
   `worker`, together with `redis` and `chroma`. Uploads live on a shared
   volume mounted into both `api` and `worker`.

3. Verify:

   ```bash
   curl http://localhost:8080/api/v1/health
   curl http://localhost:8080/api/v1/health/detailed
   ```

4. Run the end-to-end smoke script (chat step requires provider keys):

   ```bash
   python scripts/smoke_e2e.py
   ```

5. Stop: `docker compose down` (add `-v` only if you want to drop volumes).

## Local development (without Docker for the app)

Infrastructure containers: `docker compose up -d postgres redis chroma`
(postgres is published on host port **5433**, chroma on 8000, redis on 6379).

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
cp .env.example .env            # adjust values as needed
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python -m uvicorn app.main:app --reload
# in another terminal:
.venv/Scripts/python -m app.run_worker
```

Run the test suite (needs postgres/redis/chroma running):

```powershell
$env:DATABASE_URL='postgresql+asyncpg://lifeagent:lifeagent@localhost:5433/lifeagent_test'
.venv\Scripts\python -m pytest
```

## Environment variables

See `.env.example` for the full list. Key ones:

- `DATABASE_URL`, `REDIS_URL`, `CHROMA_URL` — infrastructure endpoints
- `JWT_SECRET` — token signing secret (change in any non-local environment)
- `LLM_PROVIDER` — `deepseek` (default) or `dashscope` (Qwen debug fallback)
- `DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL` — DeepSeek chat model
- `QWEN_MODEL` (default `qwen-max`) — used with `LLM_PROVIDER=dashscope`
- `DASHSCOPE_API_KEY` — embedding model key (also the Qwen chat key)
- `INGESTION_ENQUEUE_ENABLED`, `INGESTION_MAX_ATTEMPTS`,
  `INGESTION_RETRY_DELAY_SECONDS` — worker behavior
- `MAX_FILE_SIZE_MB`, `MAX_ITERATIONS`, `MAX_RETRIEVALS`, `TOP_K_DEFAULT`,
  `LLM_MAX_TOKENS` — upload and agent budgets

## API overview

All endpoints live under `/api/v1`:

- Auth: `POST /auth/register`, `POST /auth/login`, `GET /auth/me`
- Documents: `POST /documents` (multipart), `GET /documents`,
  `GET /documents/{id}`, `DELETE /documents/{id}`,
  `POST /documents/{id}/retry`
- Conversations: `POST /conversations`, `GET /conversations`,
  `GET /conversations/{id}`, `DELETE /conversations/{id}`
- Chat: `POST /chat`
- Health: `GET /health`, `GET /health/detailed`

Errors follow one shape: `{"error": {"code", "message", "request_id"}}`.
Cross-user resource access is indistinguishable from "not found" (404).

## Project conventions

- Vocabulary: `CONTEXT.md`; architecture decisions: `docs/adr/`
- Tickets & specs: `.scratch/lifeagent-mvp/` (spec + numbered issues)
- Design baseline: `docs/lifeagent-design-baseline-v1.1.md`
