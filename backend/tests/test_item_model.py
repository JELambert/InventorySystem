"""
Tests for the Item model.

Comprehensive test coverage for the Item model including:
- Model creation and validation
- Relationships with Location and Category
- Business logic methods
- Enum validations
- Property calculations
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import Base, engine, create_tables, drop_tables
from app.models import Item, ItemType, ItemCondition, ItemStatus, Location, LocationType, Category


async def _get_test_session():
    """Helper to get a test session with setup/teardown."""
    await create_tables()
    try:
        from app.database.base import async_session
        async with async_session() as session:
            yield session
    finally:
        await drop_tables()


async def _create_sample_location(session):
    """Create a sample location for testing."""
    location = Location(
        name="Test Room",
        location_type=LocationType.ROOM,
        description="A test room for items"
    )
    session.add(location)
    await session.commit()
    await session.refresh(location)
    return location


async def _create_sample_category(session):
    """Create a sample category for testing."""
    category = Category(
        name="Test Category",
        description="A test category",
        color="#FF0000"
    )
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category


@pytest.mark.asyncio
async def test_create_basic_item():
    """Test creating a basic item with required fields."""
    async for session in _get_test_session():
        # Items no longer have direct location_id field
        # Location relationship is through Inventory model
        
        item = Item(
            name="Basic Item",
            item_type=ItemType.OTHER
        )
        
        session.add(item)
        await session.commit()
        await session.refresh(item)
        
        assert item.id is not None
        assert item.name == "Basic Item"
        assert item.item_type == ItemType.OTHER
        assert item.condition == ItemCondition.GOOD  # Default
        assert item.status == ItemStatus.AVAILABLE  # Default
        assert item.is_active is True  # Default
        assert item.version == 1  # Default


@pytest.mark.asyncio
async def test_create_comprehensive_item():
    """Test creating an item with all fields populated."""
    async for session in _get_test_session():
        # Create dependencies
        location = await _create_sample_location(session)
        category = await _create_sample_category(session)
        
        purchase_date = datetime.now() - timedelta(days=30)
        warranty_expiry = datetime.now() + timedelta(days=335)
        
        item = Item(
            name="Premium Laptop",
            description="High-end gaming laptop",
            item_type=ItemType.ELECTRONICS,
            condition=ItemCondition.EXCELLENT,
            status=ItemStatus.IN_USE,
            brand="TechCorp",
            model="TC-Gaming-2023",
            serial_number="TC2023456789",
            barcode="1234567890123",
            purchase_price=Decimal("2499.99"),
            current_value=Decimal("2000.00"),
            purchase_date=purchase_date,
            warranty_expiry=warranty_expiry,
            weight=Decimal("2.5"),
            dimensions="35x25x2 cm",
            color="Black",
            category_id=category.id,
            notes="Excellent condition gaming laptop",
            tags="gaming, laptop, high-end"
        )
        
        session.add(item)
        await session.commit()
        await session.refresh(item)
        
        assert item.name == "Premium Laptop"
        assert item.brand == "TechCorp"
        assert item.model == "TC-Gaming-2023"
        assert item.serial_number == "TC2023456789"
        assert item.barcode == "1234567890123"
        assert item.purchase_price == Decimal("2499.99")
        assert item.current_value == Decimal("2000.00")
        assert item.weight == Decimal("2.5")
        assert item.dimensions == "35x25x2 cm"
        assert item.color == "Black"
        assert item.category_id == category.id


@pytest.mark.asyncio
async def test_item_relationships():
    """Test relationships between Item, Location, and Category."""
    async for session in _get_test_session():
        # Create dependencies
        location = await _create_sample_location(session)
        category = await _create_sample_category(session)
        
        item = Item(
            name="Test Item",
            item_type=ItemType.ELECTRONICS,
            category_id=category.id
        )
        
        session.add(item)
        await session.commit()
        await session.refresh(item, ["category"])
        
        # Location relationship is now through Inventory model
        # Create inventory entry to establish location relationship
        from app.models import Inventory
        inventory = Inventory(
            item_id=item.id,
            location_id=location.id,
            quantity=1
        )
        session.add(inventory)
        await session.commit()
        
        # Test category relationship
        assert item.category is not None
        assert item.category.id == category.id
        assert item.category.name == category.name


def test_item_properties():
    """Test calculated properties."""
    # Create a mock item for testing properties (no database needed)
    item = Item(
        name="Test Laptop",
        item_type=ItemType.ELECTRONICS,
        brand="TestBrand",
        model="TB-2023",
        current_value=Decimal("800.00"),
        purchase_date=datetime.now() - timedelta(days=30)
    )
    
    # Test display_name
    expected_display = f"{item.brand} {item.model} - {item.name}"
    assert item.display_name == expected_display
    
    # Test is_valuable (current_value >= 100)
    assert item.is_valuable is True
    
    # Test age_days
    age = item.age_days
    assert age is not None
    assert age >= 29 and age <= 31  # Should be around 30 days


def test_item_validation_methods():
    """Test validation methods."""
    item = Item(name="Test", item_type=ItemType.OTHER)
    
    # Test validate_serial_number_format
    item.serial_number = "ABC123456"
    assert item.validate_serial_number_format() is True
    
    item.serial_number = "123"
    assert item.validate_serial_number_format() is True
    
    item.serial_number = None
    assert item.validate_serial_number_format() is True
    
    # Invalid serial number (too short)
    item.serial_number = "AB"
    assert item.validate_serial_number_format() is False


def test_barcode_validation():
    """Test barcode format validation."""
    item = Item(name="Test", item_type=ItemType.OTHER)
    
    # Valid barcodes
    valid_barcodes = ["12345678", "123456789012", "1234567890123", "12345678901234"]
    for barcode in valid_barcodes:
        item.barcode = barcode
        assert item.validate_barcode_format() is True
    
    item.barcode = None
    assert item.validate_barcode_format() is True
    
    # Invalid barcodes
    invalid_barcodes = ["1234567", "123456789012345", "ABC123456789", "12345"]
    for barcode in invalid_barcodes:
        item.barcode = barcode
        assert item.validate_barcode_format() is False


def test_price_validation():
    """Test price value validation."""
    item = Item(name="Test", item_type=ItemType.OTHER)
    
    # Valid prices
    item.purchase_price = Decimal("100.00")
    item.current_value = Decimal("80.00")
    assert item.validate_price_values() is True
    
    # Zero prices should be valid
    item.purchase_price = Decimal("0.00")
    item.current_value = Decimal("0.00")
    assert item.validate_price_values() is True
    
    # None values should be valid
    item.purchase_price = None
    item.current_value = None
    assert item.validate_price_values() is True
    
    # Negative prices should be invalid
    item.purchase_price = Decimal("-10.00")
    assert item.validate_price_values() is False
    
    item.purchase_price = Decimal("100.00")
    item.current_value = Decimal("-5.00")
    assert item.validate_price_values() is False


def test_business_logic_methods():
    """Test business logic methods."""
    item = Item(
        name="Test Item",
        item_type=ItemType.OTHER,
        current_value=Decimal("100.00")
    )
    original_version = item.version
    
    # Test move_to_location method needs redesign
    # as Item doesn't have direct location_id anymore
    # This would be handled through Inventory service
    
    # Test update_condition
    item.update_condition(ItemCondition.FAIR, "Showing signs of wear")
    assert item.condition == ItemCondition.FAIR
    assert "Showing signs of wear" in item.notes
    assert item.version == original_version + 1
    
    # Test update_status
    item.update_status(ItemStatus.LOANED, "Loaned to colleague")
    assert item.status == ItemStatus.LOANED
    assert "Status changed to loaned" in item.notes
    assert item.version == original_version + 2
    
    # Test update_value
    item.update_value(Decimal("70.00"), "Market depreciation")
    assert item.current_value == Decimal("70.00")
    assert "Value updated from" in item.notes
    assert item.version == original_version + 3


def test_soft_delete_and_restore():
    """Test soft delete and restore functionality."""
    item = Item(
        name="Test Item",
        item_type=ItemType.OTHER
    )
    original_version = item.version
    
    # Test soft delete
    item.soft_delete("No longer needed")
    assert item.is_active is False
    assert item.status == ItemStatus.DISPOSED
    assert "Item deactivated: No longer needed" in item.notes
    assert item.version == original_version + 1
    
    # Test restore
    item.restore(ItemStatus.AVAILABLE)
    assert item.is_active is True
    assert item.status == ItemStatus.AVAILABLE
    assert "Item restored with status: available" in item.notes
    assert item.version == original_version + 2


def test_tag_operations():
    """Test tag management methods."""
    item = Item(
        name="Test Item",
        item_type=ItemType.OTHER
    )
    
    # Initially no tags
    assert item.get_tag_list() == []
    
    # Add tags
    item.add_tag("electronics")
    item.add_tag("laptop")
    item.add_tag("work")
    
    tags = item.get_tag_list()
    assert "electronics" in tags
    assert "laptop" in tags
    assert "work" in tags
    assert len(tags) == 3
    
    # Remove a tag
    item.remove_tag("work")
    tags = item.get_tag_list()
    assert "work" not in tags
    assert len(tags) == 2
    
    # Adding duplicate tag should not create duplicates
    item.add_tag("electronics")
    tags = item.get_tag_list()
    assert tags.count("electronics") == 1


def test_item_validate_class_method():
    """Test the class method for item validation."""
    # Valid item data (location_id removed as it's not part of Item model)
    valid_data = {
        'name': 'Test Item',
        'item_type': 'electronics',
        'condition': 'good',
        'status': 'available',
        'purchase_price': '100.00',
        'current_value': '80.00',
        'weight': '2.5'
    }
    
    errors = Item.validate_item(valid_data)
    assert len(errors) == 0
    
    # Invalid item data
    invalid_data = {
        'name': '',  # Empty name
        'item_type': 'invalid_type',  # Invalid enum
        'condition': 'invalid_condition',  # Invalid enum
        'purchase_price': '-100.00',  # Negative price
        'weight': '-5.0'  # Negative weight
    }
    
    errors = Item.validate_item(invalid_data)
    assert len(errors) > 0
    assert any("name is required" in error for error in errors)
    assert any("Invalid item type" in error for error in errors)
    assert any("Invalid condition" in error for error in errors)
    assert any("cannot be negative" in error for error in errors)


@pytest.mark.asyncio
async def test_enum_constraints():
    """Test that enum constraints work properly in the database."""
    async for session in _get_test_session():
        location = await _create_sample_location(session)
        
        # Test valid enums
        item = Item(
            name="Test Item",
            item_type=ItemType.ELECTRONICS,
            condition=ItemCondition.EXCELLENT,
            status=ItemStatus.AVAILABLE
        )
        
        session.add(item)
        await session.commit()
        await session.refresh(item)
        
        assert item.item_type == ItemType.ELECTRONICS
        assert item.condition == ItemCondition.EXCELLENT
        assert item.status == ItemStatus.AVAILABLE


@pytest.mark.asyncio
async def test_unique_constraints():
    """Test unique constraints on serial number and barcode."""
    async for session in _get_test_session():
        location = await _create_sample_location(session)
        
        # Create first item with serial number and barcode
        item1 = Item(
            name="Item 1",
            item_type=ItemType.ELECTRONICS,
            serial_number="UNIQUE123",
            barcode="1234567890123"
        )
        
        session.add(item1)
        await session.commit()
        
        # Try to create second item with same serial number
        item2 = Item(
            name="Item 2",
            item_type=ItemType.ELECTRONICS,
            serial_number="UNIQUE123"  # Same serial number
        )
        
        session.add(item2)
        
        with pytest.raises(Exception):  # Should raise integrity error
            await session.commit()
        
        await session.rollback()
        
        # Try to create third item with same barcode  
        item3 = Item(
            name="Item 3",
            item_type=ItemType.ELECTRONICS,
            barcode="1234567890123"  # Same barcode
        )
        
        session.add(item3)
        
        with pytest.raises(Exception):  # Should raise integrity error
            await session.commit()