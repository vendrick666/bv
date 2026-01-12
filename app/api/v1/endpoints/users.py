"""
API для управления пользователями (только админ)
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, Field

from app.db.database import get_async_session
from app.core.deps import get_current_user
from app.core.security import get_password_hash_async
from app.models.user import User, UserRole

router = APIRouter(prefix="/users", tags=["Users Management"])


class UserCreateByAdmin(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6)
    first_name: Optional[str] = None
    role: UserRole = UserRole.USER


class UserUpdateByAdmin(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserAdminResponse(BaseModel):
    id: int
    email: str
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}


def check_admin(user: User):
    """Проверка прав админа"""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Только для администраторов")


@router.get("", response_model=List[UserAdminResponse])
async def get_users(
    role: Optional[UserRole] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Список всех пользователей - только админ"""
    check_admin(current_user)

    query = select(User).order_by(User.created_at.desc())

    if role:
        query = query.where(User.role == role)

    result = await session.execute(query)
    return result.scalars().all()


@router.post("", response_model=UserAdminResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreateByAdmin,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Создание пользователя админом"""
    check_admin(current_user)

    # Проверка email
    result = await session.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")

    # Проверка username
    result = await session.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username уже занят")

    user = User(
        email=data.email,
        username=data.username,
        password_hash=await get_password_hash_async(data.password),
        first_name=data.first_name,
        role=data.role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user


@router.get("/{user_id}", response_model=UserAdminResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Получение пользователя по ID - только админ"""
    check_admin(current_user)

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    return user


@router.put("/{user_id}", response_model=UserAdminResponse)
async def update_user(
    user_id: int,
    data: UserUpdateByAdmin,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Обновление пользователя - только админ"""
    check_admin(current_user)

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Нельзя менять роль самому себе
    if user_id == current_user.id and data.role and data.role != current_user.role:
        raise HTTPException(status_code=400, detail="Нельзя изменить свою роль")

    # Нельзя деактивировать самого себя
    if user_id == current_user.id and data.is_active is False:
        raise HTTPException(status_code=400, detail="Нельзя деактивировать себя")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)

    await session.commit()
    await session.refresh(user)

    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Деактивация пользователя - только админ"""
    check_admin(current_user)

    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Нельзя удалить себя")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    user.is_active = False
    await session.commit()


@router.get("/staff/list", response_model=List[UserAdminResponse])
async def get_staff(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Список саппортов и админов - для назначения тикетов"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPPORT]:
        raise HTTPException(status_code=403, detail="Нет доступа")

    result = await session.execute(
        select(User)
        .where(User.role.in_([UserRole.SUPPORT, UserRole.ADMIN]))
        .where(User.is_active.is_(True))
    )
    return result.scalars().all()
