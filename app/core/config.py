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

    # Document processing
    stale_processing_minutes: int = 15


@lru_cache
def get_settings() -> Settings:
    return Settings()
