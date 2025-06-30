#!/usr/bin/env python3
"""
Manual verification script for Step 1.2a: SQLAlchemy Base Setup

This script provides standalone testing of database functionality
without requiring pytest, for manual verification.
"""

import asyncio
import sys
import os
from typing import Dict, Any

# Add the parent directory to Python path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.base import (
    get_session,
    create_tables,
    drop_tables,
    check_connection,
    Base,
    engine,
)
from app.database.config import DatabaseConfig


def print_result(test_name: str, success: bool, details: str = "") -> None:
    """Print colored test result."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    if details:
        print(f"    {details}")


async def verify_database_connection() -> bool:
    """Verify database connection works."""
    print("\n=== Testing Database Connection ===")
    try:
        result = await check_connection()
        print_result(
            "Database Connection",
            result,
            "Successfully connected to SQLite database"
            if result
            else "Failed to connect",
        )
        return result
    except Exception as e:
        print_result("Database Connection", False, f"Exception: {e}")
        return False


async def verify_session_creation() -> bool:
    """Verify session factory works."""
    print("\n=== Testing Session Creation ===")
    try:
        session_created = False
        async for session in get_session():
            session_created = True
            session_type = type(session).__name__
            print_result(
                "Session Creation", True, f"Created session of type: {session_type}"
            )
            break

        if not session_created:
            print_result("Session Creation", False, "No session was created")
            return False
        return True
    except Exception as e:
        print_result("Session Creation", False, f"Exception: {e}")
        return False


async def verify_table_operations() -> bool:
    """Verify table creation and deletion works."""
    print("\n=== Testing Table Operations ===")
    try:
        # Create tables
        await create_tables()
        print_result("Table Creation", True, "Tables created successfully")

        # Verify connection still works
        connection_ok = await check_connection()
        if not connection_ok:
            print_result(
                "Post-Create Connection",
                False,
                "Connection failed after table creation",
            )
            return False
        print_result(
            "Post-Create Connection", True, "Connection works after table creation"
        )

        # Drop tables
        await drop_tables()
        print_result("Table Deletion", True, "Tables dropped successfully")

        # Verify connection still works
        connection_ok = await check_connection()
        if not connection_ok:
            print_result(
                "Post-Drop Connection", False, "Connection failed after table deletion"
            )
            return False
        print_result(
            "Post-Drop Connection", True, "Connection works after table deletion"
        )

        return True
    except Exception as e:
        print_result("Table Operations", False, f"Exception: {e}")
        return False


def verify_configuration() -> bool:
    """Verify configuration functions work."""
    print("\n=== Testing Configuration ===")
    try:
        # Test database URL
        db_url = DatabaseConfig.get_database_url()
        url_ok = isinstance(db_url, str) and "sqlite" in db_url.lower()
        print_result("Database URL", url_ok, f"URL: {db_url}")

        # Test engine config
        engine_config = DatabaseConfig.get_engine_config()
        engine_ok = isinstance(engine_config, dict) and "echo" in engine_config
        print_result(
            "Engine Config", engine_ok, f"Config keys: {list(engine_config.keys())}"
        )

        # Test session config
        session_config = DatabaseConfig.get_session_config()
        session_ok = (
            isinstance(session_config, dict) and "expire_on_commit" in session_config
        )
        print_result(
            "Session Config", session_ok, f"Config keys: {list(session_config.keys())}"
        )

        return url_ok and engine_ok and session_ok
    except Exception as e:
        print_result("Configuration", False, f"Exception: {e}")
        return False


def verify_base_setup() -> bool:
    """Verify SQLAlchemy Base is properly configured."""
    print("\n=== Testing SQLAlchemy Base ===")
    try:
        base_ok = Base is not None
        metadata_ok = hasattr(Base, "metadata")
        registry_ok = hasattr(Base, "registry")

        print_result("Base Exists", base_ok, f"Base type: {type(Base)}")
        print_result("Metadata Attribute", metadata_ok, "Base has metadata attribute")
        print_result("Registry Attribute", registry_ok, "Base has registry attribute")

        return base_ok and metadata_ok and registry_ok
    except Exception as e:
        print_result("Base Setup", False, f"Exception: {e}")
        return False


async def verify_database_file() -> bool:
    """Verify database file is created."""
    print("\n=== Testing Database File ===")
    try:
        # Create tables to ensure database file exists
        await create_tables()

        # Check if file exists
        db_file = "inventory.db"
        file_exists = os.path.exists(db_file)

        if file_exists:
            file_size = os.path.getsize(db_file)
            print_result(
                "Database File", True, f"File exists: {db_file} ({file_size} bytes)"
            )
        else:
            print_result("Database File", False, f"File not found: {db_file}")

        return file_exists
    except Exception as e:
        print_result("Database File", False, f"Exception: {e}")
        return False


async def main() -> None:
    """Run all verification tests."""
    print("🧪 Step 1.2a Verification: SQLAlchemy Base Setup")
    print("=" * 50)

    tests = [
        ("Database Connection", verify_database_connection()),
        ("Session Creation", verify_session_creation()),
        ("Table Operations", verify_table_operations()),
        ("Configuration", verify_configuration()),
        ("Base Setup", verify_base_setup()),
        ("Database File", verify_database_file()),
    ]

    results = []
    for test_name, test_coro in tests:
        if asyncio.iscoroutine(test_coro):
            result = await test_coro
        else:
            result = test_coro
        results.append((test_name, result))

    # Print summary
    print("\n" + "=" * 50)
    print("🏁 VERIFICATION SUMMARY")
    print("=" * 50)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All verifications PASSED! Step 1.2a is complete.")
        return True
    else:
        print("❌ Some verifications FAILED. Please check the errors above.")
        return False


if __name__ == "__main__":
    # Change to the backend directory if needed
    if not os.path.exists("app"):
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(backend_dir)

    success = asyncio.run(main())
    sys.exit(0 if success else 1)
