"""FastAPI application entry point."""

from fastapi import FastAPI

from app.api.routes import health
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middleware import RequestContextMiddleware

settings = get_settings()
setup_logging(settings.log_level)

app = FastAPI(
    title="LifeAgent API",
    description="Personal information and decision assistant.",
    version="0.1.0",
)

app.add_middleware(RequestContextMiddleware)
register_exception_handlers(app)

app.include_router(health.router, prefix="/api/v1")
