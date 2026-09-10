"""Query expansion for multi-query retrieval (V2.2, ADR-0010).

Generates one or more query variants that SUPPLEMENT the original query (they
never replace it). Two V2.1 defects are fixed here:

- relative dates are resolved only when the query actually contains an explicit
  relative-date expression; otherwise the prompt forbids introducing any date;
- entities, identifiers, numbers and discriminative nouns must be preserved;
  a variant that drops a protected token is discarded.

Generation is deterministic (temperature 0) and fails open: on timeout, error or
inval id output it returns zero variants and retrieval continues with the
original query only.
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

ID_PATTERN = re.compile(r"[A-Z]{2,5}-\d{4}-\d{3,4}", re.IGNORECASE)
VALUE_PATTERN = re.compile(r"\d+(?:\.\d+)?%?")
RELATIVE_DATE_TOKENS = (
    "去年",
    "今年",
    "明年",
    "上个月",
    "这个月",
    "下个月",
    "上星期",
    "上周",
    "这周",
    "下周",
    "今天",
    "明天",
    "昨天",
    "前天",
    "后天",
    "年初",
    "年底",
    "上季度",
    "本季度",
    "下季度",
)
MAX_VARIANT_CHARS = 120

SYSTEM_PROMPT = (
    "你是检索查询变体生成器。基于用户问题生成若干条补充检索查询，"
    "用于向量检索的多路召回。规则："
    "1. 变体只是原问题的不同表达，不得改变意图；"
    "2. 保留原问题中的专有名词、编号、型号、金额和其他数字，原样出现；"
    "3. 只有用户问题中明确出现相对日期表达（去年/上个月/今天等）时，"
    "才可结合给定的当前日期把它解析为具体日期；若未给出当前日期，"
    "绝对不要引入任何日期；"
    "4. 不要编造原问题没有的条件；"
    "5. 每行一条查询，不要编号、不要解释、不要引号，每条不超过120个字符。"
)


@dataclass(frozen=True)
class ExpansionResult:
    variants: list[str]
    fallback_reason: str | None
    duration_ms: float
    model: str
    requested: int


class QueryExpander:
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

    async def generate(self, query: str) -> ExpansionResult:
        started = time.perf_counter()
        requested = max(1, self._settings.query_expansion_variants)

        def finish(
            variants: list[str], reason: str | None
        ) -> ExpansionResult:
            return ExpansionResult(
                variants=variants,
                fallback_reason=reason,
                duration_ms=round(
                    (time.perf_counter() - started) * 1000, 2
                ),
                model=self._model_name(),
                requested=requested,
            )

        stripped = query.strip()
        if not stripped:
            return finish([], "empty_query")
        if ID_PATTERN.search(stripped):
            return finish([], "unique_id")

        has_relative_date = any(
            token in stripped for token in RELATIVE_DATE_TOKENS
        )
        current = (
            datetime.now(
                ZoneInfo(self._settings.app_timezone)
            ).isoformat()
            if has_relative_date
            else None
        )
        user_content = f"用户问题：{stripped}\n请生成 {requested} 条补充查询。"
        if current is not None:
            user_content = (
                f"当前日期时间：{current}\n" + user_content
            )
        messages = [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(role="user", content=user_content),
        ]
        try:
            response = await asyncio.wait_for(
                self._llm.chat(
                    messages,
                    tools=[],
                    max_tokens=self._settings.query_expansion_max_tokens,
                    temperature=0.0,
                ),
                timeout=self._settings.query_expansion_timeout_seconds,
            )
        except asyncio.TimeoutError:
            return finish([], "timeout")
        except Exception:
            return finish([], "error")

        protected = set(ID_PATTERN.findall(stripped)) | set(
            VALUE_PATTERN.findall(stripped)
        )
        variants: list[str] = []
        dropped_for_entity = False
        seen = {stripped}
        for raw_line in (response.content or "").splitlines():
            line = raw_line.strip().lstrip("-*0123456789. ").strip("`\"'“”")
            if not line or line in seen:
                continue
            if len(line) > MAX_VARIANT_CHARS:
                continue
            if protected and any(
                token not in line for token in protected
            ):
                dropped_for_entity = True
                continue
            variants.append(line)
            seen.add(line)
            if len(variants) >= requested:
                break

        if not variants:
            return finish(
                [], "entity_lost" if dropped_for_entity else "empty_output"
            )
        return finish(variants, None)
