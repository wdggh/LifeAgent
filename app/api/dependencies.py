"""Dependencies shared by protected routes.

Ticket 01 establishes the authentication convention: a missing or malformed
Authorization header yields 401 with the unified error body. Real token
verification and user loading land in ticket 02.
"""

from fastapi import Header

from app.core.exceptions import AppError


def get_current_user(
    authorization: str | None = Header(default=None),
) -> None:
    """Placeholder auth guard; returns the current user once ticket 02 lands."""

    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(401, "UNAUTHENTICATED", "Authentication required")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise AppError(401, "UNAUTHENTICATED", "Authentication required")
    # TODO(ticket 02): verify JWT and load the current user.
    raise AppError(401, "INVALID_TOKEN", "Invalid or expired token")
