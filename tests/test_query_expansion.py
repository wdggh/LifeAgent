"""V2.2 query expansion + equal-weight RRF tests (ADR-0010)."""

import asyncio

from app.agent.tools.base import ToolContext
from app.agent.tools.search_knowledge import SearchKnowledgeTool
from app.core.config import Settings, get_settings
from app.domain.models.llm import ChatMessage, LLMResponse
from app.domain.models.search_result import SearchResult
from app.infrastructure.llm.base import LLMClient
from app.rag.query.expansion import QueryExpander
from app.rag.retrieval.fusion import reciprocal_rank_fusion


class ScriptedExpansionLLM(LLMClient):
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
        temperature: float | None = None,
    ) -> LLMResponse:
        self.calls.append(
            {
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error is not None:
            raise self.error
        return LLMResponse(content=self.content)


class RecordingRetriever:
    def __init__(
        self, results: dict[str, list[SearchResult]]
    ) -> None:
        self.results = results
        self.calls: list[dict] = []

    async def search(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        document_type: str | None = None,
        document_id: str | None = None,
    ) -> list[SearchResult]:
        self.calls.append({"query": query, "top_k": top_k})
        return self.results.get(query, [])[:top_k]


def hit(chunk_id: str, score: float = 0.9) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id,
        document_id="doc_1",
        document_name="doc.pdf",
        content="content",
        score=score,
    )


def expansion_settings(**overrides) -> Settings:
    base = {
        "query_expansion_enabled": True,
        "query_expansion_variants": 1,
        "query_expansion_candidate_k": 8,
        "query_expansion_rrf_k": 60,
        "query_expansion_original_weight": 1.0,
        "query_expansion_timeout_seconds": 1.0,
    }
    base.update(overrides)
    return Settings(**base)


async def test_expansion_never_injects_date_without_relative_token() -> None:
    llm = ScriptedExpansionLLM(content="违约金 一个月租金")
    expander = QueryExpander(llm, expansion_settings())
    result = await expander.generate("提前退租违约金是多少？")
    assert result.variants == ["违约金 一个月租金"]
    assert result.fallback_reason is None
    user_content = llm.calls[0]["messages"][1].content
    assert "当前日期时间" not in user_content
    assert llm.calls[0]["temperature"] == 0.0
    assert llm.calls[0]["max_tokens"] == 200


async def test_expansion_resolves_explicit_relative_date() -> None:
    llm = ScriptedExpansionLLM(content="2025年购买的自行车 保修期限")
    expander = QueryExpander(llm, expansion_settings())
    result = await expander.generate("我去年买的自行车保修多久？")
    assert result.variants
    assert "当前日期时间" in llm.calls[0]["messages"][1].content


async def test_expansion_discards_variant_that_loses_protected_tokens() -> None:
    llm = ScriptedExpansionLLM(content="违约金计算方式")
    expander = QueryExpander(llm, expansion_settings())
    result = await expander.generate("合同第4条 违约金 4500元 怎么算？")
    assert result.variants == []
    assert result.fallback_reason == "entity_lost"


async def test_expansion_fails_open_on_error_empty_and_timeout() -> None:
    error = ScriptedExpansionLLM(error=RuntimeError("boom"))
    result = await QueryExpander(error, expansion_settings()).generate("q")
    assert result.variants == [] and result.fallback_reason == "error"

    empty = ScriptedExpansionLLM(content="   ")
    result = await QueryExpander(empty, expansion_settings()).generate("q")
    assert result.variants == [] and result.fallback_reason == "empty_output"

    slow = ScriptedExpansionLLM(content="x", delay=0.05)
    result = await QueryExpander(
        slow, expansion_settings(query_expansion_timeout_seconds=0.001)
    ).generate("q")
    assert result.variants == [] and result.fallback_reason == "timeout"


def test_rrf_equal_scores_break_towards_original_branch() -> None:
    outcome = reciprocal_rank_fusion(
        [[hit("correct")], [hit("wrong")]], k=60, limit=None
    )
    ids = [result.chunk_id for result in outcome.results]
    assert ids == ["correct", "wrong"]
    assert outcome.scores["correct"] == outcome.scores["wrong"]


def test_rrf_dedupes_and_sums_scores_across_branches() -> None:
    outcome = reciprocal_rank_fusion(
        [[hit("a"), hit("b")], [hit("a"), hit("c")]],
        k=60,
        limit=3,
    )
    ids = [result.chunk_id for result in outcome.results]
    assert ids == ["a", "b", "c"]
    assert outcome.scores["a"] > outcome.scores["b"]
    assert outcome.candidate_count == 3


async def test_tool_runs_two_branches_and_fuses(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "query_expansion_enabled", True)
    monkeypatch.setattr(settings, "query_expansion_variants", 1)
    monkeypatch.setattr(settings, "query_expansion_candidate_k", 8)
    monkeypatch.setattr(settings, "query_expansion_rrf_k", 60)
    monkeypatch.setattr(settings, "query_expansion_original_weight", 1.0)
    llm = ScriptedExpansionLLM(content="保险 水浸损失")
    retriever = RecordingRetriever(
        {
            "水管爆了保险赔吗？": [hit("original_hit")],
            "保险 水浸损失": [hit("variant_hit")],
        }
    )
    tool = SearchKnowledgeTool(
        retriever,  # type: ignore[arg-type]
        query_expander=QueryExpander(llm, settings),
    )
    result = await tool.run(
        {"query": "水管爆了保险赔吗？"},
        ToolContext("user_1", remaining_chunk_budget=10),
    )
    assert [call["query"] for call in retriever.calls] == [
        "水管爆了保险赔吗？",
        "保险 水浸损失",
    ]
    assert retriever.calls[0]["top_k"] == 8
    assert [r.chunk_id for r in result.results] == [
        "original_hit",
        "variant_hit",
    ]
    metadata = result.metadata
    assert metadata["query_variants"] == ["保险 水浸损失"]
    assert metadata["per_variant_hits"] == [1, 1]
    assert metadata["fusion_candidates"] == 2
    assert metadata["rrf_k"] == 60
    assert metadata["original_weight"] == 1.0
    assert metadata["expansion_fallback"] is False


async def test_tool_expansion_failure_falls_back_to_original_only(
    monkeypatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "query_expansion_enabled", True)
    llm = ScriptedExpansionLLM(error=RuntimeError("boom"))
    retriever = RecordingRetriever({"原始问题": [hit("only")]})
    tool = SearchKnowledgeTool(
        retriever,  # type: ignore[arg-type]
        query_expander=QueryExpander(llm, settings),
    )
    result = await tool.run(
        {"query": "原始问题"}, ToolContext("user_1", remaining_chunk_budget=10)
    )
    assert [call["query"] for call in retriever.calls] == ["原始问题"]
    assert result.metadata["expansion_fallback"] is True
    assert result.metadata["expansion_fallback_reason"] == "error"
    assert result.metadata["query_variants"] == []


async def test_tool_disabled_equals_baseline(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "query_expansion_enabled", False)
    llm = ScriptedExpansionLLM(content="不应使用")
    retriever = RecordingRetriever({"原始问题": [hit("only")]})
    tool = SearchKnowledgeTool(
        retriever,  # type: ignore[arg-type]
        query_expander=QueryExpander(llm, settings),
    )
    result = await tool.run(
        {"query": "原始问题"}, ToolContext("user_1", remaining_chunk_budget=10)
    )
    assert [call["query"] for call in retriever.calls] == ["原始问题"]
    assert result.metadata == {}
    assert llm.calls == []


async def test_tool_truncates_fused_results_to_budget(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "query_expansion_enabled", True)
    monkeypatch.setattr(settings, "query_expansion_candidate_k", 8)
    llm = ScriptedExpansionLLM(content="变体查询")
    retriever = RecordingRetriever(
        {
            "原始问题": [hit("a"), hit("b"), hit("c")],
            "变体查询": [hit("c"), hit("d"), hit("e")],
        }
    )
    tool = SearchKnowledgeTool(
        retriever,  # type: ignore[arg-type]
        query_expander=QueryExpander(llm, settings),
    )
    result = await tool.run(
        {"query": "原始问题"}, ToolContext("user_1", remaining_chunk_budget=4)
    )
    ids = [r.chunk_id for r in result.results]
    assert len(ids) == 4
    # "c" is returned by both branches and therefore has the highest RRF score
    assert ids[0] == "c"
    assert len(set(ids)) == len(ids)
