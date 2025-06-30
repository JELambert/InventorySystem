#!/usr/bin/env python3
"""
Environment Diagnostic Script for Home Inventory System

This script diagnoses common issues that prevent tests from running properly.
Run this first if you're experiencing test failures.
"""

import os
import sys
import subprocess
import sqlite3
import importlib
from pathlib import Path
from typing import List, Tuple, Dict, Any


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")


def print_result(check: str, success: bool, details: str = "") -> None:
    """Print a check result with colored output."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {check}")
    if details:
        print(f"    {details}")


def check_working_directory() -> bool:
    """Check if we're in the correct working directory."""
    print_section("Working Directory Check")

    current_dir = os.getcwd()
    print_result("Current Directory", True, f"{current_dir}")

    # Check if we're in the backend directory
    has_app_dir = os.path.exists("app")
    print_result("App Directory Exists", has_app_dir, "Looking for 'app' directory")

    has_tests_dir = os.path.exists("tests")
    print_result(
        "Tests Directory Exists", has_tests_dir, "Looking for 'tests' directory"
    )

    has_requirements = os.path.exists("requirements-dev.txt")
    print_result(
        "Requirements File Exists",
        has_requirements,
        "Looking for 'requirements-dev.txt'",
    )

    # If we're not in the right place, try to find it
    if not (has_app_dir and has_tests_dir):
        backend_path = Path(current_dir) / "backend"
        if backend_path.exists():
            print_result("Backend Directory Found", True, f"Found at: {backend_path}")
            print("💡 TIP: Run 'cd backend' before running tests")
            return False
        else:
            print_result(
                "Backend Directory Found", False, "Could not locate backend directory"
            )
            return False

    return has_app_dir and has_tests_dir and has_requirements


def check_python_path() -> bool:
    """Check if Python can import our modules."""
    print_section("Python Path and Imports")

    # Check if current directory is in Python path
    current_in_path = os.getcwd() in sys.path
    print_result(
        "Current Dir in Python Path", current_in_path, f"Current dir: {os.getcwd()}"
    )

    # Try to import our modules
    import_results = []
    modules_to_test = [
        "app",
        "app.main",
        "app.database",
        "app.database.base",
        "app.database.config",
    ]

    for module in modules_to_test:
        try:
            importlib.import_module(module)
            print_result(f"Import {module}", True, "Module imported successfully")
            import_results.append(True)
        except ImportError as e:
            print_result(f"Import {module}", False, f"ImportError: {e}")
            import_results.append(False)
        except Exception as e:
            print_result(f"Import {module}", False, f"Unexpected error: {e}")
            import_results.append(False)

    return all(import_results)


def check_virtual_environment() -> bool:
    """Check virtual environment status."""
    print_section("Virtual Environment Check")

    # Check if in virtual environment
    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )
    print_result(
        "Virtual Environment Active", in_venv, f"Python executable: {sys.executable}"
    )

    if not in_venv:
        print("💡 TIP: Activate virtual environment with:")
        print("    source venv/bin/activate  (Linux/Mac)")
        print("    venv\\Scripts\\activate     (Windows)")

    return in_venv


def check_dependencies() -> bool:
    """Check if required dependencies are installed."""
    print_section("Dependencies Check")

    required_packages = [
        ("fastapi", "0.104.1"),
        ("uvicorn", None),
        ("sqlalchemy", "2.0.23"),
        ("aiosqlite", "0.19.0"),
        ("pytest", "7.4.3"),
        ("pytest-asyncio", "0.21.1"),
    ]

    all_installed = True

    for package, expected_version in required_packages:
        try:
            module = importlib.import_module(package.replace("-", "_"))
            if hasattr(module, "__version__"):
                version = module.__version__
                version_match = expected_version is None or version == expected_version
                version_info = f"v{version}" + (
                    "" if version_match else f" (expected {expected_version})"
                )
                print_result(f"Package {package}", True, version_info)
                if not version_match:
                    all_installed = False
            else:
                print_result(f"Package {package}", True, "Installed (version unknown)")
        except ImportError:
            print_result(f"Package {package}", False, "Not installed")
            all_installed = False
        except Exception as e:
            print_result(f"Package {package}", False, f"Error: {e}")
            all_installed = False

    if not all_installed:
        print("\n💡 TIP: Install missing dependencies with:")
        print("    pip install -r requirements-dev.txt")

    return all_installed


