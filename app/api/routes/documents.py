"""Document upload and management endpoints."""

import logging
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_current_user,
    get_ingestion_dispatcher,
)
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.domain.entities.document import Document
from app.domain.entities.user import User
from app.infrastructure.database.document_repository import (
    SQLAlchemyDocumentRepository,
)
from app.infrastructure.database.session import get_db
from app.schemas.document import DocumentOut, DocumentType
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger("app.documents")


def _service(session: AsyncSession) -> DocumentService:
    return DocumentService(SQLAlchemyDocumentRepository(session))


def _to_out(document: Document) -> DocumentOut:
    return DocumentOut(
        document_id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        document_type=document.document_type,
        file_size=document.file_size,
        status=document.status,
        processing_stage=document.processing_stage,
        error_message=document.error_message,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


IngestionDispatcher = Callable[[str], Awaitable[None]]


async def _read_upload(upload: UploadFile) -> bytes:
    max_bytes = get_settings().max_file_size_mb * 1024 * 1024
    chunks: list[bytes] = []
    total = 0
    while chunk := await upload.read(1024 * 1024):
        total += len(chunk)
        if total > max_bytes:
            raise AppError(413, "FILE_TOO_LARGE", "File exceeds the size limit")
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    document_type: DocumentType = Form(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    dispatcher: IngestionDispatcher = Depends(get_ingestion_dispatcher),
) -> DocumentOut:
    content = await _read_upload(file)
    document = await _service(db).upload(
        user_id=current_user.id,
        filename=file.filename or "untitled",
        document_type=document_type,
        content=content,
    )
    try:
        await dispatcher(document.id)
    except Exception as exc:
        logger.exception(
            "ingestion enqueue failed; rolling back upload",
            extra={"document_id": document.id, "error": type(exc).__name__},
        )
        try:
            await _service(db).delete_document(document.id, current_user.id)
        except Exception as cleanup_exc:
            logger.exception(
                "upload rollback cleanup failed",
                extra={
                    "document_id": document.id,
                    "error": type(cleanup_exc).__name__,
                },
            )
        raise AppError(
            503,
            "SERVICE_UNAVAILABLE",
            "Document processing queue is unavailable, please try again",
        ) from exc
    return _to_out(document)


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentOut]:
    documents = await _service(db).list_documents(
        current_user.id, page, page_size
    )
    return [_to_out(d) for d in documents]


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    document = await _service(db).get_document(document_id, current_user.id)
    return _to_out(document)


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await _service(db).delete_document(document_id, current_user.id)
    return Response(status_code=204)


@router.post(
    "/{document_id}/retry", response_model=DocumentOut, status_code=202
)
async def retry_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    dispatcher: IngestionDispatcher = Depends(get_ingestion_dispatcher),
) -> DocumentOut:
    document = await _service(db).retry(document_id, current_user.id)
    await dispatcher(document.id)
    return _to_out(document)
