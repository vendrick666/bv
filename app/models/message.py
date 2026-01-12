"""
Модель сообщений для чата (Занятие 32)
"""

from datetime import datetime

from sqlalchemy import Column, Integer, Text, Boolean, DateTime, ForeignKey

from app.db.database import Base


class Message(Base):
    """Сообщение в чате между покупателем и продавцом"""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)

    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id"), nullable=True)

    is_read = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
