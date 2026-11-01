import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class UserBase(BaseModel):
    username: str
    email: str
    role: str = "developer"  # 'admin' | 'developer' | 'viewer'
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: uuid.UUID
    totp_enabled: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("totp_enabled", mode="before")
    @classmethod
    def _coerce_totp_enabled(cls, v):
        return bool(v)


class LoginRequest(BaseModel):
    username: str
    password: str
    otp_code: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
