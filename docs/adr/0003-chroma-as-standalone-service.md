# Chroma runs as a standalone service

Status: accepted

Because ingestion runs in a dedicated worker while retrieval runs in the API process, Chroma is deployed as a standalone service (its own container, accessed over HTTP) rather than a local persistent directory. Chroma's local client is not safe for concurrent multi-process access, and containerizing it keeps vector writes and reads behind one consistent interface.

Consequences: docker-compose includes a Chroma service; the API and worker both use the HTTP client; the collection is still shared across users with `user_id` enforced as a metadata filter on every query.
