"""
Unit tests for auth endpoints
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import login
from app.schemas.user import LoginRequest
from app.models.user import User, UserRole


@pytest.mark.asyncio
async def test_login_success():
    """Test successful login with email"""
    # Mock session
    session = AsyncMock(spec=AsyncSession)

    # Create a mock user
    mock_user = User(
        id=1,
        email="test@test.com",
        username="testuser",
        password_hash="$2b$12$example_hash",  # Valid bcrypt hash
        role=UserRole.USER,
        is_active=True,
        created_at=datetime.utcnow(),
    )

    # Mock the database query
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    session.execute.return_value = mock_result

    # Mock verify_password_async to return True
    with patch("app.api.v1.endpoints.auth.verify_password_async", return_value=True):
        with patch(
            "app.api.v1.endpoints.auth.create_access_token",
            return_value="mock_access_token",
        ):
            with patch(
                "app.api.v1.endpoints.auth.create_refresh_token",
                return_value="mock_refresh_token",
            ):
                # Call the login function
                credentials = LoginRequest(login="test@test.com", password="Test1234")
                result = await login(credentials, session)

                # Assertions
                assert result.access_token == "mock_access_token"
                assert result.refresh_token == "mock_refresh_token"
                assert result.user.id == mock_user.id
                assert result.user.email == mock_user.email
                assert result.user.username == mock_user.username


@pytest.mark.asyncio
async def test_login_with_username():
    """Test successful login with username"""
    # Mock session
    session = AsyncMock(spec=AsyncSession)

    # Create a mock user
    mock_user = User(
        id=1,
        email="test@test.com",
        username="testuser",
        password_hash="$2b$12$example_hash",  # Valid bcrypt hash
        role=UserRole.USER,
        is_active=True,
        created_at=datetime.utcnow(),
    )

    # Mock the database query (first call returns None, second call returns user)
    first_result = MagicMock()
    first_result.scalar_one_or_none.return_value = None

    second_result = MagicMock()
    second_result.scalar_one_or_none.return_value = mock_user

    session.execute.side_effect = [first_result, second_result]

    # Mock verify_password_async to return True
    with patch("app.api.v1.endpoints.auth.verify_password_async", return_value=True):
        with patch(
            "app.api.v1.endpoints.auth.create_access_token",
            return_value="mock_access_token",
        ):
            with patch(
                "app.api.v1.endpoints.auth.create_refresh_token",
                return_value="mock_refresh_token",
            ):
                # Call the login function
                credentials = LoginRequest(login="testuser", password="Test1234")
                result = await login(credentials, session)

                # Assertions
                assert result.access_token == "mock_access_token"
                assert result.refresh_token == "mock_refresh_token"
                assert result.user.id == mock_user.id
                assert result.user.email == mock_user.email
                assert result.user.username == mock_user.username


@pytest.mark.asyncio
async def test_login_wrong_password():
    """Test login with wrong password raises HTTPException"""
    # Mock session
    session = AsyncMock(spec=AsyncSession)

    # Create a mock user
    mock_user = User(
        id=1,
        email="test@test.com",
        username="testuser",
        password_hash="$2b$12$example_hash",  # Valid bcrypt hash
        role=UserRole.USER,
        is_active=True,
    )

    # Mock the database query
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    session.execute.return_value = mock_result

    # Mock verify_password_async to return False (wrong password)
    with patch("app.api.v1.endpoints.auth.verify_password_async", return_value=False):
        credentials = LoginRequest(login="test@test.com", password="WrongPassword")

        # Should raise HTTPException with 401 status
        with pytest.raises(HTTPException) as exc_info:
            await login(credentials, session)

        assert exc_info.value.status_code == 401
        assert "Неверный логин/email или пароль" in exc_info.value.detail


@pytest.mark.asyncio
async def test_login_user_not_found():
    """Test login with non-existent user raises HTTPException"""
    # Mock session
    session = AsyncMock(spec=AsyncSession)

    # Mock the database query to return None (user not found)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    credentials = LoginRequest(login="nonexistent@test.com", password="Test1234")

    # Should raise HTTPException with 401 status
    with pytest.raises(HTTPException) as exc_info:
        await login(credentials, session)

    assert exc_info.value.status_code == 401
    assert "Неверный логин/email или пароль" in exc_info.value.detail


@pytest.mark.asyncio
async def test_login_inactive_user():
    """Test login with inactive user raises HTTPException"""
    # Mock session
    session = AsyncMock(spec=AsyncSession)

    # Create a mock user that is not active
    mock_user = User(
        id=1,
        email="test@test.com",
        username="testuser",
        password_hash="$2b$12$example_hash",  # Valid bcrypt hash
        role=UserRole.USER,
        is_active=False,  # User is not active
        created_at=datetime.utcnow(),
    )

    # Mock the database query
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    session.execute.return_value = mock_result

    # Mock verify_password_async to return True
    with patch("app.api.v1.endpoints.auth.verify_password_async", return_value=True):
        credentials = LoginRequest(login="test@test.com", password="Test1234")

        # Should raise HTTPException with 401 status
        with pytest.raises(HTTPException) as exc_info:
            await login(credentials, session)

        assert exc_info.value.status_code == 401
        assert "Аккаунт деактивирован" in exc_info.value.detail
