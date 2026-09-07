"""User registration, authentication, and lookup."""

import asyncio

from app.core.exceptions import AppError
from app.core.security import hash_password, verify_password
from app.domain.entities.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    @staticmethod
    def _normalize_username(username: str) -> str:
        return username.strip().lower()

    async def register(self, username: str, password: str) -> User:
        normalized = self._normalize_username(username)
        existing = await self._repository.get_by_username(normalized)
        if existing is not None:
            raise AppError(409, "USERNAME_TAKEN", "Username already exists")
        password_hash = await asyncio.to_thread(hash_password, password)
        return await self._repository.create(normalized, password_hash)

    async def authenticate(self, username: str, password: str) -> User:
        normalized = self._normalize_username(username)
        user = await self._repository.get_by_username(normalized)
        if user is None:
            raise AppError(
                401, "INVALID_CREDENTIALS", "Invalid username or password"
            )
        valid = await asyncio.to_thread(
            verify_password, password, user.password_hash
        )
        if not valid:
            raise AppError(
                401, "INVALID_CREDENTIALS", "Invalid username or password"
            )
        return user

    async def get_user(self, user_id: str) -> User | None:
        return await self._repository.get_by_id(user_id)
