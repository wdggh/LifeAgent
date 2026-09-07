"""SQLAlchemy implementation of the document repository."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.document import Document
from app.infrastructure.database.models.document import DocumentModel
from app.repositories.document_repository import DocumentRepository


def _to_domain(model: DocumentModel) -> Document:
    return Document(
        id=model.id,
        user_id=model.user_id,
        filename=model.filename,
        file_type=model.file_type,
        file_path=model.file_path,
        file_size=model.file_size,
        document_type=model.document_type,
        status=model.status,
        processing_stage=model.processing_stage,
        error_message=model.error_message,
        embedding_model=model.embedding_model,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SQLAlchemyDocumentRepository(DocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, document_id: str) -> Document | None:
        model = await self._session.get(DocumentModel, document_id)
        return _to_domain(model) if model else None

    async def list_by_user(
        self, user_id: str, page: int, page_size: int
    ) -> list[Document]:
        result = await self._session.execute(
            select(DocumentModel)
            .where(DocumentModel.user_id == user_id)
            .order_by(DocumentModel.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return [_to_domain(row) for row in result.scalars().all()]

    async def get_by_id_and_user(
        self, document_id: str, user_id: str
    ) -> Document | None:
        result = await self._session.execute(
            select(DocumentModel).where(
                DocumentModel.id == document_id,
                DocumentModel.user_id == user_id,
            )
        )
        model = result.scalar_one_or_none()
        return _to_domain(model) if model else None

    async def create(self, document: Document) -> Document:
        model = DocumentModel(
            user_id=document.user_id,
            filename=document.filename,
            file_type=document.file_type,
            file_path=document.file_path,
            file_size=document.file_size,
            document_type=document.document_type,
            status=document.status,
            processing_stage=document.processing_stage,
            error_message=document.error_message,
            embedding_model=document.embedding_model,
        )
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return _to_domain(model)

    async def delete(self, document_id: str) -> None:
        model = await self._session.get(DocumentModel, document_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.commit()

    async def update_status(
        self,
        document_id: str,
        *,
        status: str,
        processing_stage: str | None = None,
        error_message: str | None = None,
        embedding_model: str | None = None,
    ) -> None:
        model = await self._session.get(DocumentModel, document_id)
        if model is None:
            return
        model.status = status
        model.processing_stage = processing_stage
        model.error_message = error_message
        model.embedding_model = embedding_model
        await self._session.commit()
