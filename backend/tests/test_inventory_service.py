"""
Test cases for the Inventory Service.

Tests business logic for inventory operations including CRUD, search, and reporting.
"""

import pytest
from decimal import Decimal

from app.services.inventory_service import InventoryService
from app.models.inventory import Inventory
from app.models.item import Item, ItemType, ItemCondition, ItemStatus
from app.models.location import Location, LocationType
from app.schemas.inventory import (
    InventoryCreate, InventoryUpdate, InventorySearch, InventoryMove, InventoryBulkOperation
)


@pytest.fixture
async def inventory_service(test_session):
    """Create an inventory service instance with test session."""
    return InventoryService(test_session)


@pytest.fixture
async def test_data(test_session):
    """Create test data for inventory tests."""
    # Create locations
    warehouse = Location(name="Warehouse", location_type=LocationType.ROOM)
    office = Location(name="Office", location_type=LocationType.ROOM)
    test_session.add_all([warehouse, office])

    # Create items
    laptop = Item(
        name="Laptop",
        item_type=ItemType.ELECTRONICS,
        current_value=Decimal("1500.00")
    )
    mouse = Item(
        name="Mouse",
        item_type=ItemType.ELECTRONICS,
        current_value=Decimal("25.00")
    )
    book = Item(
        name="Book",
        item_type=ItemType.BOOKS,
        current_value=Decimal("15.00")
    )
    test_session.add_all([laptop, mouse, book])

    await test_session.commit()
    
    # Refresh to get IDs
    for obj in [warehouse, office, laptop, mouse, book]:
        await test_session.refresh(obj)

    return {
        "locations": {"warehouse": warehouse, "office": office},
        "items": {"laptop": laptop, "mouse": mouse, "book": book}
    }


@pytest.mark.asyncio
async def test_create_inventory_entry(inventory_service, test_data):
    """Test creating a new inventory entry."""
    laptop = test_data["items"]["laptop"]
    warehouse = test_data["locations"]["warehouse"]

    inventory_data = InventoryCreate(
        item_id=laptop.id,
        location_id=warehouse.id,
        quantity=2
    )

    # Create inventory entry
    result = await inventory_service.create_inventory_entry(inventory_data)

    assert result.id is not None
    assert result.item_id == laptop.id
    assert result.location_id == warehouse.id
    assert result.quantity == 2


@pytest.mark.asyncio
async def test_create_inventory_entry_duplicate_fails(inventory_service, test_data):
    """Test that creating duplicate inventory entries fails."""
    laptop = test_data["items"]["laptop"]
    warehouse = test_data["locations"]["warehouse"]

    inventory_data = InventoryCreate(
        item_id=laptop.id,
        location_id=warehouse.id,
        quantity=1
    )

    # Create first entry
    await inventory_service.create_inventory_entry(inventory_data)

    # Try to create duplicate - should fail
    with pytest.raises(ValueError, match="already exists"):
        await inventory_service.create_inventory_entry(inventory_data)


@pytest.mark.asyncio
async def test_create_inventory_entry_invalid_item(inventory_service, test_data):
    """Test creating inventory entry with invalid item ID."""
    warehouse = test_data["locations"]["warehouse"]

    inventory_data = InventoryCreate(
        item_id=99999,  # Non-existent item
        location_id=warehouse.id,
        quantity=1
    )

    with pytest.raises(ValueError, match="Item.*not found"):
        await inventory_service.create_inventory_entry(inventory_data)


@pytest.mark.asyncio
async def test_create_inventory_entry_invalid_location(inventory_service, test_data):
    """Test creating inventory entry with invalid location ID."""
    laptop = test_data["items"]["laptop"]

    inventory_data = InventoryCreate(
        item_id=laptop.id,
        location_id=99999,  # Non-existent location
        quantity=1
    )

    with pytest.raises(ValueError, match="Location.*not found"):
        await inventory_service.create_inventory_entry(inventory_data)


