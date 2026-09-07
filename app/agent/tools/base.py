"""Tool abstraction used by the registry."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.domain.models.llm import ToolSpec
from app.domain.models.search_result import SearchResult
from app.domain.constants import CHUNKS_PER_ROUND


@dataclass
class ToolContext:
    user_id: str
    remaining_chunk_budget: int = CHUNKS_PER_ROUND


@dataclass
class ToolResult:
    text: str
    results: list[SearchResult] = field(default_factory=list)
    error: str | None = None


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
