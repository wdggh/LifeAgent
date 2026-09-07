"""Request id correlation behavior."""


def test_response_carries_generated_request_id(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers["x-request-id"]


def test_response_echoes_client_supplied_request_id(client) -> None:
    response = client.get(
        "/api/v1/health", headers={"X-Request-ID": "client-supplied-id-123"}
    )
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "client-supplied-id-123"