def check_sqlite_functionality() -> bool:
    """Check if SQLite works properly."""
    print_section("SQLite Functionality Check")

    try:
        # Test basic SQLite
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        conn.close()

        sqlite_basic = result[0] == 1
        print_result("Basic SQLite", sqlite_basic, "In-memory database test")

        # Test file-based SQLite
        test_db = "test_diagnostic.db"
        if os.path.exists(test_db):
            os.remove(test_db)

        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE test (id INTEGER)")
        cursor.execute("INSERT INTO test (id) VALUES (1)")
        cursor.execute("SELECT id FROM test")
        result = cursor.fetchone()
        conn.close()

        file_sqlite = result[0] == 1
        print_result("File-based SQLite", file_sqlite, f"Created and tested {test_db}")

        # Cleanup
        if os.path.exists(test_db):
            os.remove(test_db)
            print_result("SQLite Cleanup", True, f"Removed {test_db}")

        return sqlite_basic and file_sqlite

    except Exception as e:
        print_result("SQLite Test", False, f"Error: {e}")
        return False


def check_async_functionality() -> bool:
    """Check if async/await works properly."""
    print_section("Async Functionality Check")

    try:
        import asyncio

        async def test_async():
            await asyncio.sleep(0.001)
            return "async_works"

        # Test basic async
        result = asyncio.run(test_async())
        basic_async = result == "async_works"
        print_result("Basic Async/Await", basic_async, "Simple async function test")

        # Test aiosqlite if available
        try:
            import aiosqlite

            async def test_aiosqlite():
                async with aiosqlite.connect(":memory:") as db:
                    await db.execute("SELECT 1")
                    async with db.execute("SELECT 1") as cursor:
                        result = await cursor.fetchone()
                        return result[0] == 1

            aiosqlite_result = asyncio.run(test_aiosqlite())
            print_result("AIOSQLite", aiosqlite_result, "Async SQLite test")

            return basic_async and aiosqlite_result

        except ImportError:
            print_result("AIOSQLite", False, "aiosqlite not installed")
            return False

    except Exception as e:
        print_result("Async Test", False, f"Error: {e}")
        return False


def check_database_permissions() -> bool:
    """Check database file creation permissions."""
    print_section("Database Permissions Check")

    try:
        test_file = "test_permissions.db"

        # Test file creation
        with open(test_file, "w") as f:
            f.write("test")

        file_create = os.path.exists(test_file)
        print_result("File Creation", file_create, f"Created {test_file}")

        # Test file write
        with open(test_file, "a") as f:
            f.write("append")

        # Test file read
        with open(test_file, "r") as f:
            content = f.read()

        file_rw = content == "testappend"
        print_result("File Read/Write", file_rw, "File read/write operations")

        # Test file deletion
        os.remove(test_file)
        file_delete = not os.path.exists(test_file)
        print_result("File Deletion", file_delete, f"Removed {test_file}")

        return file_create and file_rw and file_delete

    except Exception as e:
        print_result("Permission Test", False, f"Error: {e}")
        return False


def check_pytest_configuration() -> bool:
    """Check pytest configuration."""
    print_section("Pytest Configuration Check")

    try:
        # Check if pytest.ini exists
        pytest_ini = os.path.exists("pytest.ini")
        print_result("pytest.ini exists", pytest_ini, "Configuration file")

        # Try to import pytest
        import pytest

        print_result("Pytest Import", True, f"Version: {pytest.__version__}")

        # Check pytest-asyncio
        try:
            import pytest_asyncio

            print_result(
                "Pytest-Asyncio", True, f"Version: {pytest_asyncio.__version__}"
            )
            asyncio_plugin = True
        except ImportError:
            print_result("Pytest-Asyncio", False, "Plugin not installed")
            asyncio_plugin = False

        # Test pytest discovery
        if os.path.exists("tests"):
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pytest", "--collect-only", "tests/"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                discovery_ok = result.returncode == 0
                print_result(
                    "Test Discovery", discovery_ok, f"Found tests: {discovery_ok}"
                )

                if not discovery_ok:
                    print(f"    Error output: {result.stderr[:200]}...")

            except subprocess.TimeoutExpired:
                print_result("Test Discovery", False, "Timeout during discovery")
                discovery_ok = False
            except Exception as e:
                print_result("Test Discovery", False, f"Error: {e}")
                discovery_ok = False
        else:
            discovery_ok = False
            print_result("Test Discovery", False, "Tests directory not found")

        return pytest_ini and asyncio_plugin and discovery_ok

    except ImportError:
        print_result("Pytest Import", False, "Pytest not installed")
        return False
    except Exception as e:
        print_result("Pytest Check", False, f"Error: {e}")
        return False


