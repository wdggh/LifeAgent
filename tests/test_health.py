"""Health endpoint behavior."""


async def test_health_returns_healthy(client) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


async def test_detailed_health_reports_dependencies(client) -> None:
    response = await client.get("/api/v1/health/detailed")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "healthy"
    assert set(body["checks"]) == {"postgres", "redis", "chroma"}
    assert all(value == "ok" for value in body["checks"].values())