@pytest.mark.asyncio
async def test_get_inventory_entry(inventory_service, test_data):
    """Test retrieving an inventory entry by ID."""
    laptop = test_data["items"]["laptop"]
    warehouse = test_data["locations"]["warehouse"]

    # Create inventory entry
    inventory_data = InventoryCreate(
        item_id=laptop.id,
        location_id=warehouse.id,
        quantity=3
    )
    created = await inventory_service.create_inventory_entry(inventory_data)

    # Retrieve by ID
    result = await inventory_service.get_inventory_entry(created.id)

    assert result is not None
    assert result.id == created.id
    assert result.item is not None
    assert result.item.name == "Laptop"
    assert result.location is not None
    assert result.location.name == "Warehouse"


@pytest.mark.asyncio
async def test_update_inventory_entry_quantity(inventory_service, test_data):
    """Test updating inventory entry quantity."""
    laptop = test_data["items"]["laptop"]
    warehouse = test_data["locations"]["warehouse"]

    # Create inventory entry
    inventory_data = InventoryCreate(
        item_id=laptop.id,
        location_id=warehouse.id,
        quantity=1
    )
    created = await inventory_service.create_inventory_entry(inventory_data)

    # Update quantity
    update_data = InventoryUpdate(quantity=5)
    result = await inventory_service.update_inventory_entry(created.id, update_data)

    assert result is not None
    assert result.quantity == 5
    assert result.item_id == laptop.id
    assert result.location_id == warehouse.id


@pytest.mark.asyncio
async def test_update_inventory_entry_location(inventory_service, test_data):
    """Test moving inventory entry to different location."""
    laptop = test_data["items"]["laptop"]
    warehouse = test_data["locations"]["warehouse"]
    office = test_data["locations"]["office"]

    # Create inventory entry in warehouse
    inventory_data = InventoryCreate(
        item_id=laptop.id,
        location_id=warehouse.id,
        quantity=1
    )
    created = await inventory_service.create_inventory_entry(inventory_data)

    # Move to office
    update_data = InventoryUpdate(location_id=office.id)
    result = await inventory_service.update_inventory_entry(created.id, update_data)

    assert result is not None
    assert result.location_id == office.id
    assert result.item_id == laptop.id
    assert result.quantity == 1


@pytest.mark.asyncio
async def test_delete_inventory_entry(inventory_service, test_data):
    """Test deleting an inventory entry."""
    laptop = test_data["items"]["laptop"]
    warehouse = test_data["locations"]["warehouse"]

    # Create inventory entry
    inventory_data = InventoryCreate(
        item_id=laptop.id,
        location_id=warehouse.id,
        quantity=1
    )
    created = await inventory_service.create_inventory_entry(inventory_data)

    # Delete entry
    success = await inventory_service.delete_inventory_entry(created.id)
    assert success is True

    # Verify deletion
    result = await inventory_service.get_inventory_entry(created.id)
    assert result is None


@pytest.mark.asyncio
async def test_search_inventory_by_item(inventory_service, test_data):
    """Test searching inventory by item ID."""
    laptop = test_data["items"]["laptop"]
    mouse = test_data["items"]["mouse"]
    warehouse = test_data["locations"]["warehouse"]

    # Create inventory entries
    for item in [laptop, mouse]:
        inventory_data = InventoryCreate(
            item_id=item.id,
            location_id=warehouse.id,
            quantity=1
        )
        await inventory_service.create_inventory_entry(inventory_data)

    # Search by laptop item ID
    search_params = InventorySearch(item_id=laptop.id)
    results = await inventory_service.search_inventory(search_params)

    assert len(results) == 1
    assert results[0].item_id == laptop.id


@pytest.mark.asyncio
async def test_search_inventory_by_location(inventory_service, test_data):
    """Test searching inventory by location ID."""
    laptop = test_data["items"]["laptop"]
    warehouse = test_data["locations"]["warehouse"]
    office = test_data["locations"]["office"]

    # Create inventory entries in different locations
    warehouse_data = InventoryCreate(
        item_id=laptop.id,
        location_id=warehouse.id,
        quantity=1
    )
    await inventory_service.create_inventory_entry(warehouse_data)

    # Search by warehouse location
    search_params = InventorySearch(location_id=warehouse.id)
    results = await inventory_service.search_inventory(search_params)

    assert len(results) == 1
    assert results[0].location_id == warehouse.id


