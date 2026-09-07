"""Types shared between the Agent and LLM clients."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ToolCallRequest:
    id: str
    name: str
    arguments: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[ToolCallRequest] | None = None


@dataclass(frozen=True)
class LLMResponse:
    content: str | None = None
    tool_calls: list[ToolCallRequest] = field(default_factory=list)
