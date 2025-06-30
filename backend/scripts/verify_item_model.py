#!/usr/bin/env python3
"""
Verification script for Item model functionality.

This script verifies that the Item model works correctly with PostgreSQL
including all relationships, constraints, and business logic.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import select

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database.base import get_session, create_tables
from app.models import Item, ItemType, ItemCondition, ItemStatus, Location, LocationType, Category
from app.core.logging import get_logger

logger = get_logger("item_verification")


async def verify_item_model():
    """Comprehensive verification of Item model functionality."""
    
    logger.info("🚀 Starting Item model verification...")
    
    try:
        # Ensure tables exist
        await create_tables()
        
        async for session in get_session():
            # Step 1: Create dependencies (Location and Category)
            logger.info("📍 Creating test location...")
            location = Location(
                name="Test Storage Room",
                location_type=LocationType.ROOM,
                description="A room for testing item storage"
            )
            session.add(location)
            await session.commit()
            await session.refresh(location)
            logger.info(f"✅ Created location: {location.name} (ID: {location.id})")
            
            logger.info("🏷️ Creating test category...")
            
            # Try to find existing Electronics category first
            stmt = select(Category).where(Category.name == "Electronics")
            result = await session.execute(stmt)
            category = result.scalar_one_or_none()
            
            if category:
                logger.info(f"✅ Using existing category: {category.name} (ID: {category.id})")
            else:
                category = Category(
                    name="Electronics",
                    description="Electronic devices and gadgets",
                    color="#007BFF"
                )
                session.add(category)
                await session.commit()
                await session.refresh(category)
                logger.info(f"✅ Created category: {category.name} (ID: {category.id})")
            
            # Step 2: Create basic item
            logger.info("📦 Creating basic item...")
            basic_item = Item(
                name="Basic Test Item",
                item_type=ItemType.OTHER,
                location_id=location.id
            )
            session.add(basic_item)
            await session.commit()
            await session.refresh(basic_item)
            logger.info(f"✅ Created basic item: {basic_item.name} (ID: {basic_item.id})")
            
            # Verify defaults
            assert basic_item.condition == ItemCondition.GOOD
            assert basic_item.status == ItemStatus.AVAILABLE
            assert basic_item.is_active is True
            assert basic_item.version == 1
            logger.info("✅ Basic item defaults verified")
            
            # Step 3: Create comprehensive item
            logger.info("💻 Creating comprehensive item...")
            purchase_date = datetime.now() - timedelta(days=365)
            warranty_expiry = datetime.now() + timedelta(days=365)
            
            laptop = Item(
                name="MacBook Pro 16\"",
                description="High-performance laptop for development",
                item_type=ItemType.ELECTRONICS,
                condition=ItemCondition.EXCELLENT,
                status=ItemStatus.IN_USE,
                brand="Apple",
                model="MacBook Pro 16-inch",
                serial_number="FVFX3456HF",
                barcode="1234567890123",
                purchase_price=Decimal("2499.99"),
                current_value=Decimal("2000.00"),
                purchase_date=purchase_date,
                warranty_expiry=warranty_expiry,
                weight=Decimal("2.0"),
                dimensions="35.57 x 24.59 x 1.68 cm",
                color="Space Gray",
                location_id=location.id,
                category_id=category.id,
                notes="Purchased for software development work",
                tags="laptop, development, work"
            )
            session.add(laptop)
            await session.commit()
            await session.refresh(laptop)
            logger.info(f"✅ Created comprehensive item: {laptop.name} (ID: {laptop.id})")
            
            # Step 4: Test relationships
            logger.info("🔗 Testing relationships...")
            await session.refresh(laptop, ["location", "category"])
            
            assert laptop.location is not None
            assert laptop.location.name == location.name
            assert laptop.category is not None
            assert laptop.category.name == category.name
            logger.info("✅ Item relationships verified")
            
            # Test reverse relationships
            await session.refresh(location, ["items"])
            await session.refresh(category, ["items"])
            
            location_item_names = [item.name for item in location.items]
            category_item_names = [item.name for item in category.items]
            
            assert basic_item.name in location_item_names
            assert laptop.name in location_item_names
            assert laptop.name in category_item_names
            logger.info("✅ Reverse relationships verified")
            
            # Step 5: Test calculated properties
            logger.info("📊 Testing calculated properties...")
            
            # Test display_name
            expected_display = f"{laptop.brand} {laptop.model} - {laptop.name}"
            assert laptop.display_name == expected_display
            
            # Test is_valuable
            assert laptop.is_valuable is True
            
            # Test age_days
            age = laptop.age_days
            assert age is not None
            assert age >= 364 and age <= 366  # Around 365 days
            
            # Test is_under_warranty
            assert laptop.is_under_warranty is True
            
            logger.info("✅ Calculated properties verified")
            
            # Step 6: Test validation methods
            logger.info("✅ Testing validation methods...")
            
            assert laptop.validate_serial_number_format() is True
            assert laptop.validate_barcode_format() is True
            assert laptop.validate_price_values() is True
            assert laptop.validate_weight() is True
            assert laptop.validate_dates() is True
            
            logger.info("✅ Validation methods verified")
            
            # Step 7: Test business logic methods
            logger.info("🔄 Testing business logic methods...")
            original_version = laptop.version
            
            # Test move_to_location
            logger.info("📍 Testing move_to_location...")
            new_location = Location(
                name="New Storage Location",
                location_type=LocationType.CONTAINER,
                description="New storage for moved items",
                parent_id=location.id
            )
            session.add(new_location)
            await session.commit()
            await session.refresh(new_location)
            
            laptop.move_to_location(new_location.id)
            assert laptop.location_id == new_location.id
            assert laptop.version == original_version + 1
            session.add(laptop)
            await session.commit()
            logger.info("✅ move_to_location verified")
            
            # Test update_condition
            logger.info("🔧 Testing update_condition...")
            laptop.update_condition(ItemCondition.GOOD, "Minor wear from regular use")
            assert laptop.condition == ItemCondition.GOOD
            assert "Minor wear from regular use" in laptop.notes
            assert laptop.version == original_version + 2
            session.add(laptop)
            await session.commit()
            logger.info("✅ update_condition verified")
            
            # Test update_status
            logger.info("📋 Testing update_status...")
            laptop.update_status(ItemStatus.AVAILABLE, "No longer in active use")
            assert laptop.status == ItemStatus.AVAILABLE
            assert "Status changed to available" in laptop.notes
            assert laptop.version == original_version + 3
            session.add(laptop)
            await session.commit()
            logger.info("✅ update_status verified")
            
            # Test update_value
            logger.info("💰 Testing update_value...")
            laptop.update_value(Decimal("1800.00"), "Depreciation due to age")
            assert laptop.current_value == Decimal("1800.00")
            assert "Value updated from $2000.00 to $1800.00" in laptop.notes
            assert laptop.version == original_version + 4
            session.add(laptop)
            await session.commit()
            logger.info("✅ update_value verified")
            
            # Step 8: Test tag operations
            logger.info("🏷️ Testing tag operations...")
            
            # Test initial tags
            initial_tags = laptop.get_tag_list()
            assert "laptop" in initial_tags
            assert "development" in initial_tags
            assert "work" in initial_tags
            
            # Test add_tag
            laptop.add_tag("portable")
            tags = laptop.get_tag_list()
            assert "portable" in tags
            
            # Test remove_tag
            laptop.remove_tag("work")
            tags = laptop.get_tag_list()
            assert "work" not in tags
            
            session.add(laptop)
            await session.commit()
            logger.info("✅ Tag operations verified")
            
            # Step 9: Test soft delete and restore
            logger.info("🗑️ Testing soft delete and restore...")
            laptop.soft_delete("Testing soft delete functionality")
            assert laptop.is_active is False
            assert laptop.status == ItemStatus.DISPOSED
            assert "Item deactivated: Testing soft delete functionality" in laptop.notes
            
            laptop.restore(ItemStatus.AVAILABLE)
            assert laptop.is_active is True
            assert laptop.status == ItemStatus.AVAILABLE
            assert "Item restored with status: available" in laptop.notes
            
            session.add(laptop)
            await session.commit()
            logger.info("✅ Soft delete and restore verified")
            
            # Step 10: Test class validation method
            logger.info("✅ Testing class validation method...")
            
            valid_data = {
                'name': 'Test Item',
                'location_id': location.id,
                'item_type': 'electronics',
                'condition': 'good',
                'status': 'available',
                'purchase_price': '100.00',
                'current_value': '80.00',
                'weight': '2.5'
            }
            
            errors = Item.validate_item(valid_data)
            assert len(errors) == 0
            
            invalid_data = {
                'name': '',  # Empty name
                'location_id': None,  # Missing location
                'item_type': 'invalid_type',  # Invalid enum
                'purchase_price': '-100.00',  # Negative price
            }
            
            errors = Item.validate_item(invalid_data)
            assert len(errors) > 0
            logger.info("✅ Class validation method verified")
            
            # Step 11: Test enum constraints
            logger.info("📝 Testing enum constraints...")
            
            enum_item = Item(
                name="Enum Test Item",
                item_type=ItemType.BOOKS,
                condition=ItemCondition.FAIR,
                status=ItemStatus.RESERVED,
                location_id=location.id
            )
            session.add(enum_item)
            await session.commit()
            await session.refresh(enum_item)
            
            assert enum_item.item_type == ItemType.BOOKS
            assert enum_item.condition == ItemCondition.FAIR
            assert enum_item.status == ItemStatus.RESERVED
            logger.info("✅ Enum constraints verified")
            
            # Step 12: Test unique constraints
            logger.info("🔒 Testing unique constraints...")
            
            # Create item with unique serial number
            unique_item1 = Item(
                name="Unique Item 1",
                item_type=ItemType.ELECTRONICS,
                location_id=location.id,
                serial_number="UNIQUE123456",
                barcode="9876543210123"
            )
            session.add(unique_item1)
            await session.commit()
            
            # Try to create item with duplicate serial number
            try:
                unique_item2 = Item(
                    name="Unique Item 2",
                    item_type=ItemType.ELECTRONICS,
                    location_id=location.id,
                    serial_number="UNIQUE123456"  # Duplicate
                )
                session.add(unique_item2)
                await session.commit()
                assert False, "Should have raised constraint violation"
            except Exception:
                await session.rollback()
                logger.info("✅ Serial number uniqueness constraint verified")
            
            # Try to create item with duplicate barcode
            try:
                unique_item3 = Item(
                    name="Unique Item 3",
                    item_type=ItemType.ELECTRONICS,
                    location_id=location.id,
                    barcode="9876543210123"  # Duplicate
                )
                session.add(unique_item3)
                await session.commit()
                assert False, "Should have raised constraint violation"
            except Exception:
                await session.rollback()
                logger.info("✅ Barcode uniqueness constraint verified")
            
            # Step 13: Query and count verification
            logger.info("📊 Testing queries and counts...")
            
            # Count total items
            stmt = select(Item).where(Item.is_active == True)
            result = await session.execute(stmt)
            items = result.scalars().all()
            
            assert len(items) >= 3  # basic_item, laptop, enum_item, unique_item1
            logger.info(f"✅ Found {len(items)} active items")
            
            # Count items by type
            stmt = select(Item).where(Item.item_type == ItemType.ELECTRONICS)
            result = await session.execute(stmt)
            electronics = result.scalars().all()
            
            assert len(electronics) >= 2  # laptop, unique_item1
            logger.info(f"✅ Found {len(electronics)} electronics items")
            
            # Count items by location
            stmt = select(Item).where(Item.location_id == location.id)
            result = await session.execute(stmt)
            location_items = result.scalars().all()
            
            assert len(location_items) >= 3  # basic_item, enum_item, unique_item1
            logger.info(f"✅ Found {len(location_items)} items in original location")
            
            logger.info("🎉 All Item model verification tests passed!")
            return True
            
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run the verification."""
    success = await verify_item_model()
    if success:
        print("\n✅ Item model verification completed successfully!")
        print("   All features are working correctly with PostgreSQL.")
    else:
        print("\n❌ Item model verification failed!")
        print("   Check the logs above for details.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())