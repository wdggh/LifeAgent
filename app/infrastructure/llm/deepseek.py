"""DeepSeek chat client over its OpenAI-compatible API."""

from app.core.config import get_settings
from app.infrastructure.llm.openai_compatible import OpenAICompatibleClient


class DeepSeekClient(OpenAICompatibleClient):
    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(
            base_url=settings.deepseek_base_url,
            api_key=settings.deepseek_api_key,
            model=settings.deepseek_model,
            max_tokens=settings.llm_max_tokens,
        )
