#!/usr/bin/env python3
"""
Manual Verification Script for Step 1.2b: Location Model Core

This script validates that the Location model is working correctly with:
- Basic location creation and validation
- Hierarchical relationships (parent/child)
- Location types and path generation
- Self-referential relationship functionality
"""

import asyncio
import sys
import os

# Add the parent directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.base import create_tables, drop_tables, async_session
from app.models.location import Location, LocationType


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"🏠 {title}")
    print(f"{'='*60}")


def print_result(check: str, success: bool, details: str = "") -> None:
    """Print a check result with colored output."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {check}")
    if details:
        print(f"    {details}")


async def test_location_creation() -> bool:
    """Test basic location creation and field validation."""
    print_section("Location Creation Test")
    
    try:
        async with async_session() as session:
            # Create a simple location
            location = Location(
                name="Test House",
                description="A test house for validation",
                location_type=LocationType.HOUSE
            )
            
            session.add(location)
            await session.commit()
            await session.refresh(location)
            
            # Validate fields
            checks = [
                ("ID Generated", location.id is not None, f"ID: {location.id}"),
                ("Name Set", location.name == "Test House", f"Name: {location.name}"),
                ("Description Set", location.description == "A test house for validation", f"Description: {location.description}"),
                ("Location Type Set", location.location_type == LocationType.HOUSE, f"Type: {location.location_type.value}"),
                ("No Parent", location.parent_id is None, "Parent ID: None"),
                ("Created At Set", location.created_at is not None, f"Created: {location.created_at}"),
                ("Updated At Set", location.updated_at is not None, f"Updated: {location.updated_at}")
            ]
            
            all_passed = True
            for check_name, passed, detail in checks:
                print_result(check_name, passed, detail)
                if not passed:
                    all_passed = False
            
            return all_passed
            
    except Exception as e:
        print_result("Location Creation", False, f"Exception: {e}")
        return False


async def test_location_types() -> bool:
    """Test all location type enum values."""
    print_section("Location Types Test")
    
    try:
        async with async_session() as session:
            # Test all location types
            locations = [
                ("Main House", LocationType.HOUSE),
                ("Living Room", LocationType.ROOM),
                ("Storage Box", LocationType.CONTAINER),
                ("Top Shelf", LocationType.SHELF)
            ]
            
            created_locations = []
            for name, loc_type in locations:
                location = Location(name=name, location_type=loc_type)
                session.add(location)
                created_locations.append((name, loc_type, location))
            
            await session.commit()
            
            all_passed = True
            for name, expected_type, location in created_locations:
                await session.refresh(location)
                passed = location.location_type == expected_type
                print_result(f"Create {expected_type.value}", passed, f"{name} - ID: {location.id}")
                if not passed:
                    all_passed = False
            
            return all_passed
            
    except Exception as e:
        print_result("Location Types", False, f"Exception: {e}")
        return False


async def test_string_representations() -> bool:
    """Test __str__ and __repr__ methods."""
    print_section("String Representations Test")
    
    try:
        async with async_session() as session:
            location = Location(name="Kitchen", location_type=LocationType.ROOM)
            session.add(location)
            await session.commit()
            await session.refresh(location)
            
            str_repr = str(location)
            repr_repr = repr(location)
            
            str_expected = "Kitchen (room)"
            repr_expected = f"<Location(id={location.id}, name='Kitchen', type='room')>"
            
            checks = [
                ("String Representation", str_repr == str_expected, f"Got: {str_repr}"),
                ("Repr Representation", repr_repr == repr_expected, f"Got: {repr_repr}")
            ]
            
            all_passed = True
            for check_name, passed, detail in checks:
                print_result(check_name, passed, detail)
                if not passed:
                    all_passed = False
            
            return all_passed
            
    except Exception as e:
        print_result("String Representations", False, f"Exception: {e}")
        return False


async def test_hierarchical_relationships() -> bool:
    """Test parent-child relationships."""
    print_section("Hierarchical Relationships Test")
    
    try:
        async with async_session() as session:
            # Create parent
            house = Location(name="Family House", location_type=LocationType.HOUSE)
            session.add(house)
            await session.commit()
            await session.refresh(house)
            
            # Create child
            room = Location(
                name="Master Bedroom", 
                location_type=LocationType.ROOM, 
                parent_id=house.id
            )
            session.add(room)
            await session.commit()
            await session.refresh(room)
            
            # Refresh relationships
            await session.refresh(house, ['children'])
            await session.refresh(room, ['parent'])
            
            checks = [
                ("Parent ID Set", room.parent_id == house.id, f"Room parent_id: {room.parent_id}"),
                ("Parent Relationship", room.parent == house, f"Room parent: {room.parent}"),
                ("Child in Parent", room in house.children, f"House children: {len(house.children)}"),
                ("Children Count", len(house.children) == 1, f"Expected 1, got: {len(house.children)}")
            ]
            
            all_passed = True
            for check_name, passed, detail in checks:
                print_result(check_name, passed, detail)
                if not passed:
                    all_passed = False
            
            return all_passed
            
    except Exception as e:
        print_result("Hierarchical Relationships", False, f"Exception: {e}")
        return False


async def test_full_path_generation() -> bool:
    """Test full path generation for nested locations."""
    print_section("Full Path Generation Test")
    
    try:
        async with async_session() as session:
            # Create hierarchy: House -> Room -> Container -> Shelf
            house = Location(name="My House", location_type=LocationType.HOUSE)
            session.add(house)
            await session.commit()
            await session.refresh(house)
            
            room = Location(
                name="Office", 
                location_type=LocationType.ROOM, 
                parent_id=house.id
            )
            session.add(room)
            await session.commit()
            await session.refresh(room)
            
            container = Location(
                name="Desk",
                location_type=LocationType.CONTAINER,
                parent_id=room.id
            )
            session.add(container)
            await session.commit()
            await session.refresh(container)
            
            shelf = Location(
                name="Top Drawer",
                location_type=LocationType.SHELF,
                parent_id=container.id
            )
            session.add(shelf)
            await session.commit()
            await session.refresh(shelf)
            
            # Test full paths
            paths = [
                (house, "My House"),
                (room, "My House/Office"),
                (container, "My House/Office/Desk"),
                (shelf, "My House/Office/Desk/Top Drawer")
            ]
            
            all_passed = True
            for location, expected_path in paths:
                actual_path = location.full_path
                passed = actual_path == expected_path
                print_result(f"Path for {location.name}", passed, f"Expected: {expected_path}, Got: {actual_path}")
                if not passed:
                    all_passed = False
            
            return all_passed
            
    except Exception as e:
        print_result("Full Path Generation", False, f"Exception: {e}")
        return False


async def test_depth_calculation() -> bool:
    """Test depth calculation for hierarchical locations."""
    print_section("Depth Calculation Test")
    
    try:
        async with async_session() as session:
            # Create hierarchy
            house = Location(name="House", location_type=LocationType.HOUSE)
            session.add(house)
            await session.commit()
            await session.refresh(house)
            
            room = Location(
                name="Room", 
                location_type=LocationType.ROOM, 
                parent_id=house.id
            )
            session.add(room)
            await session.commit()
            await session.refresh(room)
            
            container = Location(
                name="Container",
                location_type=LocationType.CONTAINER,
                parent_id=room.id
            )
            session.add(container)
            await session.commit()
            await session.refresh(container)
            
            # Test depths
            depths = [
                (house, 0),
                (room, 1), 
                (container, 2)
            ]
            
            all_passed = True
            for location, expected_depth in depths:
                actual_depth = location.depth
                passed = actual_depth == expected_depth
                print_result(f"Depth for {location.name}", passed, f"Expected: {expected_depth}, Got: {actual_depth}")
                if not passed:
                    all_passed = False
            
            return all_passed
            
    except Exception as e:
        print_result("Depth Calculation", False, f"Exception: {e}")
        return False


async def test_ancestor_descendant_methods() -> bool:
    """Test ancestor and descendant relationship methods."""
    print_section("Ancestor/Descendant Methods Test")
    
    try:
        async with async_session() as session:
            # Create hierarchy
            house = Location(name="House", location_type=LocationType.HOUSE)
            session.add(house)
            await session.commit()
            await session.refresh(house)
            
            room = Location(
                name="Room", 
                location_type=LocationType.ROOM, 
                parent_id=house.id
            )
            session.add(room)
            await session.commit()
            await session.refresh(room)
            
            container = Location(
                name="Container",
                location_type=LocationType.CONTAINER,
                parent_id=room.id
            )
            session.add(container)
            await session.commit()
            await session.refresh(container)
            
            # Test ancestor relationships
            ancestor_tests = [
                ("House ancestor of Room", house.is_ancestor_of(room), True),
                ("House ancestor of Container", house.is_ancestor_of(container), True),
                ("Room ancestor of Container", room.is_ancestor_of(container), True),
                ("Room NOT ancestor of House", room.is_ancestor_of(house), False),
                ("Container NOT ancestor of House", container.is_ancestor_of(house), False)
            ]
            
            # Test descendant relationships
            descendant_tests = [
                ("Room descendant of House", room.is_descendant_of(house), True),
                ("Container descendant of House", container.is_descendant_of(house), True),
                ("Container descendant of Room", container.is_descendant_of(room), True),
                ("House NOT descendant of Room", house.is_descendant_of(room), False),
                ("House NOT descendant of Container", house.is_descendant_of(container), False)
            ]
            
            all_passed = True
            for test_name, actual, expected in ancestor_tests + descendant_tests:
                passed = actual == expected
                print_result(test_name, passed, f"Expected: {expected}, Got: {actual}")
                if not passed:
                    all_passed = False
            
            return all_passed
            
    except Exception as e:
        print_result("Ancestor/Descendant Methods", False, f"Exception: {e}")
        return False


async def test_get_root_method() -> bool:
    """Test getting the root location in a hierarchy."""
    print_section("Get Root Method Test")
    
    try:
        async with async_session() as session:
            # Create hierarchy
            house = Location(name="Root House", location_type=LocationType.HOUSE)
            session.add(house)
            await session.commit()
            await session.refresh(house)
            
            room = Location(
                name="Room", 
                location_type=LocationType.ROOM, 
                parent_id=house.id
            )
            session.add(room)
            await session.commit()
            await session.refresh(room)
            
            container = Location(
                name="Container",
                location_type=LocationType.CONTAINER,
                parent_id=room.id
            )
            session.add(container)
            await session.commit()
            await session.refresh(container)
            
            # Test get_root method
            root_tests = [
                ("House root is itself", house.get_root() == house),
                ("Room root is House", room.get_root() == house),
                ("Container root is House", container.get_root() == house)
            ]
            
            all_passed = True
            for test_name, passed in root_tests:
                print_result(test_name, passed, f"Root: {house.name}")
                if not passed:
                    all_passed = False
            
            return all_passed
            
    except Exception as e:
        print_result("Get Root Method", False, f"Exception: {e}")
        return False


async def main() -> None:
    """Run all verification tests."""
    print("🏠 Location Model Verification - Step 1.2b")
    print("This script validates the Location model functionality.")
    
    # Set up database
    print_section("Database Setup")
    try:
        await create_tables()
        print_result("Create Tables", True, "Database tables created successfully")
    except Exception as e:
        print_result("Create Tables", False, f"Exception: {e}")
        return
    
    # Run all tests
    tests = [
        ("Location Creation", test_location_creation),
        ("Location Types", test_location_types),
        ("String Representations", test_string_representations),
        ("Hierarchical Relationships", test_hierarchical_relationships),
        ("Full Path Generation", test_full_path_generation),
        ("Depth Calculation", test_depth_calculation),
        ("Ancestor/Descendant Methods", test_ancestor_descendant_methods),
        ("Get Root Method", test_get_root_method)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n⏳ Running: {test_name}")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print_result(test_name, False, f"Unexpected error: {e}")
            results.append((test_name, False))
    
    # Clean up database
    print_section("Database Cleanup")
    try:
        await drop_tables()
        print_result("Drop Tables", True, "Database tables dropped successfully")
    except Exception as e:
        print_result("Drop Tables", False, f"Exception: {e}")
    
    # Summary
    print_section("Verification Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Location model tests passed! Step 1.2b is complete.")
        print("\nThe Location model supports:")
        print("• Hierarchical structure (House → Room → Container → Shelf)")
        print("• Self-referential parent/child relationships")
        print("• Full path generation and depth calculation")
        print("• Ancestor/descendant relationship methods")
        print("• All location type enums")
        print("• Proper string representations")
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        print("💡 Common issues:")
        print("• Database connection problems")
        print("• SQLAlchemy relationship configuration")
        print("• Model field validation")


if __name__ == "__main__":
    asyncio.run(main())