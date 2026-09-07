"""Chat endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_current_user,
    get_llm_client,
    get_retriever,
)
from app.domain.entities.user import User
from app.infrastructure.database.agent_run_repository import (
    SQLAlchemyAgentRunRepository,
)
from app.infrastructure.database.conversation_repository import (
    SQLAlchemyConversationRepository,
)
from app.infrastructure.database.session import get_db
from app.infrastructure.llm.base import LLMClient
from app.rag.retrieval.retriever import Retriever
from app.schemas.chat import ChatMetadataOut, ChatRequest, ChatResponse, SourceOut
from app.services.agent_service import AgentService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    llm_client: LLMClient = Depends(get_llm_client),
    retriever: Retriever = Depends(get_retriever),
) -> ChatResponse:
    service = AgentService(
        conversation_repository=SQLAlchemyConversationRepository(db),
        agent_run_repository=SQLAlchemyAgentRunRepository(db),
        llm_client=llm_client,
        retriever=retriever,
    )
    result = await service.ask(
        payload.conversation_id, current_user, payload.query
    )
    return ChatResponse(
        answer=result.answer,
        sources=[
            SourceOut(
                document_id=source["document_id"],
                document_name=source["document_name"],
                relevance=source["relevance"],
            )
            for source in result.sources
        ],
        metadata=ChatMetadataOut(
            retrieval_count=result.retrieval_count,
            duration_ms=result.duration_ms,
        ),
    )
