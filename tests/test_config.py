"""Configuration behavior: defaults and environment overrides."""

from app.core.config import Settings, get_settings


def test_settings_defaults_match_environment_example(settings) -> None:
    assert settings.app_env == "test"
    assert settings.chroma_collection == "lifeagent_text-embedding-v3_1024"
    assert settings.embedding_provider == "dashscope"
    assert settings.embedding_model == "text-embedding-v3"
    assert settings.embedding_dimensions == 1024
    assert settings.max_file_size_mb == 50
    assert settings.max_iterations == 5
    assert settings.max_retrievals == 3
    assert settings.top_k_default == 5
    assert settings.llm_max_tokens == 1500
    assert settings.stale_processing_minutes == 15
    assert not settings.deepseek_api_key
    assert not settings.dashscope_api_key


def test_settings_environment_override(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("MAX_ITERATIONS", "7")
    get_settings.cache_clear()
    try:
        overridden = get_settings()
        assert overridden.app_env == "staging"
        assert overridden.max_iterations == 7
    finally:
        get_settings.cache_clear()


def test_settings_accept_uppercase_env_names(monkeypatch) -> None:
    monkeypatch.setenv("CHROMA_COLLECTION", "custom_collection")
    get_settings.cache_clear()
    try:
        assert get_settings().chroma_collection == "custom_collection"
    finally:
        get_settings.cache_clear()
