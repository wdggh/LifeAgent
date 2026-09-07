"""SQLAlchemy ORM models."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


def _uuid_hex() -> str:
    return uuid.uuid4().hex


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=_uuid_hex
    )
    username: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
