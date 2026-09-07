"""Conversation request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=200)


class ConversationOut(BaseModel):
    conversation_id: str
    title: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MessageOut(BaseModel):
    message_id: str
    role: str
    content: str
    created_at: datetime | None = None


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut] = []
