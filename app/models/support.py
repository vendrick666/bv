"""
Модели для системы поддержки
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Enum,
    Boolean,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


class TicketStatus(str, PyEnum):
    """Статусы тикетов"""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class SupportTicket(Base):
    """Тикет поддержки"""

    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String(200), nullable=False)
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="tickets")
    assignee = relationship("User", foreign_keys=[assigned_to])
    messages = relationship(
        "SupportMessage", back_populates="ticket", order_by="SupportMessage.created_at"
    )


class SupportMessage(Base):
    """Сообщение в тикете"""

    __tablename__ = "support_messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    is_staff = Column(Boolean, default=False)  # True если от саппорта/админа

    ticket_id = Column(Integer, ForeignKey("support_tickets.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ticket = relationship("SupportTicket", back_populates="messages")
    user = relationship("User")
