"""Unified error body and the protected-route 401 convention."""

import httpx
from fastapi import Depends, FastAPI

from app.api.dependencies import get_current_user
from app.core.exceptions import register_exception_handlers


async def test_unknown_route_returns_unified_404(client) -> None:
    response = await client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert set(body["error"]) == {"code", "message", "request_id"}
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["request_id"] == response.headers["x-request-id"]


async def _probe_response(
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    probe_app = FastAPI()
    register_exception_handlers(probe_app)

    @probe_app.get("/probe", dependencies=[Depends(get_current_user)])
    def probe() -> dict[str, bool]:
        return {"ok": True}

    transport = httpx.ASGITransport(app=probe_app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as probe_client:
        return await probe_client.get("/probe", headers=headers or {})


async def test_missing_token_on_protected_route_returns_401() -> None:
    response = await _probe_response()
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


async def test_malformed_token_on_protected_route_returns_401() -> None:
    response = await _probe_response(
        {"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"
