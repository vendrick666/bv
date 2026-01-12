"""
Pydantic схемы для системы поддержки
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.models.support import TicketStatus


class SupportMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class SupportMessageResponse(BaseModel):
    id: int
    content: str
    is_staff: bool
    user_id: int
    user_name: Optional[str] = None
    user_role: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TicketCreate(BaseModel):
    subject: str = Field(..., min_length=3, max_length=200)
    message: str = Field(..., min_length=1, max_length=2000)


class TicketResponse(BaseModel):
    id: int
    subject: str
    status: TicketStatus
    user_id: int
    user_name: Optional[str] = None
    assigned_to: Optional[int] = None
    assignee_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TicketWithMessages(TicketResponse):
    messages: List[SupportMessageResponse] = []


class TicketStatusUpdate(BaseModel):
    status: TicketStatus


class TicketAssign(BaseModel):
    assigned_to: int
