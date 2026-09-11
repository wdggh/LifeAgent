"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime settings. Values come from environment variables or `.env`;
    names are case-insensitive and match `.env.example`.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Application
    app_env: str = "dev"
    log_level: str = "INFO"

    # Auth (used from ticket 02 onward; placeholder default for local dev)
    jwt_secret: str = "dev-only-secret-change-me-0123456789abcdef"
    access_token_expire_minutes: int = 1440

    # PostgreSQL
    database_url: str = (
        "postgresql+asyncpg://lifeagent:lifeagent@localhost:5433/lifeagent"
    )

    # Redis / ARQ worker
    redis_url: str = "redis://localhost:6379/0"
    ingestion_enqueue_enabled: bool = True
    ingestion_max_attempts: int = 3
    ingestion_retry_delay_seconds: int = 2

    # Chroma (standalone service)
    chroma_url: str = "http://localhost:8000"
    chroma_collection: str = "lifeagent_text-embedding-v3_1024"

    # LLM provider (DeepSeek via OpenAI-compatible API)
    llm_provider: str = "deepseek"
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_api_key: str = ""
    deepseek_model: str = ""
    qwen_model: str = "qwen-max"
    app_timezone: str = "Asia/Shanghai"

    # Embedding provider (Alibaba DashScope via OpenAI-compatible API)
    embedding_provider: str = "dashscope"
    embedding_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    embedding_model: str = "text-embedding-v3"
    embedding_dimensions: int = 1024
    dashscope_api_key: str = ""

    # Uploads
    upload_dir: str = "data/uploads"
    max_file_size_mb: int = 50

    # Agent budget
    max_iterations: int = 5
    max_retrievals: int = 3
    top_k_default: int = 5
    llm_max_tokens: int = 1500

    # Query rewrite (V2.1, ADR-0009)
    # V2.1 single-query rewrite FAILED its pre-registered criteria
    # (hard-10 MRR/NDCG regressed), so it ships disabled; V2.2 replaces it
    # with query expansion + weighted RRF.
    query_rewrite_enabled: bool = False
    query_rewrite_timeout_seconds: float = 8.0
    query_rewrite_max_tokens: int = 200

    # Query expansion / multi-query retrieval (V2.2, ADR-0010)
    query_expansion_enabled: bool = False
    query_expansion_variants: int = 1
    query_expansion_candidate_k: int = 8
    query_expansion_rrf_k: int = 60
    # Kept for the later multi-variant/multi-channel stage; V2.2 always
    # uses 1.0 with an original-priority tie-break.
    query_expansion_original_weight: float = 1.0
    query_expansion_timeout_seconds: float = 8.0
    query_expansion_max_tokens: int = 200

    # Sparse / hybrid retrieval (V2.3, ADR-0011)
    query_sparse_enabled: bool = False
    query_sparse_candidate_k: int = 8
    query_sparse_bm25_k1: float = 1.5
    query_sparse_bm25_b: float = 0.75
    query_sparse_rrf_k: int = 60
    query_sparse_version_ttl_seconds: int = 60
    query_sparse_fusion_mode: str = "equal_rrf"
    query_sparse_rrf_weight_dense: float = 2.0
    query_sparse_reserved_slots: int = 1

    # Document processing
    stale_processing_minutes: int = 15


@lru_cache
def get_settings() -> Settings:
    return Settings()
