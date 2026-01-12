"""
API для заказов (Занятия 16-17)
"""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.database import get_async_session
from app.core.deps import get_current_user, get_current_seller_user
from app.models.user import User
from app.models.item import Item
from app.models.order import Order, OrderItem, CartItem, OrderStatus
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderWithItems,
    OrderStatusUpdate,
)

router = APIRouter(prefix="/orders", tags=["Orders"])


# Допустимые переходы статусов (Занятие 17)
STATUS_TRANSITIONS = {
    OrderStatus.PENDING: [OrderStatus.PAID, OrderStatus.CANCELLED],
    OrderStatus.PAID: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
    OrderStatus.SHIPPED: [OrderStatus.DELIVERED],
    OrderStatus.DELIVERED: [],
    OrderStatus.CANCELLED: [],
}


async def send_status_notification(order_id: int, new_status: str):
    """Фоновая задача: уведомление (Занятие 17)"""
    print(f"[NOTIFICATION] Order {order_id} -> {new_status}")


@router.get("", response_model=List[OrderResponse])
async def get_orders(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """История заказов пользователя (Занятие 16)"""
    result = await session.execute(
        select(Order)
        .where(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{order_id}", response_model=OrderWithItems)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Детали заказа (Занятие 16)"""
    result = await session.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(joinedload(Order.items).joinedload(OrderItem.item))
    )
    order = result.unique().scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    if order.user_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Нет доступа")

    return order


@router.post("", response_model=OrderWithItems, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Создание заказа из корзины (Занятие 16)"""
    # Получаем корзину
    cart_result = await session.execute(
        select(CartItem)
        .where(CartItem.user_id == current_user.id)
        .options(joinedload(CartItem.item))
    )
    cart_items = cart_result.scalars().unique().all()

    if not cart_items:
        raise HTTPException(status_code=400, detail="Корзина пуста")

    # Проверяем наличие
    for ci in cart_items:
        if ci.item.stock_quantity < ci.quantity:
            raise HTTPException(
                status_code=400, detail=f"Недостаточно товара: {ci.item.name}"
            )

    # Считаем сумму
    total = sum(ci.item.price * ci.quantity for ci in cart_items)

    # Создаём заказ
    order = Order(
        order_number=f"BVP-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
        user_id=current_user.id,
        total_price=total,
        shipping_address=data.shipping_address,
        notes=data.notes,
    )
    session.add(order)
    await session.flush()

    # Создаём позиции заказа
    for ci in cart_items:
        order_item = OrderItem(
            order_id=order.id,
            item_id=ci.item_id,
            quantity=ci.quantity,
            price_at_purchase=ci.item.price,
        )
        session.add(order_item)

        # Уменьшаем остаток
        ci.item.stock_quantity -= ci.quantity

        # Удаляем из корзины
        await session.delete(ci)

    await session.commit()

    # Загружаем с items
    result = await session.execute(
        select(Order)
        .where(Order.id == order.id)
        .options(joinedload(Order.items).joinedload(OrderItem.item))
    )
    order = result.unique().scalar_one()

    # Фоновое уведомление (Занятие 17)
    background_tasks.add_task(send_status_notification, order.id, order.status.value)

    return order


@router.put("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_seller_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Изменение статуса заказа (Занятие 17)

    Только продавец/admin. Валидация переходов статусов.
    """
    result = await session.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    # Проверка допустимости перехода
    allowed = STATUS_TRANSITIONS.get(order.status, [])
    if data.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Нельзя перейти из {order.status.value} в {data.status.value}",
        )

    order.status = data.status
    await session.commit()
    await session.refresh(order)

    # Уведомление
    background_tasks.add_task(send_status_notification, order.id, order.status.value)

    return order


@router.get("/seller/orders", response_model=List[OrderResponse], tags=["Seller"])
async def get_seller_orders(
    status: Optional[OrderStatus] = None,
    current_user: User = Depends(get_current_seller_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Заказы с товарами продавца (Занятие 17)"""
    # Подзапрос: заказы с товарами этого продавца
    subquery = (
        select(OrderItem.order_id)
        .join(Item)
        .where(Item.owner_id == current_user.id)
        .distinct()
    )

    query = select(Order).where(Order.id.in_(subquery))

    if status:
        query = query.where(Order.status == status)

    query = query.order_by(Order.created_at.desc())

    result = await session.execute(query)
    return result.scalars().all()
