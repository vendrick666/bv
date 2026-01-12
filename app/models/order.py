"""
Модели корзины и заказов (Занятия 15-17)
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Numeric,
    DateTime,
    Enum,
    ForeignKey,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


class OrderStatus(str, PyEnum):
    """Статусы заказа (Занятие 16)"""

    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class CartItem(Base):
    """Товар в корзине (Занятие 15)"""

    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    quantity = Column(Integer, default=1)

    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    item_id = Column(
        Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False
    )

    added_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="cart_items")
    item = relationship("Item", back_populates="cart_items")


class Order(Base):
    """Заказ (Занятие 16)"""

    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, nullable=False)

    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    total_price = Column(Numeric(10, 2), nullable=False)

    shipping_address = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    """Товар в заказе (Занятие 16)"""

    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    quantity = Column(Integer, nullable=False)
    price_at_purchase = Column(Numeric(10, 2), nullable=False)

    order_id = Column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    item_id = Column(Integer, ForeignKey("items.id"), nullable=False)

    order = relationship("Order", back_populates="items")
    item = relationship("Item", back_populates="order_items")
