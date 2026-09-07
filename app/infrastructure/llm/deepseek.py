"""DeepSeek chat client over its OpenAI-compatible API."""

import json

import httpx

from app.core.config import get_settings
from app.domain.models.llm import (
    ChatMessage,
    LLMResponse,
    ToolCallRequest,
    ToolSpec,
)
from app.infrastructure.llm.base import LLMClient


class DeepSeekClient(LLMClient):
    def __init__(self) -> None:
        self._settings = get_settings()

    @staticmethod
    def _to_api_message(message: ChatMessage) -> dict:
        payload: dict = {"role": message.role}
        if message.content is not None:
            payload["content"] = message.content
        if message.tool_call_id:
            payload["tool_call_id"] = message.tool_call_id
        if message.tool_calls:
            payload["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.arguments),
                    },
                }
                for call in message.tool_calls
            ]
        return payload

    @staticmethod
    def _to_api_tool(tool: ToolSpec) -> dict:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }

    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list[ToolSpec] | None = None,
    ) -> LLMResponse:
        if not self._settings.deepseek_api_key or not self._settings.deepseek_model:
            raise RuntimeError("DEEPSEEK_API_KEY and DEEPSEEK_MODEL must be set")
        url = f"{self._settings.deepseek_base_url}/chat/completions"
        payload: dict = {
            "model": self._settings.deepseek_model,
            "messages": [self._to_api_message(m) for m in messages],
            "max_tokens": self._settings.llm_max_tokens,
        }
        if tools:
            payload["tools"] = [self._to_api_tool(t) for t in tools]
            payload["tool_choice"] = "auto"
        headers = {"Authorization": f"Bearer {self._settings.deepseek_api_key}"}
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
        message = response.json()["choices"][0]["message"]
        tool_calls = []
        for call in message.get("tool_calls") or []:
            try:
                arguments = json.loads(call["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                arguments = {}
            tool_calls.append(
                ToolCallRequest(
                    id=call["id"],
                    name=call["function"]["name"],
                    arguments=arguments,
                )
            )
        return LLMResponse(
            content=message.get("content"), tool_calls=tool_calls
        )
