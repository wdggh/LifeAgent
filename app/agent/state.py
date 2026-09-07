"""Runtime state for one Agent run."""

from dataclasses import dataclass, field

from app.domain.models.search_result import SearchResult


@dataclass
class AgentRunState:
    user_id: str
    conversation_id: str
    query: str
    iteration: int = 0
    retrieval_count: int = 0
    status: str = "planning"
    steps: list[dict] = field(default_factory=list)
    results: list[SearchResult] = field(default_factory=list)
    final_answer: str | None = None
