import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class UserBase(BaseModel):
    username: str
    email: str
    role: str = "developer"  # 'admin' | 'developer' | 'viewer'
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