@pytest.mark.asyncio
async def test_search_inventory_by_quantity_range(inventory_service, test_data):
    """Test searching inventory by quantity range."""
    laptop = test_data["items"]["laptop"]
    mouse = test_data["items"]["mouse"]
    warehouse = test_data["locations"]["warehouse"]

    # Create inventory entries with different quantities
    laptop_data = InventoryCreate(
        item_id=laptop.id,
        location_id=warehouse.id,
        quantity=5
    )
    await inventory_service.create_inventory_entry(laptop_data)

    mouse_data = InventoryCreate(
        item_id=mouse.id,
        location_id=warehouse.id,
        quantity=1
    )
    await inventory_service.create_inventory_entry(mouse_data)

    # Search by minimum quantity
    search_params = InventorySearch(min_quantity=3)
    results = await inventory_service.search_inventory(search_params)

    assert len(results) == 1
    assert results[0].item_id == laptop.id
    assert results[0].quantity == 5


@pytest.mark.asyncio
async def test_move_item_partial(inventory_service, test_data):
    """Test moving part of an item's quantity to another location."""
    laptop = test_data["items"]["laptop"]
    warehouse = test_data["locations"]["warehouse"]
    office = test_data["locations"]["office"]

    # Create inventory entry with quantity 5
    inventory_data = InventoryCreate(
        item_id=laptop.id,
        location_id=warehouse.id,
        quantity=5
    )
    await inventory_service.create_inventory_entry(inventory_data)

    # Move 2 items to office
    move_data = InventoryMove(
        from_location_id=warehouse.id,
        to_location_id=office.id,
        quantity=2
    )
    result = await inventory_service.move_item(laptop.id, move_data)

    # Verify destination entry
    assert result.location_id == office.id
    assert result.quantity == 2

    # Verify source entry still exists with reduced quantity
    search_params = InventorySearch(item_id=laptop.id, location_id=warehouse.id)
    source_entries = await inventory_service.search_inventory(search_params)
    assert len(source_entries) == 1
    assert source_entries[0].quantity == 3


@pytest.mark.asyncio
async def test_move_item_all(inventory_service, test_data):
    """Test moving all of an item's quantity to another location."""
    laptop = test_data["items"]["laptop"]
    warehouse = test_data["locations"]["warehouse"]
    office = test_data["locations"]["office"]

    # Create inventory entry
    inventory_data = InventoryCreate(
        item_id=laptop.id,
        location_id=warehouse.id,
        quantity=3
    )
    await inventory_service.create_inventory_entry(inventory_data)

    # Move all items to office
    move_data = InventoryMove(
        from_location_id=warehouse.id,
        to_location_id=office.id,
        quantity=3
    )
    result = await inventory_service.move_item(laptop.id, move_data)

    # Verify destination entry
    assert result.location_id == office.id
    assert result.quantity == 3

    # Verify source entry no longer exists
    search_params = InventorySearch(item_id=laptop.id, location_id=warehouse.id)
    source_entries = await inventory_service.search_inventory(search_params)
    assert len(source_entries) == 0


