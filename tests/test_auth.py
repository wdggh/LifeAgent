"""Authentication: register, login, current user, and token handling."""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_session_maker


async def _register(client, username: str = "alice", password: str = "passw0rd123"):
    return await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": password},
    )


async def test_register_creates_user_and_hashes_password(client) -> None:
    response = await _register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "alice"
    assert body["user_id"]
    assert body["created_at"]

    async with get_session_maker()() as session:
        result = await session.execute(
            select(UserModel).where(UserModel.username == "alice")
        )
    model = result.scalar_one()
    assert model.password_hash != "passw0rd123"
    assert verify_password("passw0rd123", model.password_hash)


async def test_register_normalizes_username_case(client) -> None:
    response = await _register(client, username="  Alice  ")
    assert response.status_code == 201
    assert response.json()["username"] == "alice"


async def test_duplicate_username_returns_conflict(client) -> None:
    await _register(client)
    response = await _register(client)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "USERNAME_TAKEN"


async def test_register_rejects_weak_and_oversized_credentials(client) -> None:
    short = await _register(client, username="ab", password="passw0rd123")
    assert short.status_code == 422
    long_password = await _register(
        client, username="bob", password="a" * 73
    )
    assert long_password.status_code == 422


async def test_client_supplied_user_id_is_rejected(client) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "alice",
            "password": "passw0rd123",
            "user_id": "hacker-chosen-id",
        },
    )
    assert response.status_code == 422


async def test_login_and_me_roundtrip(client) -> None:
    await _register(client)
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "passw0rd123"},
    )
    assert login.status_code == 200
    token = login.json()
    assert token["token_type"] == "bearer"
    assert token["access_token"]

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["username"] == "alice"


async def test_login_rejects_wrong_password_and_unknown_user(client) -> None:
    await _register(client)
    wrong_password = await client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "wrong-password"},
    )
    assert wrong_password.status_code == 401
    assert (
        wrong_password.json()["error"]["code"] == "INVALID_CREDENTIALS"
    )

    unknown = await client.post(
        "/api/v1/auth/login",
        json={"username": "nobody", "password": "passw0rd123"},
    )
    assert unknown.status_code == 401
    assert unknown.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_me_requires_valid_token(client) -> None:
    no_token = await client.get("/api/v1/auth/me")
    assert no_token.status_code == 401
    assert no_token.json()["error"]["code"] == "UNAUTHENTICATED"

    garbage = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer garbage"}
    )
    assert garbage.status_code == 401
    assert garbage.json()["error"]["code"] == "INVALID_TOKEN"


async def test_expired_token_is_rejected(client) -> None:
    settings = get_settings()
    expired = create_access_token(
        "some-user", settings.jwt_secret, expires_minutes=-1
    )
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


async def test_token_for_deleted_user_is_rejected(client) -> None:
    await _register(client)
    settings = get_settings()
    async with get_session_maker()() as session:
        result = await session.execute(
            select(UserModel).where(UserModel.username == "alice")
        )
        model = result.scalar_one()
        user_id = model.id
        await session.delete(model)
        await session.commit()

    token = create_access_token(
        user_id, settings.jwt_secret, settings.access_token_expire_minutes
    )
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


async def test_password_hash_helpers_roundtrip() -> None:
    hashed = await asyncio.to_thread(hash_password, "passw0rd123")
    assert hashed != "passw0rd123"
    assert await asyncio.to_thread(verify_password, "passw0rd123", hashed)
    assert not await asyncio.to_thread(
        verify_password, "wrong-password", hashed
    )


async def test_me_returns_own_user_only(client) -> None:
    await _register(client, username="alice")
    await _register(client, username="bob")
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "passw0rd123"},
    )
    token = login.json()["access_token"]
    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.json()["username"] == "alice"
