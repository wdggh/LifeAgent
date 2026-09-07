"""AgentRun repository abstraction."""

from abc import ABC, abstractmethod


class AgentRunRepository(ABC):
    @abstractmethod
    async def create(
        self,
        *,
        user_id: str,
        conversation_id: str,
        query: str,
        status: str,
        iterations: int,
        retrieval_count: int,
        duration_ms: int | None,
        error_message: str | None,
        steps: list[dict] | None,
    ) -> str:
        raise NotImplementedError
