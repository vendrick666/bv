"""
Pytest fixtures for pytest-asyncio 0.24+
"""

import os
from typing import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.security import create_access_token, get_password_hash
from app.db.database import Base, get_async_session
from app.main import app
from app.models.user import User, UserRole

TEST_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_maker() as session:
        yield session

    # Drop all tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with overridden database session."""

    async def override_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a regular test user."""
    user = User(
        email="test@test.com",
        username="testuser",
        password_hash=get_password_hash("Test1234"),
        role=UserRole.USER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_seller(db_session: AsyncSession) -> User:
    """Create a seller test user."""
    user = User(
        email="seller@test.com",
        username="testseller",
        password_hash=get_password_hash("Test1234"),
        role=UserRole.SELLER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create an admin test user."""
    user = User(
        email="admin@test.com",
        username="testadmin",
        password_hash=get_password_hash("Test1234"),
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict:
    """Get auth headers for regular user."""
    token = create_access_token({"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def seller_headers(test_seller: User) -> dict:
    """Get auth headers for seller."""
    token = create_access_token({"sub": str(test_seller.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_headers(test_admin: User) -> dict:
    """Get auth headers for admin."""
    token = create_access_token({"sub": str(test_admin.id)})
    return {"Authorization": f"Bearer {token}"}
