"""Single-query LLM rewrite for retrieval (V2.1, ADR-0009).

The rewriter turns the user's/Agent's raw retrieval query into ONE
retrieval-optimised query and always fails open: on timeout, provider error,
empty output, multi-line output or over-length output it returns the original
query together with a fallback reason, so retrieval never breaks because of a
rewrite failure.
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import Settings, get_settings
from app.domain.models.llm import ChatMessage
from app.infrastructure.llm.base import LLMClient

UNIQUE_ID_PATTERN = re.compile(r"[A-Z]{2,5}-\d{4}-\d{3,4}", re.IGNORECASE)
MAX_QUERY_CHARS = 120

SYSTEM_PROMPT = (
    "你是检索查询改写器。把用户问题改写为一条更适合向量检索的中文查询："
    "1. 口语改书面，使用文档常用的业务词；"
    "2. 扩展同义词与相关术语，但不要改变意图；"
    "3. 相对日期（去年、上个月、今天等）按给定当前日期解析为具体年份或日期；"
    "4. 专有名词、编号、型号、金额原样保留；"
    "5. 多意图问题合并为一条查询，覆盖全部关键面；"
    "6. 只输出一行改写后的查询，不要解释、不要引号、不超过120个字符。"
)


@dataclass(frozen=True)
class RewriteResult:
    query: str
    rewritten: bool
    fallback_reason: str | None
    duration_ms: float
    model: str


class QueryRewriter:
    def __init__(
        self,
        llm_client: LLMClient,
        settings: Settings | None = None,
    ) -> None:
        self._llm = llm_client
        self._settings = settings or get_settings()

    def _model_name(self) -> str:
        settings = self._settings
        if settings.llm_provider in {"dashscope", "qwen"}:
            return settings.qwen_model or "unknown"
        return settings.deepseek_model or "unknown"

    async def rewrite(self, query: str) -> RewriteResult:
        started = time.perf_counter()

        def finish(  # noqa: ANN202
            result_query: str,
            rewritten: bool,
            reason: str | None,
        ) -> RewriteResult:
            return RewriteResult(
                query=result_query,
                rewritten=rewritten,
                fallback_reason=reason,
                duration_ms=round(
                    (time.perf_counter() - started) * 1000, 2
                ),
                model=self._model_name(),
            )

        stripped = query.strip()
        if not stripped:
            return finish(query, False, "empty_query")
        if UNIQUE_ID_PATTERN.search(stripped):
            return finish(query, False, "unique_id")

        now = datetime.now(
            ZoneInfo(self._settings.app_timezone)
        ).isoformat()
        messages = [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(
                role="user",
                content=f"当前日期时间：{now}\n用户问题：{stripped}",
            ),
        ]
        try:
            response = await asyncio.wait_for(
                self._llm.chat(
                    messages,
                    tools=[],
                    max_tokens=self._settings.query_rewrite_max_tokens,
                ),
                timeout=self._settings.query_rewrite_timeout_seconds,
            )
        except asyncio.TimeoutError:
            return finish(query, False, "timeout")
        except Exception:
            return finish(query, False, "error")

        candidate = (response.content or "").strip()
        candidate = candidate.strip("` \t\n\r\"'“”")
        if not candidate:
            return finish(query, False, "empty_output")
        if "\n" in candidate or "\r" in candidate:
            return finish(query, False, "multiline")
        if len(candidate) > MAX_QUERY_CHARS:
            return finish(query, False, "too_long")
        return finish(candidate, True, None)
