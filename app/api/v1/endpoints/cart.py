"""
API для корзины (Занятие 15)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.database import get_async_session
from app.core.deps import get_current_user
from app.models.user import User
from app.models.item import Item
from app.models.order import CartItem
from app.schemas.order import (
    CartItemCreate,
    CartItemUpdate,
    CartItemResponse,
    CartResponse,
)

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("", response_model=CartResponse)
async def get_cart(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Просмотр корзины"""
    result = await session.execute(
        select(CartItem)
        .where(CartItem.user_id == current_user.id)
        .options(joinedload(CartItem.item))
    )
    cart_items = result.scalars().unique().all()

    total_items = sum(ci.quantity for ci in cart_items)
    total_price = sum(ci.item.price * ci.quantity for ci in cart_items)

    return CartResponse(
        items=cart_items,
        total_items=total_items,
        total_price=total_price,
    )


@router.post("", response_model=CartItemResponse, status_code=status.HTTP_201_CREATED)
async def add_to_cart(
    data: CartItemCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Добавить в корзину"""
    # Проверка товара
    item_result = await session.execute(
        select(Item).where(Item.id == data.item_id, Item.is_active.is_(True))
    )
    item = item_result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Товар не найден")

    # Проверка наличия
    if item.stock_quantity < data.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Недостаточно товара. В наличии: {item.stock_quantity}",
        )

    # Проверка, есть ли уже в корзине
    existing = await session.execute(
        select(CartItem).where(
            CartItem.user_id == current_user.id,
            CartItem.item_id == data.item_id,
        )
    )
    cart_item = existing.scalar_one_or_none()

    if cart_item:
        cart_item.quantity += data.quantity
    else:
        cart_item = CartItem(
            user_id=current_user.id,
            item_id=data.item_id,
            quantity=data.quantity,
        )
        session.add(cart_item)

    await session.commit()

    # Загружаем с item
    result = await session.execute(
        select(CartItem)
        .where(CartItem.id == cart_item.id)
        .options(joinedload(CartItem.item))
    )
    return result.scalar_one()


@router.put("/{cart_item_id}", response_model=CartItemResponse)
async def update_cart_item(
    cart_item_id: int,
    data: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Изменить количество"""
    result = await session.execute(
        select(CartItem)
        .where(CartItem.user_id == current_user.id, CartItem.id == cart_item_id)
        .options(joinedload(CartItem.item))
    )
    cart_item = result.scalar_one_or_none()

    if not cart_item:
        raise HTTPException(status_code=404, detail="Товар не в корзине")

    if cart_item.item.stock_quantity < data.quantity:
        raise HTTPException(status_code=400, detail="Недостаточно товара")

    cart_item.quantity = data.quantity
    await session.commit()
    await session.refresh(cart_item)

    return cart_item


@router.delete("/{cart_item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_cart(
    cart_item_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Удалить из корзины"""
    result = await session.execute(
        select(CartItem).where(
            CartItem.user_id == current_user.id,
            CartItem.id == cart_item_id,
        )
    )
    cart_item = result.scalar_one_or_none()

    if not cart_item:
        raise HTTPException(status_code=404, detail="Товар не в корзине")

    await session.delete(cart_item)
    await session.commit()
