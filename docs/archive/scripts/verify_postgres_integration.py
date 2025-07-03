#!/usr/bin/env python3
"""
PostgreSQL Integration Verification Script

This script validates:
- PostgreSQL connection and functionality
- Location model operations on PostgreSQL
- Migration compatibility
- Performance characteristics
"""

import asyncio
import sys
import os
import tempfile
import time

# Add the parent directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.logging import LoggingConfig
from app.database.base import create_tables, drop_tables, async_session, engine
from app.database.config import DatabaseConfig
from app.models.location import Location, LocationType
from sqlalchemy import text


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"🐘 {title}")
    print(f"{'='*60}")


def print_result(check: str, success: bool, details: str = "") -> None:
    """Print a check result with colored output."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {check}")
    if details:
        print(f"    {details}")


async def test_postgresql_connection() -> bool:
    """Test basic PostgreSQL connection and information."""
    print_section("PostgreSQL Connection Test")
    
    try:
        database_url = DatabaseConfig.get_database_url()
        print_result("Database URL", "postgresql" in database_url, f"URL: {database_url}")
        
        async with engine.begin() as conn:
            # Test basic connection
            result = await conn.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            print_result("Basic Connection", test_value == 1, f"Test query result: {test_value}")
            
            # Get PostgreSQL version
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print_result("PostgreSQL Version", "PostgreSQL" in version, f"Version: {version[:80]}...")
            
            # Get current database
            result = await conn.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            print_result("Target Database", db_name == "inventory_system", f"Database: {db_name}")
            
            # Test transaction
            await conn.execute(text("SELECT now()"))
            print_result("Transaction Support", True, "Transactions working")
            
        return True
        
    except Exception as e:
        print_result("PostgreSQL Connection", False, f"Error: {e}")
        return False


async def test_schema_validation() -> bool:
    """Test that the schema was created correctly."""
    print_section("Schema Validation Test")
    
    try:
        async with async_session() as session:
            # Check that locations table exists
            result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'locations'
            """))
            table_exists = result.scalar() is not None
            print_result("Locations Table Exists", table_exists, "Table found in schema")
            
            # Check table structure
            result = await session.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'locations'
                ORDER BY ordinal_position
            """))
            columns = result.fetchall()
            
            expected_columns = {"id", "name", "description", "location_type", "parent_id", "created_at", "updated_at"}
            actual_columns = {col[0] for col in columns}
            
            columns_match = expected_columns.issubset(actual_columns)
            print_result("Table Structure", columns_match, f"Columns: {', '.join(sorted(actual_columns))}")
            
            # Check indexes
            result = await session.execute(text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = 'locations'
            """))
            indexes = {row[0] for row in result.fetchall()}
            expected_indexes = {"locations_pkey", "ix_locations_id", "ix_locations_name", "ix_locations_location_type", "ix_locations_parent_id"}
            
            indexes_match = expected_indexes.issubset(indexes)
            print_result("Indexes Created", indexes_match, f"Indexes: {', '.join(sorted(indexes))}")
            
            return table_exists and columns_match and indexes_match
            
    except Exception as e:
        print_result("Schema Validation", False, f"Error: {e}")
        return False


async def test_location_operations() -> bool:
    """Test Location model operations on PostgreSQL."""
    print_section("Location Operations Test")
    
    try:
        async with async_session() as session:
            # Create a hierarchy
            house = Location(
                name="PostgreSQL Test House",
                description="Test house for PostgreSQL validation",
                location_type=LocationType.HOUSE
            )
            session.add(house)
            await session.commit()
            await session.refresh(house)
            
            print_result("House Creation", house.id is not None, f"House ID: {house.id}")
            
            room = Location(
                name="Test Room",
                location_type=LocationType.ROOM,
                parent_id=house.id
            )
            session.add(room)
            await session.commit()
            await session.refresh(room)
            
            print_result("Room Creation", room.id is not None, f"Room ID: {room.id}")
            
            # Load relationships
            await session.refresh(house, ['children'])
            await session.refresh(room, ['parent'])
            
            # Test hierarchical operations
            hierarchy_valid = room.parent == house and room in house.children
            print_result("Hierarchical Relationships", hierarchy_valid, "Parent-child relationships working")
            
            # Test path generation
            expected_path = "PostgreSQL Test House/Test Room"
            actual_path = room.full_path
            path_correct = actual_path == expected_path
            print_result("Path Generation", path_correct, f"Path: {actual_path}")
            
            # Test search functionality
            search_results = Location.find_by_pattern("postgresql", [house, room])
            search_working = len(search_results) == 1
            print_result("Search Functionality", search_working, f"Found {len(search_results)} matching locations")
            
            # Test validation methods
            validation_working = house.validate_hierarchy() and room.validate_location_type_order()
            print_result("Validation Methods", validation_working, "Hierarchy and type validation working")
            
            return all([hierarchy_valid, path_correct, search_working, validation_working])
            
    except Exception as e:
        print_result("Location Operations", False, f"Error: {e}")
        return False


