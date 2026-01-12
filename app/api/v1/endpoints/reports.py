"""
Административные отчёты (Занятие 33)
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_session
from app.core.deps import get_current_admin_user
from app.models.user import User
from app.models.item import Item, Category
from app.models.order import Order, OrderItem, OrderStatus

router = APIRouter(prefix="/admin/reports", tags=["Admin Reports"])


@router.get("/users")
async def users_report(
    days: int = Query(30, ge=1),
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Отчёт по пользователям"""
    since = datetime.utcnow() - timedelta(days=days)

    total = (await session.execute(select(func.count(User.id)))).scalar()
    new = (
        await session.execute(
            select(func.count(User.id)).where(User.created_at >= since)
        )
    ).scalar()
    active = (
        await session.execute(
            select(func.count(func.distinct(Order.user_id))).where(
                Order.created_at >= since
            )
        )
    ).scalar()

    return {
        "total_users": total,
        "new_users": new,
        "active_users": active,
        "period_days": days,
    }


@router.get("/items")
async def items_report(
    days: int = Query(30, ge=1),
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Отчёт по товарам"""
    since = datetime.utcnow() - timedelta(days=days)

    total = (
        await session.execute(
            select(func.count(Item.id)).where(Item.is_active.is_(True))
        )
    ).scalar()

    out_of_stock = (
        await session.execute(
            select(func.count(Item.id)).where(
                Item.is_active.is_(True), Item.stock_quantity == 0
            )
        )
    ).scalar()

    # Топ продаж
    top_result = await session.execute(
        select(Item.id, Item.name, func.sum(OrderItem.quantity).label("sold"))
        .join(OrderItem)
        .join(Order)
        .where(Order.created_at >= since, Order.status != OrderStatus.CANCELLED)
        .group_by(Item.id)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(10)
    )

    return {
        "total_items": total,
        "out_of_stock": out_of_stock,
        "top_selling": [
            {"id": r.id, "name": r.name, "sold": r.sold} for r in top_result.all()
        ],
        "period_days": days,
    }


@router.get("/categories")
async def categories_report(
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Отчёт по категориям"""
    result = await session.execute(
        select(Category.id, Category.name, func.count(Item.id).label("items_count"))
        .outerjoin(Item)
        .group_by(Category.id)
        .order_by(func.count(Item.id).desc())
    )

    return [
        {"id": r.id, "name": r.name, "items_count": r.items_count} for r in result.all()
    ]
