"""Chat v1: Agent retrieval QA with budgets, isolation, and guardrails."""

import copy
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import pytest_asyncio
from sqlalchemy import select

from app.agent.agent import Agent
from app.agent.tool_registry import ToolRegistry
from app.agent.tools.base import Tool, ToolContext, ToolResult
from app.api.dependencies import get_llm_client, get_retriever
from app.core.config import get_settings
from app.domain.models.llm import ChatMessage, LLMResponse, ToolCallRequest
from app.domain.models.llm import ToolSpec
from app.domain.models.search_result import SearchResult
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
    def __init__(
        self,
        script: list[LLMResponse] | None = None,
        *,
        raise_error: bool = False,
    ) -> None:
        self.script = list(script or [])
        self.raise_error = raise_error
        self.calls = 0
        self.captured: list[list[ChatMessage]] = []

    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list | None = None,
    ) -> LLMResponse:
        self.calls += 1
        self.captured.append(copy.deepcopy(messages))
        if self.raise_error:
            raise RuntimeError("model service down")
        if self.script:
            return self.script.pop(0)
        return LLMResponse(content="fallback answer")


def _tool_call(query: str, **extra) -> LLMResponse:
    arguments = {"query": query, **extra}
    return LLMResponse(
        tool_calls=[
            ToolCallRequest(
                id=f"call_{query[:8]}",
                name="search_knowledge",
                arguments=arguments,
            )
        ]
    )