@pytest.mark.asyncio
async def test_move_item_to_existing_location(inventory_service, test_data):
    """Test moving items to a location that already has some of that item."""
    laptop = test_data["items"]["laptop"]
    warehouse = test_data["locations"]["warehouse"]
    office = test_data["locations"]["office"]

    # Create inventory entries in both locations
    warehouse_data = InventoryCreate(
        item_id=laptop.id,
        location_id=warehouse.id,
        quantity=5
    )
    await inventory_service.create_inventory_entry(warehouse_data)

    office_data = InventoryCreate(
        item_id=laptop.id,
        location_id=office.id,
        quantity=2
    )
    await inventory_service.create_inventory_entry(office_data)

    # Move 3 items from warehouse to office
    move_data = InventoryMove(
        from_location_id=warehouse.id,
        to_location_id=office.id,
        quantity=3
    )
    result = await inventory_service.move_item(laptop.id, move_data)

    # Verify office now has 5 items (2 + 3)
    assert result.location_id == office.id
    assert result.quantity == 5

    # Verify warehouse has 2 items left (5 - 3)
    search_params = InventorySearch(item_id=laptop.id, location_id=warehouse.id)
    warehouse_entries = await inventory_service.search_inventory(search_params)
    assert len(warehouse_entries) == 1
    assert warehouse_entries[0].quantity == 2


@pytest.mark.asyncio
async def test_get_item_locations(inventory_service, test_data):
    """Test getting all locations where an item is stored."""
    laptop = test_data["items"]["laptop"]
    warehouse = test_data["locations"]["warehouse"]
    office = test_data["locations"]["office"]

    # Create inventory entries in multiple locations
    warehouse_data = InventoryCreate(
        item_id=laptop.id,
        location_id=warehouse.id,
        quantity=3
    )
    await inventory_service.create_inventory_entry(warehouse_data)

    office_data = InventoryCreate(
        item_id=laptop.id,
        location_id=office.id,
        quantity=1
    )
    await inventory_service.create_inventory_entry(office_data)

    # Get all locations for laptop
    locations = await inventory_service.get_item_locations(laptop.id)

    assert len(locations) == 2
    location_ids = [loc.location_id for loc in locations]
    assert warehouse.id in location_ids
    assert office.id in location_ids

    # Should be ordered by quantity desc
    assert locations[0].quantity >= locations[1].quantity


@pytest.mark.asyncio
async def test_get_location_items(inventory_service, test_data):
    """Test getting all items in a location."""
    laptop = test_data["items"]["laptop"]
    mouse = test_data["items"]["mouse"]
    warehouse = test_data["locations"]["warehouse"]

    # Create inventory entries for multiple items in warehouse
    laptop_data = InventoryCreate(
        item_id=laptop.id,
        location_id=warehouse.id,
        quantity=2
    )
    await inventory_service.create_inventory_entry(laptop_data)

    mouse_data = InventoryCreate(
        item_id=mouse.id,
        location_id=warehouse.id,
        quantity=5
    )
    await inventory_service.create_inventory_entry(mouse_data)

    # Get all items in warehouse
    items = await inventory_service.get_location_items(warehouse.id)

    assert len(items) == 2
    item_ids = [item.item_id for item in items]
    assert laptop.id in item_ids
    assert mouse.id in item_ids


@pytest.mark.asyncio
async def test_get_inventory_summary(inventory_service, test_data):
    """Test getting overall inventory summary statistics."""
    laptop = test_data["items"]["laptop"]
    mouse = test_data["items"]["mouse"]
    book = test_data["items"]["book"]
    warehouse = test_data["locations"]["warehouse"]
    office = test_data["locations"]["office"]

    # Create various inventory entries
    entries = [
        InventoryCreate(item_id=laptop.id, location_id=warehouse.id, quantity=2),
        InventoryCreate(item_id=mouse.id, location_id=warehouse.id, quantity=5),
        InventoryCreate(item_id=book.id, location_id=office.id, quantity=3),
    ]

    for entry in entries:
        await inventory_service.create_inventory_entry(entry)

    # Get summary
    summary = await inventory_service.get_inventory_summary()

    assert summary.total_items == 3  # 3 unique items
    assert summary.total_quantity == 10  # 2 + 5 + 3
    assert summary.total_locations == 2  # warehouse and office
    
    # Total value: (1500*2) + (25*5) + (15*3) = 3000 + 125 + 45 = 3170
    assert summary.total_value == 3170.0

    # Check location breakdown
    assert len(summary.by_location) == 2
    location_names = [loc["location_name"] for loc in summary.by_location]
    assert "Warehouse" in location_names
    assert "Office" in location_names

    # Check item type breakdown
    assert len(summary.by_item_type) == 2  # electronics and books
    type_names = [t["item_type"] for t in summary.by_item_type]
    assert "electronics" in type_names
    assert "books" in type_names