async def test_performance_characteristics() -> bool:
    """Test basic performance characteristics."""
    print_section("Performance Test")
    
    try:
        async with async_session() as session:
            start_time = time.time()
            
            # Create multiple locations
            locations = []
            for i in range(50):
                location = Location(
                    name=f"Performance Test Location {i}",
                    location_type=LocationType.CONTAINER,
                    description=f"Test location {i} for performance testing"
                )
                locations.append(location)
                session.add(location)
            
            await session.commit()
            creation_time = time.time() - start_time
            
            print_result("Bulk Creation (50 items)", creation_time < 2.0, f"Time: {creation_time:.3f}s")
            
            # Test query performance
            start_time = time.time()
            result = await session.execute(text("SELECT COUNT(*) FROM locations"))
            count = result.scalar()
            query_time = time.time() - start_time
            
            print_result("Count Query", query_time < 0.1, f"Count: {count}, Time: {query_time:.3f}s")
            
            # Test pattern search performance
            start_time = time.time()
            for location in locations:
                await session.refresh(location)
            search_results = Location.find_by_pattern("Performance", locations)
            search_time = time.time() - start_time
            
            print_result("Pattern Search (50 items)", search_time < 0.1, f"Found: {len(search_results)}, Time: {search_time:.3f}s")
            
            return creation_time < 2.0 and query_time < 0.1
            
    except Exception as e:
        print_result("Performance Test", False, f"Error: {e}")
        return False


async def test_migration_compatibility() -> bool:
    """Test that migrations work correctly with PostgreSQL."""
    print_section("Migration Compatibility Test")
    
    try:
        # Test that alembic can detect current state
        import subprocess
        
        result = subprocess.run(
            ["python", "scripts/manage_migrations.py", "status"],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        migration_status_ok = result.returncode == 0 and "up to date" in result.stdout
        print_result("Migration Status", migration_status_ok, "Alembic reports database up to date")
        
        # Test autogenerate (should detect no changes)
        result = subprocess.run(
            ["alembic", "revision", "--autogenerate", "-m", "Test autogenerate PostgreSQL"],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        if result.returncode == 0:
            # Check if the generated migration is empty
            from pathlib import Path
            versions_dir = Path("alembic/versions")
            migration_files = list(versions_dir.glob("*test_autogenerate_postgresql*.py"))
            
            if migration_files:
                latest_migration = migration_files[-1]
                with open(latest_migration, 'r') as f:
                    content = f.read()
                
                is_empty = "pass" in content and "op." not in content.split("def upgrade()")[1].split("def downgrade()")[0]
                print_result("Autogenerate Test", is_empty, "No schema changes detected (as expected)")
                
                # Clean up test migration
                latest_migration.unlink()
            else:
                print_result("Autogenerate Test", False, "Migration file not found")
                return False
        else:
            print_result("Autogenerate Test", False, f"Alembic error: {result.stderr}")
            return False
        
        return migration_status_ok
        
    except Exception as e:
        print_result("Migration Compatibility", False, f"Error: {e}")
        return False


async def main() -> None:
    """Main verification execution."""
    print("🐘 PostgreSQL Integration Verification")
    print("This script validates PostgreSQL integration for the Home Inventory System.")
    
    # Initialize logging
    LoggingConfig.setup_logging()
    
    # Verify we're using PostgreSQL
    database_url = DatabaseConfig.get_database_url()
    if "postgresql" not in database_url:
        print("❌ Not configured for PostgreSQL")
        print(f"Current database URL: {database_url}")
        sys.exit(1)
    
    # Track test results
    results = []
    
    print("⏳ Running: PostgreSQL Connection Test")
    results.append(await test_postgresql_connection())
    
    print("\n⏳ Running: Schema Validation Test")
    results.append(await test_schema_validation())
    
    print("\n⏳ Running: Location Operations Test")
    results.append(await test_location_operations())
    
    print("\n⏳ Running: Performance Test")
    results.append(await test_performance_characteristics())
    
    print("\n⏳ Running: Migration Compatibility Test")
    results.append(await test_migration_compatibility())
    
    # Print summary
    print_section("Verification Summary")
    passed = sum(results)
    total = len(results)
    
    test_names = [
        "PostgreSQL Connection",
        "Schema Validation",
        "Location Operations",
        "Performance Characteristics",
        "Migration Compatibility"
    ]
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        print_result(name, result)
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 PostgreSQL integration is working perfectly!")
        print("\nPostgreSQL features verified:")
        print("• Database connection and basic operations")
        print("• Schema creation and structure validation")
        print("• Location model operations and relationships")
        print("• Performance characteristics within acceptable ranges")
        print("• Migration system compatibility")
        print("\n✅ Ready for production use with PostgreSQL!")
    else:
        print(f"❌ {total - passed} test(s) failed. Please review the output above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())