"""Document request and response schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

DocumentType = Literal[
    "contract",
    "purchase_record",
    "warranty",
    "manual",
    "note",
    "other",
]


class DocumentOut(BaseModel):
    document_id: str
    filename: str
    file_type: str
    document_type: str
    file_size: int
    status: str
    processing_stage: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
