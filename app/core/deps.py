"""
Dependency Injection (Занятия 5, 8, 9)
"""

from typing import List

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_session
from app.core.security import decode_token
from app.models.user import User, UserRole

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """Получение текущего пользователя (Занятие 8)"""
    token = credentials.credentials
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    result = await session.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    return user


class RoleChecker:
    """
    Проверка ролей (Занятие 9)

    Использование:
        @router.get("/admin")
        async def admin_only(user: User = Depends(RoleChecker(["admin"]))):
            ...
    """

    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    async def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.value not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
            )
        return current_user


# Готовые dependency
async def get_current_admin_user(
    user: User = Depends(RoleChecker([UserRole.ADMIN.value])),
) -> User:
    """Только админ (Занятие 9)"""
    return user


async def get_current_seller_user(
    user: User = Depends(RoleChecker([UserRole.SELLER.value, UserRole.ADMIN.value]))
) -> User:
    """Продавец или админ"""
    return user
