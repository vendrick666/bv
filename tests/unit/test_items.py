"""
Unit tests for items endpoints
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.items import get_item, create_item, update_item, delete_item
from app.models.user import User, UserRole
from app.models.item import Item
from app.schemas.item import ItemCreate, ItemUpdate


@pytest.mark.asyncio
async def test_get_item_success():
    """Test successful retrieval of an item"""
    # Mock session
    session = AsyncMock(spec=AsyncSession)

    # Create a mock item
    mock_item = Item(
        id=1,
        name="Test Item",
        price=100.0,
        description="Test Description",
        stock_quantity=10,
        is_active=True,
    )

    # Mock the database query
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_item
    session.execute.return_value = mock_result

    # Call the get_item function
    result = await get_item(1, session)

    # Assertions
    assert result.id == 1
    assert result.name == "Test Item"


@pytest.mark.asyncio
async def test_get_item_not_found():
    """Test retrieving a non-existent item raises HTTPException"""
    # Mock session
    session = AsyncMock(spec=AsyncSession)

    # Mock the database query to return None (item not found)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    # Should raise HTTPException with 404 status
    with pytest.raises(HTTPException) as exc_info:
        await get_item(999, session)

    assert exc_info.value.status_code == 404
    assert "Товар не найден" in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_item_success():
    """Test successful creation of an item"""
    # Mock session
    session = AsyncMock(spec=AsyncSession)

    # Create a mock user (seller)
    mock_user = User(
        id=1,
        email="seller@test.com",
        username="testseller",
        password_hash="$2b$12$example_hash",
        role=UserRole.SELLER,
        is_active=True,
    )

    # Mock item data
    item_data = ItemCreate(
        name="New Item",
        price=50.0,
        description="New Description",
        brand="Test Brand",
        volume_ml=100,
    )

    # Mock the session methods
    session.add.return_value = None
    session.commit.return_value = None
    session.refresh.return_value = None

    # Call the create_item function
    result = await create_item(item_data, mock_user, session)

    # Assertions
    assert result.name == "New Item"
    assert result.price == 50.0
    assert result.owner_id == 1


@pytest.mark.asyncio
async def test_update_item_success():
    """Test successful update of an item"""
    # Mock session
    session = AsyncMock(spec=AsyncSession)

    # Create a mock user (seller)
    mock_user = User(
        id=1,
        email="seller@test.com",
        username="testseller",
        password_hash="$2b$12$example_hash",
        role=UserRole.SELLER,
        is_active=True,
    )

    # Create a mock item that belongs to the user
    mock_item = Item(
        id=1,
        name="Original Item",
        price=50.0,
        description="Original Description",
        brand="Test Brand",
        volume_ml=100,
        owner_id=1,  # Owned by the mock user
    )

    # Mock the database query
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_item
    session.execute.return_value = mock_result

    # Update data
    update_data = ItemUpdate(name="Updated Item", price=75.0)

    # Call the update_item function
    result = await update_item(1, update_data, mock_user, session)

    # Assertions
    assert result.name == "Updated Item"
    assert result.price == 75.0


@pytest.mark.asyncio
async def test_update_item_not_found():
    """Test updating a non-existent item raises HTTPException"""
    # Mock session
    session = AsyncMock(spec=AsyncSession)

    # Create a mock user (seller)
    mock_user = User(
        id=1,
        email="seller@test.com",
        username="testseller",
        password_hash="$2b$12$example_hash",
        role=UserRole.SELLER,
        is_active=True,
    )

    # Mock the database query to return None (item not found)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    # Update data
    update_data = ItemUpdate(name="Updated Item", price=75.0)

    # Should raise HTTPException with 404 status
    with pytest.raises(HTTPException) as exc_info:
        await update_item(999, update_data, mock_user, session)

    assert exc_info.value.status_code == 404
    assert "Товар не найден" in exc_info.value.detail


@pytest.mark.asyncio
async def test_update_item_no_permission():
    """Test updating an item without permission raises HTTPException"""
    # Mock session
    session = AsyncMock(spec=AsyncSession)

    # Create a mock user (seller) who does not own the item
    mock_user = User(
        id=2,  # Different user ID
        email="otherseller@test.com",
        username="otherseller",
        password_hash="$2b$12$example_hash",
        role=UserRole.SELLER,
        is_active=True,
    )

    # Create a mock item that belongs to another user
    mock_item = Item(
        id=1,
        name="Original Item",
        price=50.0,
        description="Original Description",
        brand="Test Brand",
        volume_ml=100,
        owner_id=1,  # Owned by user with ID 1
    )

    # Mock the database query
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_item
    session.execute.return_value = mock_result

    # Update data
    update_data = ItemUpdate(name="Updated Item", price=75.0)

    # Should raise HTTPException with 403 status
    with pytest.raises(HTTPException) as exc_info:
        await update_item(1, update_data, mock_user, session)

    assert exc_info.value.status_code == 403
    assert "Нет прав на редактирование" in exc_info.value.detail


@pytest.mark.asyncio
async def test_delete_item_success():
    """Test successful deletion of an item"""
    # Mock session
    session = AsyncMock(spec=AsyncSession)

    # Create a mock user (seller)
    mock_user = User(
        id=1,
        email="seller@test.com",
        username="testseller",
        password_hash="$2b$12$example_hash",
        role=UserRole.SELLER,
        is_active=True,
    )

    # Create a mock item that belongs to the user
    mock_item = Item(
        id=1,
        name="Item to Delete",
        price=50.0,
        description="Description",
        brand="Test Brand",
        volume_ml=100,
        owner_id=1,  # Owned by the mock user
        is_active=True,
    )

    # Mock the database query
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_item
    session.execute.return_value = mock_result

    # Call the delete_item function (should return None as it has 204 status code)
    result = await delete_item(1, mock_user, session)

    # For 204 status code, function should return nothing
    assert result is None
    assert mock_item.is_active is False  # Soft delete should set is_active to False


@pytest.mark.asyncio
async def test_delete_item_not_found():
    """Test deleting a non-existent item raises HTTPException"""
    # Mock session
    session = AsyncMock(spec=AsyncSession)

    # Create a mock user (seller)
    mock_user = User(
        id=1,
        email="seller@test.com",
        username="testseller",
        password_hash="$2b$12$example_hash",
        role=UserRole.SELLER,
        is_active=True,
    )

    # Mock the database query to return None (item not found)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    # Should raise HTTPException with 404 status
    with pytest.raises(HTTPException) as exc_info:
        await delete_item(999, mock_user, session)

    assert exc_info.value.status_code == 404
    assert "Товар не найден" in exc_info.value.detail


@pytest.mark.asyncio
async def test_delete_item_no_permission():
    """Test deleting an item without permission raises HTTPException"""
    # Mock session
    session = AsyncMock(spec=AsyncSession)

    # Create a mock user (seller) who does not own the item
    mock_user = User(
        id=2,  # Different user ID
        email="otherseller@test.com",
        username="otherseller",
        password_hash="$2b$12$example_hash",
        role=UserRole.SELLER,
        is_active=True,
    )

    # Create a mock item that belongs to another user
    mock_item = Item(
        id=1,
        name="Item to Delete",
        price=50.0,
        description="Description",
        brand="Test Brand",
        volume_ml=100,
        owner_id=1,  # Owned by user with ID 1
    )

    # Mock the database query
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_item
    session.execute.return_value = mock_result

    # Should raise HTTPException with 403 status
    with pytest.raises(HTTPException) as exc_info:
        await delete_item(1, mock_user, session)

    assert exc_info.value.status_code == 403
    assert "Нет прав на удаление" in exc_info.value.detail
