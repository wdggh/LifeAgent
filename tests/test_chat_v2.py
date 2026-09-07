"""Chat v2: get_document deep-dive behavior."""

import copy

import httpx
import pytest_asyncio
from sqlalchemy import select

from app.api.dependencies import get_llm_client, get_retriever
from app.core.config import get_settings
from app.domain.models.llm import ChatMessage, LLMResponse, ToolCallRequest
from app.infrastructure.database.models.agent_run import AgentRunModel
from app.infrastructure.database.session import get_session_maker
from app.infrastructure.database.document_repository import (
    SQLAlchemyDocumentRepository,
)
from app.infrastructure.embedding.base import EmbeddingClient
from app.infrastructure.llm.base import LLMClient
from app.infrastructure.vector_store.chroma import (
    ChromaVectorRepository,
    reset_collection,
)
from app.rag.retrieval.retriever import Retriever
from app.services.knowledge_service import KnowledgeService
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
        self.captured: list[list[ChatMessage]] = []

    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list | None = None,
    ) -> LLMResponse:
        self.captured.append(copy.deepcopy(messages))
        return self.script.pop(0)


def _tool_call(name: str, arguments: dict) -> LLMResponse:
    return LLMResponse(
        tool_calls=[
            ToolCallRequest(
                id=f"call_{name}", name=name, arguments=arguments
            )
        ]
    )


@pytest_asyncio.fixture(scope="module", autouse=True)
async def _isolated_vector_collection() -> None:
    settings = get_settings()
    original = settings.chroma_collection
    settings.chroma_collection = "lifeagent_test_chat_v2_vectors"
    reset_collection(settings.chroma_collection)
    yield
    settings.chroma_collection = original


@pytest_asyncio.fixture(autouse=True)
async def _fake_retriever():
    async def override():
        return Retriever(
            embedding_client=FakeEmbeddingClient(),
            vector_repository=ChromaVectorRepository(),
        )

    app.dependency_overrides[get_retriever] = override
    yield
    app.dependency_overrides.pop(get_retriever, None)


async def _use_llm(llm: ScriptedLLM) -> None:
    async def override():
        return llm

    app.dependency_overrides[get_llm_client] = override


