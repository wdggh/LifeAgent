"""DashScope (Qwen) chat client over its OpenAI-compatible API."""

from app.core.config import get_settings
from app.infrastructure.llm.openai_compatible import OpenAICompatibleClient


class DashScopeLLMClient(OpenAICompatibleClient):
    """Qwen chat models served from the DashScope compatible-mode endpoint."""

    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(
            base_url=settings.llm_base_url,
            api_key=settings.dashscope_api_key,
            model=settings.qwen_model,
            max_tokens=settings.llm_max_tokens,
        )
