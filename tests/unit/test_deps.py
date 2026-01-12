import pytest
from fastapi import HTTPException

from app.core.deps import RoleChecker, get_current_admin_user, get_current_seller_user
from app.models.user import UserRole


class DummyUser:
    def __init__(self, role, is_active=True):
        self.role = role
        self.is_active = is_active


@pytest.mark.asyncio
async def test_role_checker_allows_admin():
    rc = RoleChecker([UserRole.ADMIN.value])
    user = DummyUser(UserRole.ADMIN)
    result = await rc(current_user=user)
    assert result is user


@pytest.mark.asyncio
async def test_role_checker_forbids():
    rc = RoleChecker([UserRole.ADMIN.value])
    user = DummyUser(UserRole.SELLER)
    with pytest.raises(HTTPException) as exc:
        await rc(current_user=user)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_current_admin_user_and_seller_return_user():
    user = DummyUser(UserRole.ADMIN)
    assert await get_current_admin_user(user=user) is user

    user2 = DummyUser(UserRole.SELLER)
    assert await get_current_seller_user(user=user2) is user2
