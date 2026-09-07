"""Conversation repository abstraction."""

from abc import ABC, abstractmethod

from app.domain.entities.conversation import Conversation
from app.domain.entities.message import Message


class ConversationRepository(ABC):
    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[Conversation]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id_and_user(
        self, conversation_id: str, user_id: str
    ) -> Conversation | None:
        raise NotImplementedError

    @abstractmethod
    async def list_messages(
        self, conversation_id: str
    ) -> list[Message]:
        raise NotImplementedError

    @abstractmethod
    async def create(
        self, user_id: str, title: str | None
    ) -> Conversation:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, conversation_id: str) -> None:
        raise NotImplementedError
