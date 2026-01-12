"""
Pydantic схемы для Item и Category (Занятия 10-14)
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class ItemCreate(BaseModel):
    """Создание товара (Занятие 10)"""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    price: Decimal = Field(..., gt=0)
    brand: Optional[str] = None
    volume_ml: Optional[int] = Field(None, gt=0)
    stock_quantity: int = Field(default=0, ge=0)
    category_id: Optional[int] = None
    image_url: Optional[str] = Field(None, max_length=500)


class ItemUpdate(BaseModel):
    """Обновление товара (Занятие 11)"""

    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0)
    brand: Optional[str] = None
    volume_ml: Optional[int] = Field(None, gt=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    category_id: Optional[int] = None
    is_active: Optional[bool] = None
    image_url: Optional[str] = Field(None, max_length=500)


class ItemResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: Decimal
    brand: Optional[str] = None
    volume_ml: Optional[int] = None
    stock_quantity: int
    image_url: Optional[str] = None
    is_active: bool
    category_id: Optional[int] = None
    owner_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ItemFilter(BaseModel):
    """Фильтры для поиска (Занятие 13)"""

    category_id: Optional[int] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    search: Optional[str] = None
    in_stock: Optional[bool] = None


class PaginatedItems(BaseModel):
    """Пагинация (Занятие 14)"""

    items: List[ItemResponse]
    total: int
    page: int
    page_size: int
    pages: int
