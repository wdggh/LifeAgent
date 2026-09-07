"""Document endpoints (ticket 04)."""

from fastapi import APIRouter

router = APIRouter(prefix="/documents", tags=["documents"])
