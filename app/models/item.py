"""
Модели Item (парфюм) и Category (Занятия 10-12)
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Numeric,
    Boolean,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


class Category(Base):
    """Категория товаров (Занятие 12)"""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)

    items = relationship("Item", back_populates="category")


class Item(Base):
    """
    Товар - парфюм (Занятие 10)

    В контексте BV Parfume это парфюмерия
    """

    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)

    # Специфика парфюмерии
    brand = Column(String(100), nullable=True)
    volume_ml = Column(Integer, nullable=True)  # Объём в мл

    stock_quantity = Column(Integer, default=0)
    image_url = Column(String(500), nullable=True)

    is_active = Column(Boolean, default=True)

    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    category = relationship("Category", back_populates="items")
    owner = relationship("User", back_populates="items")
    cart_items = relationship("CartItem", back_populates="item")
    order_items = relationship("OrderItem", back_populates="item")