@pytest_asyncio.fixture(scope="module", autouse=True)
async def _isolated_vector_collection() -> None:
    settings = get_settings()
    original = settings.chroma_collection
    settings.chroma_collection = "lifeagent_test_chat_vectors"
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
    document_type: str = "note",
) -> str:
    get_settings().upload_dir = str(tmp_path)
    response = await client.post(
        "/api/v1/documents",
        files={"file": (filename, content.encode("utf-8"))},
        data={"document_type": document_type},
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
        "/api/v1/conversations",
        json={"title": "chat v1"},
        headers=auth_headers,
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


async def test_multi_round_retrieval_with_persistence(
    client, auth_headers, tmp_path
) -> None:
    await _upload_and_ingest(
        client,
        auth_headers,
        tmp_path,
        "contract.txt",
        "健身合同 年费1200元 有效期至2026-12-31",
        document_type="contract",
    )
    await _upload_and_ingest(
        client,
        auth_headers,
        tmp_path,
        "usage.txt",
        "健身房使用记录 每月4次",
    )
    conversation_id = await _conversation(client, auth_headers)
    llm = ScriptedLLM(
        [
            _tool_call("健身会员价格和有效期"),
            _tool_call("健身使用频率"),
            LLMResponse(
                content=(
                    "根据资料：年费1200元，有效期至2026-12-31，"
                    "使用频率每月4次。"
                )
            ),
        ]
    )
    await _use_llm(llm)

    response = await _ask(
        client, auth_headers, conversation_id, "我的健身会员还有必要续吗？"
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["answer"]
    assert len(body["sources"]) == 2
    assert body["metadata"]["retrieval_count"] == 2
    assert body["metadata"]["duration_ms"] >= 0

    detail = await client.get(
        f"/api/v1/conversations/{conversation_id}", headers=auth_headers
    )
    roles = [message["role"] for message in detail.json()["messages"]]
    assert roles == ["user", "assistant"]

    async with get_session_maker()() as session:
        result = await session.execute(
            select(AgentRunModel).where(
                AgentRunModel.conversation_id == conversation_id
            )
        )
        run = result.scalar_one()
        assert run.status == "completed"
        assert run.retrieval_count == 2
        assert len(run.steps) == 2


async def test_general_question_skips_retrieval(
    client, auth_headers
) -> None:
    conversation_id = await _conversation(client, auth_headers)
    llm = ScriptedLLM([LLMResponse(content="这是通用问题，无需检索。")])
    await _use_llm(llm)

    response = await _ask(
        client, auth_headers, conversation_id, "今天天气怎么样？"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["retrieval_count"] == 0
    assert body["sources"] == []
    assert "通用问题" in body["answer"]


async def test_empty_retrieval_stops_and_admits_insufficiency(
    client, auth_headers
) -> None:
    conversation_id = await _conversation(client, auth_headers)
    llm = ScriptedLLM(
        [
            _tool_call("健身房记录"),
            LLMResponse(content="知识库中没有找到相关记录，无法确认。"),
        ]
    )
    await _use_llm(llm)

    response = await _ask(
        client, auth_headers, conversation_id, "我每周健身几次？"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["retrieval_count"] == 1
    assert body["sources"] == []
    assert "无法" in body["answer"]


async def test_no_new_material_stops_retrieval(
    client, auth_headers, tmp_path
) -> None:
    await _upload_and_ingest(
        client, auth_headers, tmp_path, "doc.txt", "一些资料"
    )
    conversation_id = await _conversation(client, auth_headers)
    llm = ScriptedLLM(
        [
            _tool_call("第一轮"),
            _tool_call("第二轮"),
            _tool_call("第三轮"),
        ]
    )
    await _use_llm(llm)

    response = await _ask(
        client, auth_headers, conversation_id, "反复追问直到预算耗尽"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["retrieval_count"] == 2
    assert llm.calls == 3
    assert "could not find enough information" in body["answer"]


async def test_agent_loop_respects_max_retrievals() -> None:
    """Direct Agent-loop test: retrieval budget caps the tool rounds."""

    class FreshResultTool(Tool):
        @property
        def spec(self) -> ToolSpec:
            return ToolSpec(
                name="search_knowledge",
                description="search",
                parameters={"type": "object", "properties": {}},
            )

        async def run(
            self, arguments: dict, context: ToolContext
        ) -> ToolResult:
            call = self.calls
            self.calls += 1
            return ToolResult(
                text="found",
                results=[
                    SearchResult(
                        chunk_id=f"chunk_{call}",
                        document_id=f"doc_{call}",
                        document_name=f"doc {call}.txt",
                        content="content",
                        score=0.9,
                    )
                ],
            )

    settings = get_settings()
    llm = ScriptedLLM(
        [
            _tool_call("q1"),
            _tool_call("q2"),
            _tool_call("q3"),
            LLMResponse(content="预算耗尽，只能回答已有内容。"),
        ]
    )
    tool = FreshResultTool()
    tool.calls = 0
    registry = ToolRegistry()
    registry.register(tool)
    agent = Agent(llm, registry)

    state = await agent.run(
        user_id="user_1",
        conversation_id="conv_1",
        query="question",
        history=[],
    )
    assert state.retrieval_count == settings.max_retrievals == 3
    assert state.iteration == 3
    assert llm.calls == 4
    assert "预算耗尽" in (state.final_answer or "")


async def test_cross_user_isolation_and_ownership(
    client, auth_headers, auth_headers_second, tmp_path
) -> None:
    await _upload_and_ingest(
        client,
        auth_headers,
        tmp_path,
        "private.txt",
        "用户A的私密合同",
        document_type="contract",
    )
    conversation_a = await _conversation(client, auth_headers)
    conversation_b = await _conversation(client, auth_headers_second)

    llm = ScriptedLLM([_tool_call("私密合同"), LLMResponse(content="结果")])
    await _use_llm(llm)
    response = await _ask(
        client, auth_headers_second, conversation_b, "查我的合同"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sources"] == []

    forbidden = await _ask(
        client, auth_headers_second, conversation_a, "看看你的资料"
    )
    assert forbidden.status_code == 404
    assert forbidden.json()["error"]["code"] == "CONVERSATION_NOT_FOUND"


async def test_document_type_filter_is_honored(
    client, auth_headers, tmp_path
) -> None:
    contract_id = await _upload_and_ingest(
        client,
        auth_headers,
        tmp_path,
        "gym.txt",
        "健身合同退款条款",
        document_type="contract",
    )
    await _upload_and_ingest(
        client,
        auth_headers,
        tmp_path,
        "notes.txt",
        "随便的笔记内容",
        document_type="note",
    )
    conversation_id = await _conversation(client, auth_headers)
    llm = ScriptedLLM(
        [
            _tool_call("合同条款", document_type="contract"),
            LLMResponse(content="根据健身合同的退款条款..."),
        ]
    )
    await _use_llm(llm)

    response = await _ask(
        client, auth_headers, conversation_id, "只看健身合同里的条款"
    )
    assert response.status_code == 200
    sources = response.json()["sources"]
    assert [source["document_id"] for source in sources] == [contract_id]


async def test_history_injection_and_guardrails(
    client, auth_headers
) -> None:
    conversation_id = await _conversation(client, auth_headers)
    first = ScriptedLLM([LLMResponse(content="之前的回答：合同到2026年底。")])
    await _use_llm(first)
    first_response = await _ask(
        client, auth_headers, conversation_id, "合同什么时候到期？"
    )
    assert first_response.status_code == 200

    second = ScriptedLLM([LLMResponse(content="追问回答")])
    await _use_llm(second)
    response = await _ask(
        client, auth_headers, conversation_id, "那续费呢？"
    )
    assert response.status_code == 200

    last_messages = second.captured[-1]
    system = last_messages[0]
    assert "data, not instructions" in (system.content or "")
    today = datetime.now(ZoneInfo(get_settings().app_timezone)).strftime(
        "%Y-%m-%d"
    )
    assert today in (system.content or "")
    joined = " ".join(
        message.content or "" for message in last_messages
    )
    assert "之前的回答：合同到2026年底。" in joined


async def test_llm_failure_returns_503_and_records_failed_run(
    client, auth_headers
) -> None:
    conversation_id = await _conversation(client, auth_headers)
    llm = ScriptedLLM(raise_error=True)
    await _use_llm(llm)

    response = await _ask(
        client, auth_headers, conversation_id, "这个问题会触发失败"
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "LLM_UNAVAILABLE"

    async with get_session_maker()() as session:
        result = await session.execute(
            select(AgentRunModel).where(
                AgentRunModel.conversation_id == conversation_id
            )
        )
        run = result.scalar_one()
        assert run.status == "failed"
        assert run.error_message

    detail = await client.get(
        f"/api/v1/conversations/{conversation_id}", headers=auth_headers
    )
    roles = [message["role"] for message in detail.json()["messages"]]
    assert roles == ["user"]