async def _upload_and_ingest(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    tmp_path,
    filename: str,
    content: str,
) -> str:
    get_settings().upload_dir = str(tmp_path)
    response = await client.post(
        "/api/v1/documents",
        files={"file": (filename, content.encode("utf-8"))},
        data={"document_type": "contract"},
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    document_id = response.json()["document_id"]
    async with get_session_maker()() as session:
        service = KnowledgeService(
            document_repository=SQLAlchemyDocumentRepository(session),
            embedding_client=FakeEmbeddingClient(),
            vector_repository=ChromaVectorRepository(),
        )
        await service.ingest(document_id)
    return document_id


async def _conversation(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
) -> str:
    response = await client.post(
        "/api/v1/conversations", json={}, headers=auth_headers
    )
    assert response.status_code == 201
    return response.json()["conversation_id"]


async def _ask(
    client: httpx.AsyncClient,
    auth_headers: dict[str, str],
    conversation_id: str,
    query: str,
) -> httpx.Response:
    return await client.post(
        "/api/v1/chat",
        json={"conversation_id": conversation_id, "query": query},
        headers=auth_headers,
    )


async def test_deep_dive_reads_specific_document_and_answers(
    client, auth_headers, tmp_path
) -> None:
    content = (
        "合同开头普通条款。\n"
        + ("占位内容 " * 200)
        + "\n退款条款：30 天内可全额退款。"
    )
    document_id = await _upload_and_ingest(
        client, auth_headers, tmp_path, "contract.txt", content
    )
    conversation_id = await _conversation(client, auth_headers)
    llm = ScriptedLLM(
        [
            _tool_call("search_knowledge", {"query": "退款"}),
            _tool_call(
                "get_document",
                {"document_id": document_id, "page": 1, "max_chars": 8000},
            ),
            LLMResponse(content="退款条款：30 天内可全额退款。"),
        ]
    )
    await _use_llm(llm)

    response = await _ask(
        client, auth_headers, conversation_id, "这份合同里的退款条款是什么？"
    )
    assert response.status_code == 200, response.text
    assert "全额退款" in response.json()["answer"]
    assert response.json()["metadata"]["retrieval_count"] == 1

    tool_texts = []
    for messages in llm.captured:
        tool_texts.extend(
            message.content or "" for message in messages
            if message.role == "tool"
        )
    assert any("page 1" in text for text in tool_texts)
    assert any("30 天内可全额退款" in text for text in tool_texts)

    async with get_session_maker()() as session:
        result = await session.execute(
            select(AgentRunModel).where(
                AgentRunModel.conversation_id == conversation_id
            )
        )
        run = result.scalar_one()
        tool_names = [step["tool"] for step in run.steps]
        assert tool_names == ["search_knowledge", "get_document"]
        assert run.steps[1]["args_summary"]["document_id"] == document_id
        assert run.steps[1]["args_summary"]["page"] == 1


async def test_other_users_document_is_not_readable(
    client, auth_headers, auth_headers_second, tmp_path
) -> None:
    document_id = await _upload_and_ingest(
        client,
        auth_headers,
        tmp_path,
        "secret.txt",
        "用户A的机密退款条款内容",
    )
    conversation_b = await _conversation(client, auth_headers_second)
    llm = ScriptedLLM(
        [
            _tool_call(
                "get_document",
                {"document_id": document_id, "max_chars": 8000},
            ),
            LLMResponse(content="我没有读到相关内容。"),
        ]
    )
    await _use_llm(llm)

    response = await _ask(
        client,
        auth_headers_second,
        conversation_b,
        "读取那份合同",
    )
    assert response.status_code == 200
    assert response.json()["sources"] == []

    tool_text = next(
        message.content or ""
        for messages in llm.captured
        for message in messages
        if message.role == "tool"
    )
    assert "not found or not accessible" in tool_text
    assert "机密" not in tool_text


async def test_invalid_arguments_fail_gracefully(
    client, auth_headers, tmp_path
) -> None:
    await _upload_and_ingest(
        client, auth_headers, tmp_path, "doc.txt", "内容"
    )
    conversation_id = await _conversation(client, auth_headers)
    llm = ScriptedLLM(
        [
            _tool_call(
                "get_document",
                {"document_id": "", "page": -5, "max_chars": "bad"},
            ),
            LLMResponse(content="参数不对，但我继续回答了。"),
        ]
    )
    await _use_llm(llm)

    response = await _ask(
        client, auth_headers, conversation_id, "读文档"
    )
    assert response.status_code == 200
    tool_text = next(
        message.content or ""
        for messages in llm.captured
        for message in messages
        if message.role == "tool"
    )
    assert "document_id is required" in tool_text

    async with get_session_maker()() as session:
        result = await session.execute(
            select(AgentRunModel).where(
                AgentRunModel.conversation_id == conversation_id
            )
        )
        assert result.scalar_one().status == "completed"


async def test_get_document_respects_max_chars(
    client, auth_headers, tmp_path
) -> None:
    long_content = "正文内容" + ("x" * 5000)
    await _upload_and_ingest(
        client, auth_headers, tmp_path, "long.txt", long_content
    )
    conversation_id = await _conversation(client, auth_headers)

    # Learn the document id by listing documents.
    listing = await client.get("/api/v1/documents", headers=auth_headers)
    document_id = listing.json()[0]["document_id"]

    llm = ScriptedLLM(
        [
            _tool_call(
                "get_document",
                {"document_id": document_id, "max_chars": 300},
            ),
            LLMResponse(content="读到了开头。"),
        ]
    )
    await _use_llm(llm)

    response = await _ask(
        client, auth_headers, conversation_id, "读长文档"
    )
    assert response.status_code == 200
    tool_text = next(
        message.content or ""
        for messages in llm.captured
        for message in messages
        if message.role == "tool"
    )
    assert "truncated to 300 chars" in tool_text
    assert len(tool_text) < 1000
    assert long_content not in tool_text


async def test_missing_page_is_reported_without_crash(
    client, auth_headers, tmp_path
) -> None:
    await _upload_and_ingest(
        client, auth_headers, tmp_path, "one_page.txt", "只有一页"
    )
    conversation_id = await _conversation(client, auth_headers)
    listing = await client.get("/api/v1/documents", headers=auth_headers)
    document_id = listing.json()[0]["document_id"]

    llm = ScriptedLLM(
        [
            _tool_call(
                "get_document",
                {"document_id": document_id, "page": 99},
            ),
            LLMResponse(content="页码不存在，我如实回答。"),
        ]
    )
    await _use_llm(llm)

    response = await _ask(
        client, auth_headers, conversation_id, "读第99页"
    )
    assert response.status_code == 200
    tool_text = next(
        message.content or ""
        for messages in llm.captured
        for message in messages
        if message.role == "tool"
    )
    assert "Page 99 not found" in tool_text
