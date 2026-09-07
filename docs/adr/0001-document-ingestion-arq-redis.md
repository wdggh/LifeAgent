# Document ingestion runs on a dedicated ARQ + Redis worker

Status: accepted

We chose a dedicated asynchronous worker (ARQ on Redis) over in-process FastAPI BackgroundTasks for document ingestion, so parse → chunk → embed → index survives restarts, supports retries, and keeps the API process responsive from the first version. `DocumentService` only records state; `KnowledgeService` owns the ingestion pipeline and is invoked by the worker.

Consequences: the API and worker are separate processes, so Chroma access between them must be settled before deployment; docker-compose adds Redis and worker services; a `POST /documents/{id}/retry` endpoint re-enqueues failed Documents.
