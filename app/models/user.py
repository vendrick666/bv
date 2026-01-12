"""
Модель User (Занятие 4)
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship

from app.db.database import Base


class UserRole(str, PyEnum):
    """Роли пользователей (Занятие 9)"""

    USER = "user"
    SELLER = "seller"
    SUPPORT = "support"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)

    role = Column(Enum(UserRole), default=UserRole.USER)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    items = relationship("Item", back_populates="owner")
    cart_items = relationship("CartItem", back_populates="user")
    orders = relationship("Order", back_populates="user")
