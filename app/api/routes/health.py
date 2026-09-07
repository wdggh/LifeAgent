"""Health check endpoint."""

from fastapi import APIRouter
from redis.asyncio import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.infrastructure.database.session import get_session_maker
from app.infrastructure.vector_store.chroma import _build_client

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/health/detailed", summary="Dependency health check")
async def health_detailed() -> dict:
    """Return per-dependency status; 503 when any dependency is down."""

    checks: dict[str, str] = {}

    try:
        async with get_session_maker()() as session:
            await session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "unavailable"

    redis_client = Redis.from_url(get_settings().redis_url)
    try:
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unavailable"
    finally:
        await redis_client.aclose()

    try:
        _build_client().heartbeat()
        checks["chroma"] = "ok"
    except Exception:
        checks["chroma"] = "unavailable"

    failed = [name for name, status in checks.items() if status != "ok"]
    if failed:
        raise AppError(
            503,
            "SERVICE_UNAVAILABLE",
            "Unavailable dependencies: " + ", ".join(failed),
        )
    return {"status": "healthy", "checks": checks}
