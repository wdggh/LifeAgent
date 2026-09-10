"""V2.1 query rewrite tests (ADR-0009)."""

import asyncio

from app.agent.agent import Agent
from app.agent.tool_registry import ToolRegistry
from app.agent.tools.base import ToolContext
from app.agent.tools.search_knowledge import SearchKnowledgeTool
from app.core.config import Settings, get_settings
from app.domain.models.llm import ChatMessage, LLMResponse, ToolCallRequest
from app.domain.models.search_result import SearchResult
from app.infrastructure.llm.base import LLMClient
from app.rag.query.rewriter import MAX_QUERY_CHARS, QueryRewriter


class ScriptedRewriteLLM(LLMClient):
    def __init__(
        self,
        content: str | None = None,
        error: Exception | None = None,
        delay: float = 0.0,
    ) -> None:
        self.content = content
        self.error = error
        self.delay = delay
        self.calls: list[dict] = []

    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        self.calls.append(
            {"messages": messages, "tools": tools, "max_tokens": max_tokens}
        )
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error is not None:
            raise self.error
        return LLMResponse(content=self.content)


class RecordingRetriever:
    def __init__(self, results_per_call: int = 2) -> None:
        self.calls: list[dict] = []
        self.results_per_call = results_per_call

    async def search(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        document_type: str | None = None,
        document_id: str | None = None,
    ) -> list[SearchResult]:
        self.calls.append({"query": query, "top_k": top_k})
        count = min(self.results_per_call, top_k)
        return [
            SearchResult(
                chunk_id=f"chunk_{len(self.calls)}_{index}",
                document_id=f"doc_{index}",
                document_name=f"doc {index}.pdf",
                content="content",
                score=0.9,
            )
            for index in range(count)
        ]


async def test_rewrite_success_returns_single_query() -> None:
    llm = ScriptedRewriteLLM(content="保险 水浸损失 责任范围")
    rewriter = QueryRewriter(
        llm, Settings(query_rewrite_timeout_seconds=1.0)
    )
    result = await rewriter.rewrite("水管爆了把家里泡了，保险能赔吗？")
    assert result.rewritten is True
    assert result.query == "保险 水浸损失 责任范围"
    assert result.fallback_reason is None
    assert llm.calls[0]["max_tokens"] == 200
    assert "当前日期时间" in llm.calls[0]["messages"][1].content


async def test_rewrite_strips_wrapping_quotes() -> None:
    llm = ScriptedRewriteLLM(content="`保险 水浸损失`")
    result = await QueryRewriter(llm, Settings()).rewrite("水管爆了")
    assert result.rewritten is True
    assert result.query == "保险 水浸损失"


async def test_unique_identifier_skips_rewrite() -> None:
    llm = ScriptedRewriteLLM(content="unused")
    result = await QueryRewriter(llm, Settings()).rewrite(
        "订单 PO-2025-0099 的保修到什么时候？"
    )
    assert result.rewritten is False
    assert result.fallback_reason == "unique_id"
    assert result.query == "订单 PO-2025-0099 的保修到什么时候？"
    assert llm.calls == []


async def test_timeout_falls_back_to_original() -> None:
    llm = ScriptedRewriteLLM(content="慢查询", delay=0.05)
    rewriter = QueryRewriter(
        llm, Settings(query_rewrite_timeout_seconds=0.001)
    )
    result = await rewriter.rewrite("原始问题")
    assert result.rewritten is False
    assert result.fallback_reason == "timeout"
    assert result.query == "原始问题"


async def test_error_empty_multiline_and_too_long_fall_back() -> None:
    error = ScriptedRewriteLLM(error=RuntimeError("boom"))
    assert (
        await QueryRewriter(error, Settings()).rewrite("q")
    ).fallback_reason == "error"

    empty = ScriptedRewriteLLM(content="   ")
    assert (
        await QueryRewriter(empty, Settings()).rewrite("q")
    ).fallback_reason == "empty_output"

    multiline = ScriptedRewriteLLM(content="第一行\n第二行")
    assert (
        await QueryRewriter(multiline, Settings()).rewrite("q")
    ).fallback_reason == "multiline"

    too_long = ScriptedRewriteLLM(content="查" * (MAX_QUERY_CHARS + 1))
    assert (
        await QueryRewriter(too_long, Settings()).rewrite("q")
    ).fallback_reason == "too_long"