def provide_recommendations(results: Dict[str, bool]) -> None:
    """Provide recommendations based on diagnostic results."""
    print_section("Recommendations")

    failed_checks = [check for check, passed in results.items() if not passed]

    if not failed_checks:
        print("🎉 All checks passed! Your environment should be ready for testing.")
        print("\nTry running tests with:")
        print("    python -m pytest tests/test_database_base.py -v")
        return

    print("❌ Some checks failed. Here's how to fix them:\n")

    if "working_directory" in failed_checks:
        print("📁 Working Directory Issues:")
        print("    - Make sure you're in the 'backend' directory")
        print("    - Run: cd backend")
        print("")

    if "python_path" in failed_checks:
        print("🐍 Python Path Issues:")
        print("    - Make sure you're in the backend directory")
        print("    - Try: export PYTHONPATH=.")
        print("    - Or run tests with: python -m pytest")
        print("")

    if "virtual_environment" in failed_checks:
        print("🔄 Virtual Environment Issues:")
        print("    - Create virtual environment: python -m venv venv")
        print("    - Activate it: source venv/bin/activate")
        print("    - Install dependencies: pip install -r requirements-dev.txt")
        print("")

    if "dependencies" in failed_checks:
        print("📦 Dependency Issues:")
        print("    - Install missing packages: pip install -r requirements-dev.txt")
        print("    - Upgrade pip: pip install --upgrade pip")
        print("    - Check virtual environment is activated")
        print("")

    if "sqlite_functionality" in failed_checks:
        print("🗄️ SQLite Issues:")
        print("    - Check file permissions in current directory")
        print("    - Try running from a different directory")
        print("    - Check disk space")
        print("")

    if "async_functionality" in failed_checks:
        print("⚡ Async Issues:")
        print("    - Install aiosqlite: pip install aiosqlite")
        print("    - Check Python version (3.7+ required)")
        print("    - Try: pip install --upgrade asyncio")
        print("")

    if "database_permissions" in failed_checks:
        print("🔒 Permission Issues:")
        print("    - Check write permissions in current directory")
        print("    - Try running as different user")
        print("    - Check if directory is read-only")
        print("")

    if "pytest_configuration" in failed_checks:
        print("🧪 Pytest Issues:")
        print("    - Install pytest-asyncio: pip install pytest-asyncio")
        print("    - Check pytest.ini configuration")
        print("    - Try: python -m pytest --version")
        print("")


def main() -> None:
    """Run all diagnostic checks."""
    print("🩺 Home Inventory System - Environment Diagnostics")
    print("This script will help identify why tests might be failing.")

    # Run all checks
    checks = {
        "working_directory": check_working_directory(),
        "python_path": check_python_path(),
        "virtual_environment": check_virtual_environment(),
        "dependencies": check_dependencies(),
        "sqlite_functionality": check_sqlite_functionality(),
        "async_functionality": check_async_functionality(),
        "database_permissions": check_database_permissions(),
        "pytest_configuration": check_pytest_configuration(),
    }

    # Provide recommendations
    provide_recommendations(checks)

    # Summary
    passed = sum(checks.values())
    total = len(checks)

    print_section("Summary")
    print(f"✅ Passed: {passed}/{total} checks")
    if passed == total:
        print("🚀 Environment is ready for testing!")
    else:
        print("⚠️  Environment needs attention. See recommendations above.")


if __name__ == "__main__":
    main()
