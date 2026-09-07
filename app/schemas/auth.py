"""Auth request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UsernamePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_within_bcrypt_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("password must not exceed 72 bytes")
        return value


class RegisterRequest(UsernamePasswordRequest):
    pass


class LoginRequest(UsernamePasswordRequest):
    pass


class UserOut(BaseModel):
    user_id: str
    username: str
    created_at: datetime | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
