"""Tool abstraction used by the registry."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.domain.models.llm import ToolSpec
from app.domain.models.search_result import SearchResult


@dataclass(frozen=True)
class ToolContext:
    user_id: str


@dataclass
class ToolResult:
    text: str
    results: list[SearchResult] = field(default_factory=list)


class Tool(ABC):
    @property
    @abstractmethod
    def spec(self) -> ToolSpec:
        raise NotImplementedError

    @abstractmethod
    async def run(
        self, arguments: dict, context: ToolContext
    ) -> ToolResult:
        raise NotImplementedError
