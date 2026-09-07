"""Conversation workflows."""

from app.core.exceptions import AppError
from app.domain.entities.conversation import Conversation
from app.domain.entities.message import Message
from app.repositories.conversation_repository import ConversationRepository


class ConversationService:
    def __init__(self, repository: ConversationRepository) -> None:
        self._repository = repository

    async def create(
        self, user_id: str, title: str | None
    ) -> Conversation:
        cleaned = title.strip() if title else None
        return await self._repository.create(
            user_id, cleaned or None
        )

    async def list_conversations(self, user_id: str) -> list[Conversation]:
        return await self._repository.list_by_user(user_id)

    async def get_conversation_with_messages(
        self, conversation_id: str, user_id: str
    ) -> tuple[Conversation, list[Message]]:
        conversation = await self._repository.get_by_id_and_user(
            conversation_id, user_id
        )
        if conversation is None:
            raise AppError(
                404, "CONVERSATION_NOT_FOUND", "Conversation not found"
            )
        messages = await self._repository.list_messages(conversation_id)
        return conversation, messages

    async def delete_conversation(
        self, conversation_id: str, user_id: str
    ) -> None:
        conversation = await self._repository.get_by_id_and_user(
            conversation_id, user_id
        )
        if conversation is None:
            raise AppError(
                404, "CONVERSATION_NOT_FOUND", "Conversation not found"
            )
        await self._repository.delete(conversation_id)