@pytest.mark.asyncio
async def test_bulk_create_inventory(inventory_service, test_data):
    """Test bulk creating multiple inventory entries."""
    laptop = test_data["items"]["laptop"]
    mouse = test_data["items"]["mouse"]
    warehouse = test_data["locations"]["warehouse"]
    office = test_data["locations"]["office"]

    operations = [
        InventoryCreate(item_id=laptop.id, location_id=warehouse.id, quantity=1),
        InventoryCreate(item_id=mouse.id, location_id=office.id, quantity=2),
    ]

    bulk_data = InventoryBulkOperation(operations=operations)
    results = await inventory_service.bulk_create_inventory(bulk_data)

    assert len(results) == 2
    assert results[0].item_id == laptop.id
    assert results[0].location_id == warehouse.id
    assert results[1].item_id == mouse.id
    assert results[1].location_id == office.id


@pytest.mark.asyncio
async def test_bulk_create_inventory_validation_error(inventory_service, test_data):
    """Test bulk create with validation errors."""
    # Empty operations list
    bulk_data = InventoryBulkOperation(operations=[])
    
    with pytest.raises(ValueError, match="at least one operation"):
        await inventory_service.bulk_create_inventory(bulk_data)


@pytest.mark.asyncio
async def test_get_location_inventory_report(inventory_service, test_data):
    """Test generating location inventory report."""
    laptop = test_data["items"]["laptop"]
    mouse = test_data["items"]["mouse"]
    warehouse = test_data["locations"]["warehouse"]

    # Create inventory entries
    laptop_data = InventoryCreate(
        item_id=laptop.id,
        location_id=warehouse.id,
        quantity=2
    )
    await inventory_service.create_inventory_entry(laptop_data)

    mouse_data = InventoryCreate(
        item_id=mouse.id,
        location_id=warehouse.id,
        quantity=3
    )
    await inventory_service.create_inventory_entry(mouse_data)

    # Generate report
    report = await inventory_service.get_location_inventory_report(warehouse.id)

    assert report is not None
    assert report.location_id == warehouse.id
    assert report.location_name == "Warehouse"
    assert report.total_items == 2
    assert report.total_quantity == 5  # 2 + 3
    # Total value: (1500*2) + (25*3) = 3000 + 75 = 3075
    assert report.total_value == 3075.0
    assert len(report.items) == 2


@pytest.mark.asyncio
async def test_move_item_insufficient_quantity(inventory_service, test_data):
    """Test moving more items than available."""
    laptop = test_data["items"]["laptop"]
    warehouse = test_data["locations"]["warehouse"]
    office = test_data["locations"]["office"]

    # Create inventory entry with quantity 2
    inventory_data = InventoryCreate(
        item_id=laptop.id,
        location_id=warehouse.id,
        quantity=2
    )
    await inventory_service.create_inventory_entry(inventory_data)

    # Try to move 5 items (more than available)
    move_data = InventoryMove(
        from_location_id=warehouse.id,
        to_location_id=office.id,
        quantity=5
    )

    with pytest.raises(ValueError, match="Insufficient quantity"):
        await inventory_service.move_item(laptop.id, move_data)


@pytest.mark.asyncio
async def test_move_item_same_location_fails(inventory_service, test_data):
    """Test that moving to the same location fails validation."""
    laptop = test_data["items"]["laptop"]
    warehouse = test_data["locations"]["warehouse"]

    # Try to move to same location
    move_data = InventoryMove(
        from_location_id=warehouse.id,
        to_location_id=warehouse.id,
        quantity=1
    )

    with pytest.raises(ValueError, match="must be different"):
        await inventory_service.move_item(laptop.id, move_data)