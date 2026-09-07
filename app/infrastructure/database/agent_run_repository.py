"""SQLAlchemy implementation of the AgentRun repository."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.agent_run import AgentRunModel
from app.repositories.agent_run_repository import AgentRunRepository


class SQLAlchemyAgentRunRepository(AgentRunRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
        model = AgentRunModel(
            user_id=user_id,
            conversation_id=conversation_id,
            query=query,
            status=status,
            iterations=iterations,
            retrieval_count=retrieval_count,
            duration_ms=duration_ms,
            error_message=error_message,
            steps=steps,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return model.id
