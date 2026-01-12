"""
API для товаров (парфюмов) (Занятия 10-14)
"""

from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_session
from app.core.deps import get_current_seller_user
from app.models.user import User
from app.models.item import Item
from app.schemas.item import ItemCreate, ItemUpdate, ItemResponse, PaginatedItems

router = APIRouter(prefix="/items", tags=["Items"])


@router.get("", response_model=PaginatedItems)
async def get_items(
    # Пагинация (Занятие 14)
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    # Фильтры (Занятие 13)
    category_id: Optional[int] = None,
    min_price: Optional[Decimal] = None,
    max_price: Optional[Decimal] = None,
    search: Optional[str] = None,
    in_stock: Optional[bool] = None,
    # Сортировка (Занятие 14)
    sort_by: str = Query("created_at", pattern="^(name|price|created_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Получение списка товаров с фильтрацией и пагинацией (Занятия 13-14)

    Защита от SQL-инъекций через параметризованные запросы SQLAlchemy
    """
    query = select(Item).where(Item.is_active.is_(True))
    count_query = select(func.count(Item.id)).where(Item.is_active.is_(True))

    # Фильтры
    if category_id:
        query = query.where(Item.category_id == category_id)
        count_query = count_query.where(Item.category_id == category_id)

    if min_price is not None:
        query = query.where(Item.price >= min_price)
        count_query = count_query.where(Item.price >= min_price)

    if max_price is not None:
        query = query.where(Item.price <= max_price)
        count_query = count_query.where(Item.price <= max_price)

    if search:
        # Full-text search (Занятие 13)
        search_filter = or_(
            Item.name.ilike(f"%{search}%"),
            Item.description.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    if in_stock:
        query = query.where(Item.stock_quantity > 0)
        count_query = count_query.where(Item.stock_quantity > 0)

    # Общее количество
    total = (await session.execute(count_query)).scalar()

    # Сортировка
    sort_column = getattr(Item, sort_by)
    query = query.order_by(
        sort_column.desc() if sort_order == "desc" else sort_column.asc()
    )

    # Пагинация
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await session.execute(query)
    items = result.scalars().all()

    return PaginatedItems(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size if total > 0 else 0,
    )


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """Получение товара по ID (Занятие 10)"""
    result = await session.execute(
        select(Item).where(Item.id == item_id, Item.is_active.is_(True))
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Товар не найден")

    return item


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    item_data: ItemCreate,
    current_user: User = Depends(get_current_seller_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Создание товара (Занятие 10) - только seller/admin"""
    item = Item(
        **item_data.model_dump(),
        owner_id=current_user.id,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)

    return item


@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: int,
    item_data: ItemUpdate,
    current_user: User = Depends(get_current_seller_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Обновление товара (Занятие 11) - только owner или admin"""
    result = await session.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Товар не найден")

    # Проверка прав (Занятие 11)
    if item.owner_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Нет прав на редактирование")

    for field, value in item_data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    await session.commit()
    await session.refresh(item)

    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: int,
    current_user: User = Depends(get_current_seller_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Удаление товара (Занятие 11) - soft delete"""
    result = await session.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Товар не найден")

    if item.owner_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Нет прав на удаление")

    item.is_active = False
    await session.commit()
