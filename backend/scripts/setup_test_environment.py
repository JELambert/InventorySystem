#!/usr/bin/env python3
"""
Test Environment Setup Script for Home Inventory System

This script automatically sets up the environment for running tests.
Run this if diagnostic script shows issues or before running tests.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import List, Tuple


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"🔧 {title}")
    print(f"{'='*60}")


def print_result(action: str, success: bool, details: str = "") -> None:
    """Print an action result with colored output."""
    status = "✅ SUCCESS" if success else "❌ FAILED"
    print(f"{status} {action}")
    if details:
        print(f"    {details}")


def ensure_working_directory() -> bool:
    """Ensure we're in the correct working directory."""
    print_section("Working Directory Setup")

    current_dir = os.getcwd()
    print(f"Current directory: {current_dir}")

    # Check if we're already in the backend directory
    if os.path.exists("app") and os.path.exists("tests"):
        print_result("Directory Check", True, "Already in backend directory")
        return True

    # Try to find and change to backend directory
    backend_candidates = ["backend", "./backend", "../backend", "../../backend"]

    for candidate in backend_candidates:
        backend_path = Path(candidate)
        if backend_path.exists() and (backend_path / "app").exists():
            try:
                os.chdir(backend_path)
                print_result(
                    "Directory Change", True, f"Changed to {backend_path.absolute()}"
                )
                return True
            except Exception as e:
                print_result(
                    "Directory Change", False, f"Failed to change to {candidate}: {e}"
                )

    print_result(
        "Backend Directory", False, "Could not find or access backend directory"
    )
    print(
        "💡 Please manually navigate to the backend directory and run this script again"
    )
    return False


def setup_python_path() -> bool:
    """Set up Python path for imports."""
    print_section("Python Path Setup")

    current_dir = os.getcwd()

    # Add current directory to Python path if not already there
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
        print_result("Python Path", True, f"Added {current_dir} to Python path")
    else:
        print_result("Python Path", True, "Current directory already in Python path")

    # Test imports
    try:
        import app

        print_result("App Import", True, "Successfully imported app module")
        return True
    except ImportError as e:
        print_result("App Import", False, f"Could not import app module: {e}")
        return False


def check_virtual_environment() -> bool:
    """Check and provide guidance on virtual environment."""
    print_section("Virtual Environment Check")

    # Check if in virtual environment
    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )

    if in_venv:
        print_result("Virtual Environment", True, f"Active: {sys.executable}")
        return True
    else:
        print_result("Virtual Environment", False, "No virtual environment detected")
        print("\n💡 IMPORTANT: You should use a virtual environment!")
        print("To create and activate one:")
        print("    python -m venv venv")
        print("    source venv/bin/activate  # Linux/Mac")
        print("    venv\\Scripts\\activate     # Windows")
        print("Then run this script again.")
        return False


def install_dependencies() -> bool:
    """Install required dependencies."""
    print_section("Dependencies Installation")

    # Check if requirements file exists
    requirements_file = "requirements-dev.txt"
    if not os.path.exists(requirements_file):
        print_result("Requirements File", False, f"{requirements_file} not found")
        return False

    print_result("Requirements File", True, f"Found {requirements_file}")

    # Upgrade pip first
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
            check=True,
            capture_output=True,
        )
        print_result("Pip Upgrade", True, "pip upgraded successfully")
    except subprocess.CalledProcessError as e:
        print_result("Pip Upgrade", False, f"Failed to upgrade pip: {e}")

    # Install dependencies
    try:
        print("Installing dependencies...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", requirements_file],
            check=True,
            capture_output=True,
            text=True,
        )

        print_result("Dependencies Install", True, "All dependencies installed")
        return True

    except subprocess.CalledProcessError as e:
        print_result("Dependencies Install", False, f"Installation failed: {e}")
        if e.stdout:
            print(f"    stdout: {e.stdout[-200:]}")
        if e.stderr:
            print(f"    stderr: {e.stderr[-200:]}")
        return False


