"""LLM client abstraction."""

from abc import ABC, abstractmethod

from app.domain.models.llm import ChatMessage, LLMResponse, ToolSpec


class LLMClient(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        raise NotImplementedError
