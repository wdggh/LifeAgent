"""Health endpoint behavior."""


def test_health_returns_healthy(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
