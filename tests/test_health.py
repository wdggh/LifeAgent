"""Health endpoint behavior."""


async def test_health_returns_healthy(client) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
