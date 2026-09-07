# Embedding via Alibaba DashScope text-embedding-v3

Status: accepted

DeepSeek (the chosen LLM provider) exposes no embedding endpoint, so embeddings come from Alibaba DashScope `text-embedding-v3` through its OpenAI-compatible API at dimension 1024. A local model was considered for offline/privacy use but is not part of the MVP.

Consequences: vectors are tied to this model and dimension. The embedding model version is recorded in three places so a future model change triggers re-embedding instead of silently mixing vectors: a nullable `embedding_model` column on `documents`, the Chroma collection name (e.g. `lifeagent_text-embedding-v3_1024`), and each chunk's metadata.
