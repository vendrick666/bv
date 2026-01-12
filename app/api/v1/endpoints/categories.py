"""
API для категорий (Занятие 12)
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_session
from app.core.deps import get_current_admin_user
from app.models.user import User
from app.models.item import Category
from app.schemas.item import CategoryCreate, CategoryResponse

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=List[CategoryResponse])
async def get_categories(session: AsyncSession = Depends(get_async_session)):
    """Список категорий"""
    result = await session.execute(select(Category).order_by(Category.name))
    return result.scalars().all()


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: CategoryCreate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Создание категории - только admin"""
    result = await session.execute(select(Category).where(Category.name == data.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Категория уже существует")

    category = Category(**data.model_dump())
    session.add(category)
    await session.commit()
    await session.refresh(category)

    return category
