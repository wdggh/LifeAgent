"""SQLAlchemy implementation of the conversation repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.conversation import Conversation
from app.domain.entities.message import Message
from app.infrastructure.database.models.conversation import (
    ConversationModel,
    MessageModel,
)
from app.repositories.conversation_repository import ConversationRepository


def _to_conversation(model: ConversationModel) -> Conversation:
    return Conversation(
        id=model.id,
        user_id=model.user_id,
        title=model.title,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_message(model: MessageModel) -> Message:
    return Message(
        id=model.id,
        conversation_id=model.conversation_id,
        role=model.role,  # type: ignore[arg-type]
        content=model.content,
        agent_run_id=model.agent_run_id,
        created_at=model.created_at,
    )


class SQLAlchemyConversationRepository(ConversationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_user(self, user_id: str) -> list[Conversation]:
        result = await self._session.execute(
            select(ConversationModel)
            .where(ConversationModel.user_id == user_id)
            .order_by(ConversationModel.created_at.desc())
        )
        return [_to_conversation(row) for row in result.scalars().all()]

    async def get_by_id_and_user(
        self, conversation_id: str, user_id: str
    ) -> Conversation | None:
        result = await self._session.execute(
            select(ConversationModel).where(
                ConversationModel.id == conversation_id,
                ConversationModel.user_id == user_id,
            )
        )
        model = result.scalar_one_or_none()
        return _to_conversation(model) if model else None

    async def list_messages(
        self, conversation_id: str
    ) -> list[Message]:
        result = await self._session.execute(
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            .order_by(
                MessageModel.created_at.asc(), MessageModel.id.asc()
            )
        )
        return [_to_message(row) for row in result.scalars().all()]

    async def create(
        self, user_id: str, title: str | None
    ) -> Conversation:
        model = ConversationModel(user_id=user_id, title=title)
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_conversation(model)

    async def delete(self, conversation_id: str) -> None:
        model = await self._session.get(ConversationModel, conversation_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.commit()
