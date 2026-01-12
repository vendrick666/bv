"""
API для аутентификации (Занятия 7-8)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_session
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password_async,
    get_password_hash_async,
)
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token, LoginRequest

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Регистрация пользователя (Занятие 7)"""
    # Проверка email
    result = await session.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")

    # Проверка username
    result = await session.execute(
        select(User).where(User.username == user_data.username)
    )
    existing_user = result.scalar_one_or_none()
    if existing_user:
        # Маскируем email: показываем первые 2 символа и домен
        email = existing_user.email
        at_pos = email.find("@")
        if at_pos > 2:
            masked_email = email[:2] + "*" * (at_pos - 2) + email[at_pos:]
        else:
            masked_email = (
                email[0] + "*" * (at_pos - 1) + email[at_pos:] if at_pos > 0 else email
            )
        raise HTTPException(
            status_code=400,
            detail=f"Логин '{user_data.username}' уже занят пользователем с почтой: {masked_email}",
        )

    # Проверка уникальности пароля
    password_hash = await get_password_hash_async(user_data.password)
    result = await session.execute(select(User))
    all_users = result.scalars().all()

    for existing_user in all_users:
        if await verify_password_async(user_data.password, existing_user.password_hash):
            email = existing_user.email
            at_pos = email.find("@")
            if at_pos > 2:
                masked_email = email[:2] + "*" * (at_pos - 2) + email[at_pos:]
            else:
                masked_email = (
                    email[0] + "*" * (at_pos - 1) + email[at_pos:]
                    if at_pos > 0
                    else email
                )
            raise HTTPException(
                status_code=400,
                detail=f"Этот пароль уже используется пользователем: {masked_email}. Придумайте другой пароль.",
            )

    # Создание пользователя
    user = User(
        email=user_data.email,
        username=user_data.username,
        password_hash=password_hash,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return user


@router.post("/login", response_model=Token)
async def login(
    credentials: LoginRequest,
    session: AsyncSession = Depends(get_async_session),
):
    """Вход в систему - по email или username (Занятие 8)"""
    # Ищем по email или username
    login_value = credentials.login.strip()

    # Проверяем, похоже ли на email
    if "@" in login_value:
        result = await session.execute(select(User).where(User.email == login_value))
    else:
        result = await session.execute(select(User).where(User.username == login_value))

    user = result.scalar_one_or_none()

    # Если не нашли по username, попробуем по email
    if not user and "@" not in login_value:
        result = await session.execute(select(User).where(User.email == login_value))
        user = result.scalar_one_or_none()

    if not user or not await verify_password_async(
        credentials.password, user.password_hash
    ):
        raise HTTPException(status_code=401, detail="Неверный логин/email или пароль")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Аккаунт деактивирован")

    return Token(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=create_refresh_token({"sub": str(user.id)}),
        user=user,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Текущий пользователь (Занятие 8)"""
    return current_user
