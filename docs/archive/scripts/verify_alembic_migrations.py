#!/usr/bin/env python3
"""
Verification Script for Alembic Migration System

This script validates:
- Alembic configuration and setup
- Migration generation and application
- Database schema correctness after migration
- Migration rollback functionality
"""

import asyncio
import sys
import os
import tempfile
import shutil
import subprocess
from pathlib import Path

# Add the parent directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.logging import LoggingConfig
from app.database.base import create_tables, drop_tables, async_session, engine
from app.models.location import Location, LocationType


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"🔧 {title}")
    print(f"{'='*60}")


def print_result(check: str, success: bool, details: str = "") -> None:
    """Print a check result with colored output."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {check}")
    if details:
        print(f"    {details}")


def run_alembic_command(command: list, description: str) -> tuple[bool, str]:
    """Run an alembic command and return success status and output."""
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=True, cwd=os.getcwd()
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr or e.stdout}"
    except Exception as e:
        return False, f"Exception: {str(e)}"


async def test_alembic_configuration() -> bool:
    """Test Alembic configuration and basic commands."""
    print_section("Alembic Configuration Test")
    
    try:
        # Test alembic current
        success, output = run_alembic_command(["alembic", "current"], "Check current revision")
        print_result("Alembic Current Command", success, output.strip() if success else output)
        
        if not success:
            return False
        
        # Test alembic history
        success, output = run_alembic_command(["alembic", "history"], "Check migration history")
        print_result("Alembic History Command", success, f"Found migration history" if success else output)
        
        if not success:
            return False
        
        # Test alembic show (current revision)
        success, output = run_alembic_command(["alembic", "show", "current"], "Show current revision")
        print_result("Alembic Show Command", success, "Current revision details retrieved" if success else output)
        
        return success
        
    except Exception as e:
        print_result("Alembic Configuration", False, f"Exception: {e}")
        return False


async def test_migration_rollback() -> bool:
    """Test migration rollback functionality."""
    print_section("Migration Rollback Test")
    
    try:
        # First, ensure we're at head
        success, output = run_alembic_command(["alembic", "upgrade", "head"], "Upgrade to head")
        print_result("Upgrade to Head", success, "At latest migration" if success else output)
        
        if not success:
            return False
        
        # Test downgrade to base
        success, output = run_alembic_command(["alembic", "downgrade", "base"], "Downgrade to base")
        print_result("Downgrade to Base", success, "Successfully rolled back" if success else output)
        
        if not success:
            return False
        
        # Verify we're at base
        success, output = run_alembic_command(["alembic", "current"], "Check current after downgrade")
        is_at_base = success and (not output.strip() or "current" not in output.lower())
        print_result("At Base Revision", is_at_base, "No current revision (at base)" if is_at_base else f"Output: {output.strip()}")
        
        # Upgrade back to head
        success, output = run_alembic_command(["alembic", "upgrade", "head"], "Re-upgrade to head")
        print_result("Re-upgrade to Head", success, "Back to latest migration" if success else output)
        
        return success and is_at_base
        
    except Exception as e:
        print_result("Migration Rollback", False, f"Exception: {e}")
        return False


async def test_database_schema_after_migration() -> bool:
    """Test that the database schema is correct after migration."""
    print_section("Database Schema Validation")
    
    try:
        # Test that we can create a location using the migrated schema
        async with async_session() as session:
            location = Location(
                name="Migration Test House",
                description="Test location created after migration",
                location_type=LocationType.HOUSE
            )
            
            session.add(location)
            await session.commit()
            await session.refresh(location)
            
            # Verify the location was created correctly
            checks = [
                ("Location ID Generated", location.id is not None, f"ID: {location.id}"),
                ("Location Name", location.name == "Migration Test House", f"Name: {location.name}"),
                ("Location Type", location.location_type == LocationType.HOUSE, f"Type: {location.location_type.value}"),
                ("Created At Set", location.created_at is not None, f"Created: {location.created_at}"),
                ("Updated At Set", location.updated_at is not None, f"Updated: {location.updated_at}"),
            ]
            
            all_passed = True
            for check_name, passed, detail in checks:
                print_result(check_name, passed, detail)
                if not passed:
                    all_passed = False
            
            # Test hierarchical relationship
            room = Location(
                name="Migration Test Room",
                location_type=LocationType.ROOM,
                parent_id=location.id
            )
            session.add(room)
            await session.commit()
            await session.refresh(room)
            
            # Refresh relationships
            await session.refresh(location, ['children'])
            await session.refresh(room, ['parent'])
            
            hierarchy_checks = [
                ("Child Parent ID", room.parent_id == location.id, f"Parent ID: {room.parent_id}"),
                ("Parent Relationship", room.parent == location, "Parent relationship loaded"),
                ("Children Count", len(location.children) == 1, f"Children: {len(location.children)}"),
            ]
            
            for check_name, passed, detail in hierarchy_checks:
                print_result(check_name, passed, detail)
                if not passed:
                    all_passed = False
            
            return all_passed
            
    except Exception as e:
        print_result("Database Schema Validation", False, f"Exception: {e}")
        return False


async def test_migration_autogenerate() -> bool:
    """Test that autogenerate doesn't detect any changes (schema is in sync)."""
    print_section("Migration Autogenerate Test")
    
    try:
        # Create a test migration to see if any changes are detected
        success, output = run_alembic_command(
            ["alembic", "revision", "--autogenerate", "-m", "Test autogenerate - should be empty"],
            "Test autogenerate"
        )
        
        if not success:
            print_result("Autogenerate Command", False, output)
            return False
        
        # Check if the generated migration is empty (no changes detected)
        # Look for the generated file
        versions_dir = Path("alembic/versions")
        migration_files = list(versions_dir.glob("*test_autogenerate*.py"))
        
        if not migration_files:
            print_result("Migration File Generated", False, "No migration file found")
            return False
        
        latest_migration = migration_files[-1]
        
        # Read the migration file and check if upgrade/downgrade are empty
        with open(latest_migration, 'r') as f:
            content = f.read()
        
        # Check if upgrade function is empty (indicates no changes detected)
        is_empty = "pass" in content or "# ### end Alembic commands ###\n    pass" in content
        upgrade_section = content[content.find("def upgrade()"):content.find("def downgrade()")]
        has_operations = "op." in upgrade_section
        
        print_result("Schema in Sync", not has_operations, 
                    "No schema changes detected" if not has_operations else "Schema changes detected (unexpected)")
        
        # Clean up the test migration file
        latest_migration.unlink()
        print_result("Cleanup Test Migration", True, f"Removed {latest_migration.name}")
        
        return not has_operations
        
    except Exception as e:
        print_result("Migration Autogenerate", False, f"Exception: {e}")
        return False


