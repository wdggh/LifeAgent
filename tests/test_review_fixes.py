"""Regression tests for post-review fixes."""

from datetime import datetime, timedelta, timezone

import httpx
import pytest_asyncio

import app.worker as worker_module
from app.agent.tools.search_knowledge import SearchKnowledgeTool
from app.agent.tools.base import ToolContext
from app.api.dependencies import (
    get_ingestion_dispatcher,
    get_llm_client,
    get_retriever,
)
from app.core.config import get_settings
from app.domain.models.llm import ChatMessage, LLMResponse, ToolCallRequest
from app.infrastructure.database.models.agent_run import AgentRunModel
from app.infrastructure.database.models.document import DocumentModel
from app.infrastructure.database.session import get_session_maker
from app.infrastructure.embedding.base import EmbeddingClient
from app.infrastructure.llm.base import LLMClient
from app.rag.retrieval.retriever import Retriever
from app.main import app


class FakeEmbeddingClient(EmbeddingClient):
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [
            [float((idx + j) % 7 + 1) for j in range(4)]
            for idx, _ in enumerate(texts)
        ]


class ScriptedLLM(LLMClient):
    def __init__(self, script: list[LLMResponse]) -> None:
        self.script = list(script)

    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list | None = None,
    ) -> LLMResponse:
        return self.script.pop(0)


class RecordingRetriever:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def search(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        document_type: str | None = None,
        document_id: str | None = None,
    ):
        self.calls.append(
            {
                "query": query,
                "user_id": user_id,
                "top_k": top_k,
                "document_type": document_type,
                "document_id": document_id,
            }
        )
        return []


def _tool_call(name: str, arguments: dict) -> LLMResponse:
    return LLMResponse(
        tool_calls=[
            ToolCallRequest(id=f"call_{name}", name=name, arguments=arguments)
        ]
    )


async def test_search_tool_rejects_invalid_top_k_and_document_type() -> None:
    retriever = RecordingRetriever()
    tool = SearchKnowledgeTool(retriever)  # type: ignore[arg-type]
    context = ToolContext(user_id="user_1")

    bad_top_k = await tool.run({"query": "q", "top_k": "abc"}, context)
    assert bad_top_k.error == "invalid top_k"
    assert "top_k" in bad_top_k.text

    bad_type = await tool.run(
        {"query": "q", "document_type": "secret"}, context
    )
    assert bad_type.error == "invalid document_type"

    assert retriever.calls == []


async def test_search_tool_caps_results_per_round() -> None:
    retriever = RecordingRetriever()
    tool = SearchKnowledgeTool(retriever)  # type: ignore[arg-type]
    result = await tool.run({"query": "q", "top_k": 10}, ToolContext("user_1"))
    assert result.error is None
    assert retriever.calls[0]["top_k"] == 4


async def test_chat_invalid_tool_args_returns_200_with_step_error(
    client, auth_headers
) -> None:
    async def llm_override():
        return ScriptedLLM(
            [
                _tool_call("search_knowledge", {"query": "x", "top_k": "abc"}),
                LLMResponse(content="参数有误，我继续回答。"),
            ]
        )

    async def retriever_override():
        return Retriever(
            embedding_client=FakeEmbeddingClient(),
            vector_repository=None,  # type: ignore[arg-type]
        )

    app.dependency_overrides[get_llm_client] = llm_override
    app.dependency_overrides[get_retriever] = retriever_override
    try:
        conversation = await client.post(
            "/api/v1/conversations", json={}, headers=auth_headers
        )
        conversation_id = conversation.json()["conversation_id"]
        response = await client.post(
            "/api/v1/chat",
            json={"conversation_id": conversation_id, "query": "问一下"},
            headers=auth_headers,
        )
        assert response.status_code == 200, response.text
        assert response.json()["metadata"]["retrieval_count"] == 0

        async with get_session_maker()() as session:
            from sqlalchemy import select

            result = await session.execute(
                select(AgentRunModel).where(
                    AgentRunModel.conversation_id == conversation_id
                )
            )
            run = result.scalar_one()
            assert run.status == "completed"
            assert run.steps[0]["error"] == "invalid top_k"
    finally:
        app.dependency_overrides.pop(get_llm_client, None)
        app.dependency_overrides.pop(get_retriever, None)


async def test_upload_rolls_back_when_enqueue_fails(
    client, auth_headers, tmp_path
) -> None:
    get_settings().upload_dir = str(tmp_path)

    async def failing_dispatcher(document_id: str) -> None:
        raise RuntimeError("redis down")

    async def override():
        return failing_dispatcher

    app.dependency_overrides[get_ingestion_dispatcher] = override
    try:
        response = await client.post(
            "/api/v1/documents",
            files={"file": ("note.txt", b"content")},
            data={"document_type": "note"},
            headers=auth_headers,
        )
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"

        listing = await client.get(
            "/api/v1/documents", headers=auth_headers
        )
        assert listing.json() == []
        assert list(tmp_path.iterdir()) == []
    finally:
        app.dependency_overrides.pop(get_ingestion_dispatcher, None)


async def test_worker_startup_sweep_requeues_only_stale(
    client, auth_headers, monkeypatch
) -> None:
    username = "sweep_user"
    register = await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": "passw0rd123"},
    )
    user_id = register.json()["user_id"]
    now = datetime.now(timezone.utc)

    async with get_session_maker()() as session:
        stale = DocumentModel(
            user_id=user_id,
            filename="stale.txt",
            file_type="txt",
            file_path="stale",
            file_size=1,
            document_type="note",
            status="processing",
            updated_at=now - timedelta(minutes=30),
        )
        fresh = DocumentModel(
            user_id=user_id,
            filename="fresh.txt",
            file_type="txt",
            file_path="fresh",
            file_size=1,
            document_type="note",
            status="processing",
            updated_at=now - timedelta(minutes=1),
        )
        session.add_all([stale, fresh])
        await session.commit()
        stale_id = stale.id
        fresh_id = fresh.id

    enqueued: list[str] = []

    async def fake_enqueue(document_id: str) -> bool:
        enqueued.append(document_id)
        return True

    monkeypatch.setattr(
        worker_module, "enqueue_document_ingestion", fake_enqueue
    )
    await worker_module.sweep_stale_processing()
    assert stale_id in enqueued
    assert fresh_id not in enqueued
