"""
Pytest fixtures
"""

import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.security import create_access_token, get_password_hash
from app.db.database import Base, get_async_session
from app.main import app
from app.models.user import User, UserRole

TEST_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")


# This fixture is required for session-scoped async fixtures to work properly
# It must be a regular pytest fixture, not pytest_asyncio fixture
@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    import asyncio

    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine(event_loop) -> AsyncGenerator[AsyncEngine, None]:
    """Create test database engine and tables once per test session."""
    # Use pool_pre_ping to handle connection issues
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables and close engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for each test with transaction rollback."""
    connection = await test_engine.connect()
    # Start a transaction that we'll roll back after the test
    transaction = await connection.begin()

    session_maker = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_maker() as session:
            yield session
    finally:
        # Always rollback the transaction to clean up test data
        await transaction.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
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
    token = create_access_token({"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def seller_headers(test_seller: User) -> dict:
    token = create_access_token({"sub": str(test_seller.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_headers(test_admin: User) -> dict:
    token = create_access_token({"sub": str(test_admin.id)})
    return {"Authorization": f"Bearer {token}"}
