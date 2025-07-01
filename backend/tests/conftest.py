"""
Pytest configuration and fixtures for backend tests.

This file provides common fixtures and configuration for all tests.
"""

import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.database.base import Base, engine, create_tables, drop_tables
from app.models import Location, LocationType, Category, Item, ItemType, Inventory
from app.services.inventory_service import InventoryService


# Configure async test support
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    # Create tables
    await create_tables()
    
    try:
        # Create a new session for the test
        from app.database.base import async_session
        async with async_session() as session:
            yield session
    finally:
        # Clean up tables after test
        await drop_tables()


@pytest.fixture
async def sample_location(test_session: AsyncSession) -> Location:
    """Create a sample location for testing."""
    location = Location(
        name="Test Room",
        location_type=LocationType.ROOM,
        description="A test room for items"
    )
    test_session.add(location)
    await test_session.commit()
    await test_session.refresh(location)
    return location


@pytest.fixture
async def sample_category(test_session: AsyncSession) -> Category:
    """Create a sample category for testing."""
    category = Category(
        name="Electronics",
        description="Electronic devices and accessories",
        color="#0066CC"
    )
    test_session.add(category)
    await test_session.commit()
    await test_session.refresh(category)
    return category


@pytest.fixture
async def sample_item(test_session: AsyncSession, sample_category: Category) -> Item:
    """Create a sample item for testing."""
    item = Item(
        name="Test Laptop",
        description="A test laptop for testing",
        item_type=ItemType.ELECTRONICS,
        category_id=sample_category.id,
        brand="TestBrand",
        model="TB-2023"
    )
    test_session.add(item)
    await test_session.commit()
    await test_session.refresh(item)
    return item


@pytest.fixture
async def sample_inventory(
    test_session: AsyncSession, 
    sample_item: Item, 
    sample_location: Location
) -> Inventory:
    """Create a sample inventory entry for testing."""
    inventory = Inventory(
        item_id=sample_item.id,
        location_id=sample_location.id,
        quantity=1
    )
    test_session.add(inventory)
    await test_session.commit()
    await test_session.refresh(inventory)
    return inventory


@pytest.fixture
async def inventory_service(test_session: AsyncSession) -> InventoryService:
    """Create an InventoryService instance for testing."""
    return InventoryService(test_session)


@pytest.fixture
def mock_api_client(mocker):
    """Create a mock API client for testing."""
    mock = mocker.MagicMock()
    mock.base_url = "http://test-api"
    return mock