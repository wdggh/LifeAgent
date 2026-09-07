"""Chat request and response schemas."""

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: str
    query: str = Field(min_length=1, max_length=4000)


class SourceOut(BaseModel):
    document_id: str
    document_name: str
    relevance: float


class ChatMetadataOut(BaseModel):
    retrieval_count: int
    duration_ms: int


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceOut]
    metadata: ChatMetadataOut
