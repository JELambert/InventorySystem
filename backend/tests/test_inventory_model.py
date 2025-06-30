"""
Test cases for the Inventory model and inventory functionality.

Tests the many-to-many relationship between Items and Locations through Inventory.
"""

import pytest
from datetime import datetime
from decimal import Decimal

from app.database.base import Base, engine, create_tables, drop_tables
from app.models.inventory import Inventory
from app.models.item import Item, ItemType, ItemCondition, ItemStatus
from app.models.location import Location, LocationType
from app.models.category import Category


async def _get_test_session():
    """Helper to get a test session with setup/teardown."""
    await create_tables()
    try:
        from app.database.base import async_session
        async with async_session() as session:
            yield session
    finally:
        await drop_tables()


@pytest.mark.asyncio
async def test_create_inventory_entry():
    """Test creating a basic inventory entry."""
    async for session in _get_test_session():
        # Create a location
        location = Location(
            name="Test Warehouse",
            description="A test warehouse",
            location_type=LocationType.ROOM
        )
        session.add(location)
        await session.commit()
        await session.refresh(location)

        # Create an item without location_id
        item = Item(
            name="Test Item",
            item_type=ItemType.OTHER
        )
        session.add(item)
        await session.commit()
        await session.refresh(item)

        # Create inventory entry
        inventory = Inventory(
            item_id=item.id,
            location_id=location.id,
            quantity=5
        )
        session.add(inventory)
        await session.commit()
        await session.refresh(inventory)

        # Verify inventory entry
        assert inventory.id is not None
        assert inventory.item_id == item.id
        assert inventory.location_id == location.id
        assert inventory.quantity == 5
        assert inventory.updated_at is not None


@pytest.mark.asyncio
async def test_inventory_relationships(test_session):
    """Test inventory relationships with items and locations."""
    # Create test data
    location = Location(
        name="Storage Room",
        location_type=LocationType.ROOM
    )
    test_session.add(location)

    item = Item(
        name="Widget",
        item_type=ItemType.OTHER,
        current_value=Decimal("25.99")
    )
    test_session.add(item)
    
    await test_session.commit()
    await test_session.refresh(location)
    await test_session.refresh(item)

    # Create inventory entry
    inventory = Inventory(
        item_id=item.id,
        location_id=location.id,
        quantity=3
    )
    test_session.add(inventory)
    await test_session.commit()
    await test_session.refresh(inventory)

    # Test relationships
    assert inventory.item is not None
    assert inventory.item.name == "Widget"
    assert inventory.location is not None
    assert inventory.location.name == "Storage Room"

    # Test reverse relationships
    assert len(item.inventory_entries) == 1
    assert item.inventory_entries[0].location_id == location.id
    assert len(location.inventory_entries) == 1
    assert location.inventory_entries[0].item_id == item.id


@pytest.mark.asyncio
async def test_inventory_total_value_property(test_session):
    """Test the total_value property calculation."""
    # Create test data
    location = Location(name="Test Location", location_type=LocationType.ROOM)
    test_session.add(location)

    # Item with value
    item_with_value = Item(
        name="Valuable Item",
        item_type=ItemType.ELECTRONICS,
        current_value=Decimal("100.00")
    )
    test_session.add(item_with_value)

    # Item without value
    item_no_value = Item(
        name="Valueless Item",
        item_type=ItemType.OTHER
    )
    test_session.add(item_no_value)

    await test_session.commit()
    await test_session.refresh(location)
    await test_session.refresh(item_with_value)
    await test_session.refresh(item_no_value)

    # Inventory with value
    inventory_with_value = Inventory(
        item_id=item_with_value.id,
        location_id=location.id,
        quantity=2
    )
    test_session.add(inventory_with_value)

    # Inventory without value
    inventory_no_value = Inventory(
        item_id=item_no_value.id,
        location_id=location.id,
        quantity=5
    )
    test_session.add(inventory_no_value)

    await test_session.commit()
    await test_session.refresh(inventory_with_value)
    await test_session.refresh(inventory_no_value)

    # Test total value calculation
    assert inventory_with_value.total_value == 200.0  # 100.00 * 2
    assert inventory_no_value.total_value is None


@pytest.mark.asyncio
async def test_inventory_unique_constraint(test_session):
    """Test that item-location combinations are unique."""
    # Create test data
    location = Location(name="Test Location", location_type=LocationType.ROOM)
    test_session.add(location)

    item = Item(name="Test Item", item_type=ItemType.OTHER)
    test_session.add(item)

    await test_session.commit()
    await test_session.refresh(location)
    await test_session.refresh(item)

    # Create first inventory entry
    inventory1 = Inventory(
        item_id=item.id,
        location_id=location.id,
        quantity=1
    )
    test_session.add(inventory1)
    await test_session.commit()

    # Try to create duplicate - this should fail
    inventory2 = Inventory(
        item_id=item.id,
        location_id=location.id,
        quantity=2
    )
    test_session.add(inventory2)

    with pytest.raises(Exception):  # Should raise integrity error
        await test_session.commit()