def setup_database_environment() -> bool:
    """Set up database environment."""
    print_section("Database Environment Setup")

    # Clean up any existing test databases
    test_databases = ["inventory.db", "test.db", "test_*.db"]

    cleaned = 0
    for pattern in test_databases:
        if "*" in pattern:
            # Handle wildcard patterns
            import glob

            for file in glob.glob(pattern):
                try:
                    os.remove(file)
                    cleaned += 1
                except Exception:
                    pass
        else:
            if os.path.exists(pattern):
                try:
                    os.remove(pattern)
                    cleaned += 1
                except Exception as e:
                    print_result(
                        "Database Cleanup", False, f"Could not remove {pattern}: {e}"
                    )

    if cleaned > 0:
        print_result("Database Cleanup", True, f"Removed {cleaned} old database files")
    else:
        print_result("Database Cleanup", True, "No cleanup needed")

    # Test database creation permissions
    test_db = "test_setup.db"
    try:
        import sqlite3

        conn = sqlite3.connect(test_db)
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()

        if os.path.exists(test_db):
            os.remove(test_db)
            print_result(
                "Database Permissions", True, "Can create and delete database files"
            )
            return True
        else:
            print_result("Database Permissions", False, "Database file was not created")
            return False

    except Exception as e:
        print_result("Database Permissions", False, f"Cannot create database: {e}")
        return False


def setup_pytest_configuration() -> bool:
    """Set up pytest configuration."""
    print_section("Pytest Configuration Setup")

    # Check if pytest.ini exists
    if os.path.exists("pytest.ini"):
        print_result("Pytest Config", True, "pytest.ini exists")
    else:
        print_result("Pytest Config", False, "pytest.ini not found")
        # Could create a default one here if needed

    # Test pytest import
    try:
        import pytest

        print_result("Pytest Import", True, f"pytest {pytest.__version__}")
    except ImportError:
        print_result("Pytest Import", False, "pytest not installed")
        return False

    # Test pytest-asyncio
    try:
        import pytest_asyncio

        print_result(
            "Pytest-Asyncio", True, f"pytest-asyncio {pytest_asyncio.__version__}"
        )
        return True
    except ImportError:
        print_result("Pytest-Asyncio", False, "pytest-asyncio not installed")
        return False


def run_basic_tests() -> bool:
    """Run basic import tests to verify setup."""
    print_section("Basic Functionality Test")

    try:
        # Test basic imports
        from app.database.base import Base, engine, check_connection
        from app.database.config import DatabaseConfig

        print_result("Module Imports", True, "All modules imported successfully")

        # Test basic database config
        db_url = DatabaseConfig.get_database_url()
        print_result("Database Config", True, f"Database URL: {db_url}")

        # Test async functionality
        import asyncio

        async def test_basic_async():
            return await check_connection()

        connection_works = asyncio.run(test_basic_async())
        print_result(
            "Database Connection", connection_works, "Async database connection test"
        )

        return connection_works

    except Exception as e:
        print_result("Basic Tests", False, f"Error: {e}")
        return False


def main() -> None:
    """Set up the test environment."""
    print("🔧 Home Inventory System - Test Environment Setup")
    print("This script will set up your environment for running tests.")

    steps = [
        ("Working Directory", ensure_working_directory),
        ("Python Path", setup_python_path),
        ("Virtual Environment", check_virtual_environment),
        ("Dependencies", install_dependencies),
        ("Database Environment", setup_database_environment),
        ("Pytest Configuration", setup_pytest_configuration),
        ("Basic Functionality", run_basic_tests),
    ]

    results = []
    for step_name, step_func in steps:
        print(f"\n⏳ Running: {step_name}")
        try:
            result = step_func()
            results.append((step_name, result))

            if not result:
                print(f"❌ {step_name} failed. Check the output above for details.")
                # Don't stop - continue with other steps

        except Exception as e:
            print(f"❌ {step_name} failed with exception: {e}")
            results.append((step_name, False))

    # Summary
    print_section("Setup Summary")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for step_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {step_name}")

    print(f"\nResults: {passed}/{total} steps successful")

    if passed == total:
        print("\n🎉 Environment setup complete! You can now run tests:")
        print("    python -m pytest tests/test_database_base.py -v")
        print("    python scripts/verify_step_1_2a.py")
    else:
        print("\n⚠️  Some setup steps failed. Please address the issues above.")
        print("💡 You can also try:")
        print(
            "    python scripts/diagnose_environment.py  # For more detailed diagnostics"
        )
        print(
            "    python scripts/run_tests_safe.py        # For automated test running"
        )


if __name__ == "__main__":
    main()
