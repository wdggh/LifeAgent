"""Authentication endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import create_access_token
from app.domain.entities.user import User
from app.infrastructure.database.session import get_db
from app.infrastructure.database.user_repository import SQLAlchemyUserRepository
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.services.user_service import UserService
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_service(session: AsyncSession) -> UserService:
    return UserService(SQLAlchemyUserRepository(session))


@router.post("/register", response_model=UserOut, status_code=201)
async def register(
    payload: RegisterRequest, db: AsyncSession = Depends(get_db)
) -> UserOut:
    user = await _user_service(db).register(payload.username, payload.password)
    return UserOut(
        user_id=user.id, username=user.username, created_at=user.created_at
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    user = await _user_service(db).authenticate(
        payload.username, payload.password
    )
    settings = get_settings()
    token = create_access_token(
        user.id, settings.jwt_secret, settings.access_token_expire_minutes
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(
        user_id=current_user.id,
        username=current_user.username,
        created_at=current_user.created_at,
    )