@pytest.mark.asyncio
async def test_inventory_cascade_delete(test_session):
    """Test that inventory entries are deleted when items or locations are deleted."""
    # Create test data
    location = Location(name="Test Location", location_type=LocationType.ROOM)
    test_session.add(location)

    item = Item(name="Test Item", item_type=ItemType.OTHER)
    test_session.add(item)

    await test_session.commit()
    await test_session.refresh(location)
    await test_session.refresh(item)

    # Create inventory entry
    inventory = Inventory(
        item_id=item.id,
        location_id=location.id,
        quantity=1
    )
    test_session.add(inventory)
    await test_session.commit()

    inventory_id = inventory.id

    # Delete the item - inventory should be deleted due to CASCADE
    await test_session.delete(item)
    await test_session.commit()

    # Verify inventory entry is deleted
    from sqlalchemy import select
    result = await test_session.execute(select(Inventory).where(Inventory.id == inventory_id))
    deleted_inventory = result.scalar_one_or_none()
    assert deleted_inventory is None


@pytest.mark.asyncio
async def test_inventory_to_dict(test_session):
    """Test the to_dict method."""
    # Create test data
    location = Location(name="Test Location", location_type=LocationType.ROOM)
    test_session.add(location)

    item = Item(
        name="Test Item",
        item_type=ItemType.OTHER,
        current_value=Decimal("50.00")
    )
    test_session.add(item)

    await test_session.commit()
    await test_session.refresh(location)
    await test_session.refresh(item)

    # Create inventory entry
    inventory = Inventory(
        item_id=item.id,
        location_id=location.id,
        quantity=3
    )
    test_session.add(inventory)
    await test_session.commit()
    await test_session.refresh(inventory)

    # Test to_dict
    result = inventory.to_dict()
    
    assert result["id"] == inventory.id
    assert result["item_id"] == item.id
    assert result["location_id"] == location.id
    assert result["quantity"] == 3
    assert result["total_value"] == 150.0  # 50.00 * 3
    assert "updated_at" in result


@pytest.mark.asyncio
async def test_item_primary_location_property(test_session):
    """Test the Item.primary_location property."""
    # Create test data
    location1 = Location(name="Location 1", location_type=LocationType.ROOM)
    location2 = Location(name="Location 2", location_type=LocationType.ROOM)
    test_session.add_all([location1, location2])

    item = Item(name="Multi-location Item", item_type=ItemType.OTHER)
    test_session.add(item)

    await test_session.commit()
    await test_session.refresh(location1)
    await test_session.refresh(location2)
    await test_session.refresh(item)

    # Create multiple inventory entries
    inventory1 = Inventory(item_id=item.id, location_id=location1.id, quantity=2)
    inventory2 = Inventory(item_id=item.id, location_id=location2.id, quantity=1)
    test_session.add_all([inventory1, inventory2])
    await test_session.commit()
    await test_session.refresh(item)

    # Test primary location (should be first inventory entry)
    primary_location = item.primary_location
    assert primary_location is not None
    assert primary_location.name in ["Location 1", "Location 2"]


@pytest.mark.asyncio
async def test_item_full_location_path_property(test_session):
    """Test the Item.full_location_path property with inventory."""
    # Create test data
    location = Location(name="Test Location", location_type=LocationType.ROOM)
    test_session.add(location)

    item = Item(name="Test Item", item_type=ItemType.OTHER)
    test_session.add(item)

    await test_session.commit()
    await test_session.refresh(location)
    await test_session.refresh(item)

    # Without inventory entry
    assert item.full_location_path == "Test Item"

    # With inventory entry
    inventory = Inventory(item_id=item.id, location_id=location.id, quantity=1)
    test_session.add(inventory)
    await test_session.commit()
    await test_session.refresh(item)

    assert "Test Location/Test Item" in item.full_location_path


@pytest.mark.asyncio
async def test_inventory_model_indexes(test_session):
    """Test that the model indexes work correctly."""
    # This test verifies that the indexes are created properly
    # by performing operations that should use them
    
    # Create multiple items and locations
    locations = [
        Location(name=f"Location {i}", location_type=LocationType.ROOM)
        for i in range(3)
    ]
    test_session.add_all(locations)

    items = [
        Item(name=f"Item {i}", item_type=ItemType.OTHER)
        for i in range(3)
    ]
    test_session.add_all(items)

    await test_session.commit()
    for location in locations:
        await test_session.refresh(location)
    for item in items:
        await test_session.refresh(item)

    # Create inventory entries
    inventory_entries = []
    for i, (item, location) in enumerate(zip(items, locations)):
        inventory = Inventory(
            item_id=item.id,
            location_id=location.id,
            quantity=i + 1
        )
        inventory_entries.append(inventory)
        test_session.add(inventory)

    await test_session.commit()

    # Test queries that should use indexes
    from sqlalchemy import select

    # Query by item_id (should use ix_inventory_item_id)
    result = await test_session.execute(
        select(Inventory).where(Inventory.item_id == items[0].id)
    )
    found = result.scalar_one_or_none()
    assert found is not None

    # Query by location_id (should use ix_inventory_location_id)
    result = await test_session.execute(
        select(Inventory).where(Inventory.location_id == locations[1].id)
    )
    found = result.scalar_one_or_none()
    assert found is not None

    # Query by item_id and location_id (should use ix_inventory_item_location)
    result = await test_session.execute(
        select(Inventory).where(
            (Inventory.item_id == items[2].id) &
            (Inventory.location_id == locations[2].id)
        )
    )
    found = result.scalar_one_or_none()
    assert found is not None
    assert found.quantity == 3