async def test_tool_uses_rewritten_query_and_records_trace(
    monkeypatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "query_rewrite_enabled", True, raising=False)
    llm = ScriptedRewriteLLM(content="保险 水浸损失")
    retriever = RecordingRetriever()
    tool = SearchKnowledgeTool(
        retriever,  # type: ignore[arg-type]
        query_rewriter=QueryRewriter(llm, settings),
    )
    result = await tool.run(
        {"query": "水管爆了保险赔吗？"}, ToolContext("user_1")
    )
    assert retriever.calls[0]["query"] == "保险 水浸损失"
    assert result.metadata["query_original"] == "水管爆了保险赔吗？"
    assert result.metadata["query_rewritten"] == "保险 水浸损失"
    assert result.metadata["rewrite_fallback"] is False
    assert result.metadata["rewrite_fallback_reason"] is None
    assert "rewrite_duration_ms" in result.metadata


async def test_tool_falls_back_to_original_query(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "query_rewrite_enabled", True, raising=False)
    llm = ScriptedRewriteLLM(error=RuntimeError("boom"))
    retriever = RecordingRetriever()
    tool = SearchKnowledgeTool(
        retriever,  # type: ignore[arg-type]
        query_rewriter=QueryRewriter(llm, settings),
    )
    result = await tool.run({"query": "原始问题"}, ToolContext("user_1"))
    assert retriever.calls[0]["query"] == "原始问题"
    assert result.metadata["rewrite_fallback"] is True
    assert result.metadata["rewrite_fallback_reason"] == "error"
    assert result.metadata["query_rewritten"] is None


async def test_tool_disabled_behaves_like_baseline(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "query_rewrite_enabled", False, raising=False)
    llm = ScriptedRewriteLLM(content="不应被使用")
    retriever = RecordingRetriever()
    tool = SearchKnowledgeTool(
        retriever,  # type: ignore[arg-type]
        query_rewriter=QueryRewriter(llm, settings),
    )
    result = await tool.run({"query": "原始问题"}, ToolContext("user_1"))
    assert retriever.calls[0]["query"] == "原始问题"
    assert result.metadata == {}
    assert llm.calls == []


async def test_agent_step_carries_rewrite_trace(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "query_rewrite_enabled", True, raising=False)

    class AgentLLM(LLMClient):
        def __init__(self) -> None:
            self.script = [
                LLMResponse(
                    content=None,
                    tool_calls=[
                        ToolCallRequest(
                            id="call_1",
                            name="search_knowledge",
                            arguments={"query": "水管爆了保险赔吗？"},
                        )
                    ],
                ),
                LLMResponse(content="根据保单，属于保险责任。"),
            ]

        async def chat(
            self,
            messages: list[ChatMessage],
            tools: list | None = None,
            max_tokens: int | None = None,
        ) -> LLMResponse:
            return self.script.pop(0)

    retriever = RecordingRetriever()
    registry = ToolRegistry()
    registry.register(
        SearchKnowledgeTool(
            retriever,  # type: ignore[arg-type]
            query_rewriter=QueryRewriter(
                ScriptedRewriteLLM(content="保险 水浸损失"), settings
            ),
        )
    )
    agent = Agent(AgentLLM(), registry)
    state = await agent.run(
        user_id="user_1", conversation_id="conv_1", query="水管爆了保险赔吗？",
        history=[],
    )
    step = state.steps[0]
    assert step["query_rewritten"] == "保险 水浸损失"
    assert step["rewrite_fallback"] is False
    assert step["rewrite_model"]

