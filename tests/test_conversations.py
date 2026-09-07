"""Conversation management behavior."""

import httpx


async def _create_conversation(
    client: httpx.AsyncClient, auth_headers: dict[str, str], title: str | None = None
) -> httpx.Response:
    body = {"title": title} if title is not None else {}
    return await client.post(
        "/api/v1/conversations",
        json=body,
        headers=auth_headers,
    )


async def test_create_conversation_without_title(client, auth_headers) -> None:
    response = await _create_conversation(client, auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["conversation_id"]
    assert body["title"] is None
    assert body["created_at"]


async def test_create_conversation_with_title(client, auth_headers) -> None:
    response = await _create_conversation(
        client, auth_headers, title=" 我的健身问题 "
    )
    assert response.status_code == 201
    assert response.json()["title"] == "我的健身问题"


async def test_list_returns_own_conversations_newest_first(
    client, auth_headers
) -> None:
    first = await _create_conversation(client, auth_headers, title="first")
    second = await _create_conversation(client, auth_headers, title="second")
    listing = await client.get("/api/v1/conversations", headers=auth_headers)
    assert listing.status_code == 200
    ids = [item["conversation_id"] for item in listing.json()]
    assert ids == [second.json()["conversation_id"], first.json()["conversation_id"]]


async def test_detail_includes_messages(client, auth_headers) -> None:
    created = await _create_conversation(client, auth_headers, title="chat")
    conversation_id = created.json()["conversation_id"]
    detail = await client.get(
        f"/api/v1/conversations/{conversation_id}",
        headers=auth_headers,
    )
    assert detail.status_code == 200
    body = detail.json()
    assert body["conversation_id"] == conversation_id
    assert body["messages"] == []


async def test_delete_removes_conversation_and_messages(
    client, auth_headers
) -> None:
    from app.infrastructure.database.models.conversation import MessageModel
    from app.infrastructure.database.session import get_session_maker

    created = await _create_conversation(client, auth_headers)
    conversation_id = created.json()["conversation_id"]

    async with get_session_maker()() as session:
        session.add(
            MessageModel(
                conversation_id=conversation_id,
                role="user",
                content="hello",
            )
        )
        await session.commit()

    deleted = await client.delete(
        f"/api/v1/conversations/{conversation_id}",
        headers=auth_headers,
    )
    assert deleted.status_code == 204

    missing = await client.get(
        f"/api/v1/conversations/{conversation_id}",
        headers=auth_headers,
    )
    assert missing.status_code == 404

    async with get_session_maker()() as session:
        from sqlalchemy import func, select

        result = await session.execute(
            select(func.count()).select_from(MessageModel)
        )
        assert result.scalar_one() == 0


async def test_cross_user_conversation_is_404(
    client, auth_headers, auth_headers_second
) -> None:
    created = await _create_conversation(
        client, auth_headers, title="private"
    )
    conversation_id = created.json()["conversation_id"]

    detail = await client.get(
        f"/api/v1/conversations/{conversation_id}",
        headers=auth_headers_second,
    )
    assert detail.status_code == 404
    assert detail.json()["error"]["code"] == "CONVERSATION_NOT_FOUND"

    deleted = await client.delete(
        f"/api/v1/conversations/{conversation_id}",
        headers=auth_headers_second,
    )
    assert deleted.status_code == 404


async def test_conversations_require_authentication(client) -> None:
    assert (await client.get("/api/v1/conversations")).status_code == 401
    assert (
        await client.post("/api/v1/conversations", json={})
    ).status_code == 401
