"""Conversation entity."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Conversation:
    id: str
    user_id: str
    title: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None
