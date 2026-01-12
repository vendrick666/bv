"""
Pydantic схемы для корзины и заказов (Занятия 15-17)
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field

from app.models.order import OrderStatus
from app.schemas.item import ItemResponse


class CartItemCreate(BaseModel):
    item_id: int
    quantity: int = Field(default=1, ge=1)


class CartItemUpdate(BaseModel):
    quantity: int = Field(..., ge=1)


class CartItemResponse(BaseModel):
    id: int
    item_id: int
    quantity: int
    item: ItemResponse
    added_at: datetime

    model_config = {"from_attributes": True}


class CartResponse(BaseModel):
    items: List[CartItemResponse]
    total_items: int
    total_price: Decimal


class OrderCreate(BaseModel):
    shipping_address: str = Field(..., min_length=5)
    notes: Optional[str] = None


class OrderItemResponse(BaseModel):
    id: int
    item_id: int
    quantity: int
    price_at_purchase: Decimal
    item: ItemResponse

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    id: int
    order_number: str
    status: OrderStatus
    total_price: Decimal
    shipping_address: Optional[str] = None
    notes: Optional[str] = None
    user_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderWithItems(OrderResponse):
    items: List[OrderItemResponse]


class OrderStatusUpdate(BaseModel):
    """Обновление статуса (Занятие 17)"""

    status: OrderStatus
