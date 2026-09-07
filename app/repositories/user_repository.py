"""User repository abstraction."""

from abc import ABC, abstractmethod

from app.domain.entities.user import User


class UserRepository(ABC):
    @abstractmethod
    async def get_by_username(self, username: str) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, user_id: str) -> User | None:
        raise NotImplementedError

    @abstractmethod
    async def create(self, username: str, password_hash: str) -> User:
        raise NotImplementedError
