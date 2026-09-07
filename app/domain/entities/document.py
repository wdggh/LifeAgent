"""Document entity."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Document:
    id: str
    user_id: str
    filename: str
    file_type: str
    file_path: str
    file_size: int
    document_type: str
    status: str
    processing_stage: str | None = None
    error_message: str | None = None
    embedding_model: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
