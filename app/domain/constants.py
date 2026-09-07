"""Canonical domain vocabulary values (see CONTEXT.md)."""


class DocumentStatus:
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingStage:
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"


class MessageRole:
    USER = "user"
    ASSISTANT = "assistant"


class AgentRunStatus:
    COMPLETED = "completed"
    FAILED = "failed"
