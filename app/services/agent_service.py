"""Agent chat orchestration: history, run, persistence, response."""

import logging
import time
from dataclasses import dataclass, field

from app.agent.agent import Agent
from app.agent.tool_registry import ToolRegistry
from app.agent.tools.get_document import GetDocumentTool
from app.agent.tools.search_knowledge import SearchKnowledgeTool
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.domain.constants import AgentRunStatus, MessageRole
from app.domain.entities.user import User
from app.domain.models.llm import ChatMessage
from app.domain.models.search_result import SearchResult
from app.infrastructure.llm.base import LLMClient
from app.infrastructure.vector_store.chroma import ChromaVectorRepository
from app.rag.query.expansion import QueryExpander
from app.rag.query.rewriter import QueryRewriter
from app.rag.retrieval.retriever import Retriever
from app.rag.retrieval.sparse import (
    BM25SparseSearcher,
    RedisCorpusVersionStore,
)
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.document_repository import DocumentRepository

logger = logging.getLogger("app.agent")


@dataclass
class AgentChatResult:
    answer: str
    sources: list[dict] = field(default_factory=list)
    retrieval_count: int = 0
    duration_ms: int = 0
    # Per-tool-call trace (V2.3d agent-context measurement). Internal: the API
    # response schema does not expose it.
    steps: list[dict] = field(default_factory=list)


class AgentService:
    def __init__(
        self,
        conversation_repository: ConversationRepository,
        agent_run_repository: AgentRunRepository,
        document_repository: DocumentRepository,
        llm_client: LLMClient,
        retriever: Retriever,
        sparse_searcher: BM25SparseSearcher | None = None,
    ) -> None:
        self._conversations = conversation_repository
        self._runs = agent_run_repository
        self._documents = document_repository
        self._llm = llm_client
        self._retriever = retriever
        self._sparse_searcher = sparse_searcher
        self._settings = get_settings()

    async def ask(
        self, conversation_id: str, current_user: User, query: str
    ) -> AgentChatResult:
        conversation = await self._conversations.get_by_id_and_user(
            conversation_id, current_user.id
        )
        if conversation is None:
            raise AppError(
                404, "CONVERSATION_NOT_FOUND", "Conversation not found"
            )

        await self._conversations.add_message(
            conversation_id, MessageRole.USER, query
        )
        history_messages = await self._conversations.list_messages(
            conversation_id
        )
        # Everything except the user message just added.
        history = self._to_llm_history(history_messages[:-1])

        registry = ToolRegistry()
        registry.register(
            SearchKnowledgeTool(
                self._retriever,
                default_top_k=self._settings.top_k_default,
                query_rewriter=QueryRewriter(self._llm),
                query_expander=QueryExpander(self._llm),
                sparse_searcher=(
                    self._sparse_searcher
                    if self._sparse_searcher is not None
                    else self._build_sparse_searcher()
                ),
            )
        )
        registry.register(GetDocumentTool(self._documents))
        agent = Agent(self._llm, registry)
        started = time.perf_counter()
        try:
            state = await agent.run(
                user_id=current_user.id,
                conversation_id=conversation_id,
                query=query,
                history=history,
            )
        except Exception as exc:
            duration_ms = round((time.perf_counter() - started) * 1000)
            logger.exception("agent run failed", exc_info=exc)
            await self._runs.create(
                user_id=current_user.id,
                conversation_id=conversation_id,
                query=query,
                status=AgentRunStatus.FAILED,
                iterations=0,
                retrieval_count=0,
                duration_ms=duration_ms,
                error_message=f"{type(exc).__name__}: {exc}",
                steps=[],
            )
            raise AppError(
                503,
                "LLM_UNAVAILABLE",
                "The AI service is temporarily unavailable, please try again",
            ) from exc

        duration_ms = round((time.perf_counter() - started) * 1000)
        run_id = await self._runs.create(
            user_id=current_user.id,
            conversation_id=conversation_id,
            query=query,
            status=AgentRunStatus.COMPLETED,
            iterations=state.iteration,
            retrieval_count=state.retrieval_count,
            duration_ms=duration_ms,
            error_message=None,
            steps=state.steps,
        )
        await self._conversations.add_message(
            conversation_id,
            MessageRole.ASSISTANT,
            state.final_answer or "",
            agent_run_id=run_id,
        )
        return AgentChatResult(
            answer=state.final_answer or "",
            sources=self._aggregate_sources(state.results),
            retrieval_count=state.retrieval_count,
            duration_ms=duration_ms,
            steps=state.steps,
        )

    def _build_sparse_searcher(self) -> BM25SparseSearcher | None:
        if not self._settings.query_sparse_enabled:
            return None
        return BM25SparseSearcher(
            document_source=self._documents,
            vector_repository_provider=lambda: ChromaVectorRepository(),
            version_store=RedisCorpusVersionStore(self._settings.redis_url),
            settings=self._settings,
        )

    @staticmethod
    def _to_llm_history(messages) -> list[ChatMessage]:
        llm_messages: list[ChatMessage] = []
        for message in messages[-10:]:
            if message.role not in {"user", "assistant"}:
                continue
            llm_messages.append(
                ChatMessage(
                    role=message.role,
                    content=(message.content or "")[:4000],
                )
            )
        return llm_messages

    @staticmethod
    def _aggregate_sources(results: list[SearchResult]) -> list[dict]:
        best: dict[str, dict] = {}
        for result in results:
            current = best.get(result.document_id)
            if current is None or result.score > current["relevance"]:
                best[result.document_id] = {
                    "document_id": result.document_id,
                    "document_name": result.document_name,
                    "relevance": result.score,
                }
        return sorted(
            best.values(), key=lambda item: item["relevance"], reverse=True
        )
