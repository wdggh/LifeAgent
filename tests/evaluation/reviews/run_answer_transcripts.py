"""Run the 12 answer-level cases through the real Agent (V2.0.1-07).

Assumes the active dataset corpus is already ingested into the isolated
``_eval`` collection (V2.0.1-06 triage does this). Uses the configured LLM
provider (``LLM_PROVIDER=dashscope`` + ``DASHSCOPE_API_KEY`` for qwen-max) and
the real AgentService, then writes raw transcripts for manual 0/1 review.

Run from the repository root:
    python -m tests.evaluation.reviews.run_answer_transcripts
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from app.api.dependencies import get_llm_client
from app.core.config import get_settings
from app.infrastructure.database.agent_run_repository import (
    SQLAlchemyAgentRunRepository,
)
from app.infrastructure.database.conversation_repository import (
    SQLAlchemyConversationRepository,
)
from app.infrastructure.database.document_repository import (
    SQLAlchemyDocumentRepository,
)
from app.infrastructure.database.session import get_session_maker
from app.infrastructure.embedding.factory import get_embedding_client
from app.rag.retrieval.retriever import Retriever
from app.services.agent_service import AgentService

from tests.evaluation.datasets import paths
from tests.evaluation.reviews.answer_review import load_answer_cases
from tests.evaluation.runners.ingest_corpus import live_harness

REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"


async def run(dataset: str, output: Path, limit: int | None) -> int:
    settings = get_settings()
    if settings.llm_provider not in {"dashscope", "qwen"} and not (
        settings.deepseek_api_key
    ):
        raise RuntimeError(
            "configure LLM_PROVIDER=dashscope (or a DeepSeek key) first"
        )
    cases = load_answer_cases(dataset)
    if limit:
        cases = cases[:limit]

    transcripts = []
    async with live_harness(reset=False) as harness:
        user = await harness.ensure_eval_user()
        async with get_session_maker()() as session:
            conversations = SQLAlchemyConversationRepository(session)
            service = AgentService(
                conversation_repository=conversations,
                agent_run_repository=SQLAlchemyAgentRunRepository(session),
                document_repository=SQLAlchemyDocumentRepository(session),
                llm_client=await get_llm_client(),
                retriever=Retriever(
                    get_embedding_client(), harness.vectors
                ),
            )
            for case in cases:
                conversation = await conversations.create(
                    user.id, f"answer-review {case['id']}"
                )
                result = await service.ask(
                    conversation.id, user, case["question"]
                )
                transcripts.append(
                    {
                        "id": case["id"],
                        "question": case["question"],
                        "category": case["category"],
                        "answer_requirements": case["answer_requirements"],
                        "expected_sources": case.get("expected_sources", []),
                        "not_in_kb": case["category"] == "not_in_kb",
                        "answer": result.answer,
                        "sources": result.sources,
                        "retrieval_count": result.retrieval_count,
                        "duration_ms": result.duration_ms,
                    }
                )
                print(f"answered {case['id']} ({result.duration_ms} ms)")

    payload = {
        "dataset": dataset,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.qwen_model
        if settings.llm_provider in {"dashscope", "qwen"}
        else settings.deepseek_model,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "transcripts": transcripts,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"transcripts written: {output}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=paths.active_dataset_name())
    parser.add_argument(
        "--output",
        default=str(REPORTS_DIR / "answer-transcripts-v2.raw.json"),
    )
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    return asyncio.run(run(args.dataset, Path(args.output), args.limit))


if __name__ == "__main__":
    raise SystemExit(main())
