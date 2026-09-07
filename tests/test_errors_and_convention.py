"""Unified error body and the protected-route 401 convention."""

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user
from app.core.exceptions import register_exception_handlers


def test_unknown_route_returns_unified_404(client) -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert set(body["error"]) == {"code", "message", "request_id"}
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["request_id"] == response.headers["x-request-id"]


def test_missing_token_on_protected_route_returns_401() -> None:
    probe_app = FastAPI()
    register_exception_handlers(probe_app)

    @probe_app.get("/probe", dependencies=[Depends(get_current_user)])
    def probe() -> dict[str, bool]:
        return {"ok": True}

    with TestClient(probe_app) as probe_client:
        response = probe_client.get("/probe")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_malformed_token_on_protected_route_returns_401() -> None:
    probe_app = FastAPI()
    register_exception_handlers(probe_app)

    @probe_app.get("/probe", dependencies=[Depends(get_current_user)])
    def probe() -> dict[str, bool]:
        return {"ok": True}

    with TestClient(probe_app) as probe_client:
        response = probe_client.get(
            "/probe", headers={"Authorization": "Bearer not-a-real-token"}
        )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"