async def main() -> None:
    """Main verification execution."""
    print("🔧 Alembic Migration System Verification")
    print("This script validates the Alembic migration infrastructure.")
    
    # Initialize logging
    LoggingConfig.setup_logging()
    
    # Track test results
    results = []
    
    print("⏳ Running: Alembic Configuration Test")
    results.append(await test_alembic_configuration())
    
    print("\n⏳ Running: Migration Rollback Test")
    results.append(await test_migration_rollback())
    
    print("\n⏳ Running: Database Schema Validation")
    results.append(await test_database_schema_after_migration())
    
    print("\n⏳ Running: Migration Autogenerate Test")
    results.append(await test_migration_autogenerate())
    
    # Print summary
    print_section("Verification Summary")
    passed = sum(results)
    total = len(results)
    
    test_names = [
        "Alembic Configuration",
        "Migration Rollback",
        "Database Schema Validation",
        "Migration Autogenerate"
    ]
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        print_result(name, result)
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Alembic migration system is working correctly!")
        print("\nMigration system features verified:")
        print("• Database migration generation and application")
        print("• Migration rollback functionality") 
        print("• Schema validation after migration")
        print("• Autogenerate change detection")
        print("• Proper integration with existing Location model")
    else:
        print(f"❌ {total - passed} test(s) failed. Please review the output above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())