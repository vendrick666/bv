"""
Pydantic схемы для User (Занятие 7)
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole


class UserCreate(BaseModel):
    """Регистрация"""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        errors = []
        if len(v) < 8:
            errors.append("Минимум 8 символов")
        if not any(c.isupper() for c in v):
            errors.append("Нужна хотя бы одна заглавная буква")
        if not any(c.islower() for c in v):
            errors.append("Нужна хотя бы одна строчная буква")
        if not any(c.isdigit() for c in v):
            errors.append("Нужна хотя бы одна цифра")
        if errors:
            raise ValueError("; ".join(errors))
        return v


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Optional["UserResponse"] = None


class LoginRequest(BaseModel):
    """Вход - можно использовать email или username"""

    login: str  # email или username
    password: str
