"""Shared uuid helper for ORM primary keys."""

import uuid


def new_uuid_hex() -> str:
    return uuid.uuid4().hex
