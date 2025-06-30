#!/usr/bin/env python3
"""
Safe Test Runner for Home Inventory System

This script runs diagnostics, sets up the environment, and then runs tests
with detailed error reporting and troubleshooting suggestions.
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any, Optional


def print_banner(title: str) -> None:
    """Print a banner with title."""
    print(f"\n{'='*80}")
    print(f"🧪 {title}")
    print(f"{'='*80}")


def print_step(step: str) -> None:
    """Print a step header."""
    print(f"\n🔄 {step}")
    print("-" * 60)


def run_script(script_name: str, description: str) -> tuple[bool, str, str]:
    """Run a Python script and return success, stdout, stderr."""
    print(f"Running {description}...")

    try:
        result = subprocess.run(
            [sys.executable, script_name], capture_output=True, text=True, timeout=120
        )

        success = result.returncode == 0
        return success, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        return False, "", "Script timed out after 120 seconds"
    except FileNotFoundError:
        return False, "", f"Script {script_name} not found"
    except Exception as e:
        return False, "", f"Unexpected error: {e}"


def run_pytest(test_path: str = "tests/test_database_base.py") -> tuple[bool, str, str]:
    """Run pytest with verbose output."""
    print(f"Running pytest on {test_path}...")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        success = result.returncode == 0
        return success, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        return False, "", "Pytest timed out after 60 seconds"
    except FileNotFoundError:
        return False, "", "pytest command not found"
    except Exception as e:
        return False, "", f"Unexpected error: {e}"


def analyze_test_failure(stderr: str, stdout: str) -> List[str]:
    """Analyze test failure and provide suggestions."""
    suggestions = []

    error_patterns = {
        "ModuleNotFoundError": [
            "Install missing dependencies: pip install -r requirements-dev.txt",
            "Make sure you're in the backend directory",
            "Check if virtual environment is activated",
        ],
        "ImportError": [
            "Check Python path: export PYTHONPATH=.",
            "Verify all required packages are installed",
            "Make sure you're in the correct directory",
        ],
        "aiosqlite": [
            "Install aiosqlite: pip install aiosqlite",
            "Check if virtual environment is activated",
        ],
        "sqlalchemy": [
            "Install SQLAlchemy: pip install sqlalchemy",
            "Check SQLAlchemy version compatibility",
        ],
        "pytest": [
            "Install pytest: pip install pytest pytest-asyncio",
            "Check pytest configuration in pytest.ini",
        ],
        "PermissionError": [
            "Check file permissions in current directory",
            "Try running from a different directory",
            "Check if directory is read-only",
        ],
        "database": [
            "Check database file permissions",
            "Remove old database files: rm *.db",
            "Check disk space availability",
        ],
        "async": [
            "Install pytest-asyncio: pip install pytest-asyncio",
            "Check async/await syntax compatibility",
        ],
    }

    combined_output = (stderr + stdout).lower()

    for pattern, pattern_suggestions in error_patterns.items():
        if pattern.lower() in combined_output:
            suggestions.extend(pattern_suggestions)

    # Remove duplicates while preserving order
    unique_suggestions = []
    for suggestion in suggestions:
        if suggestion not in unique_suggestions:
            unique_suggestions.append(suggestion)

    return unique_suggestions


def provide_final_recommendations(
    diagnostic_success: bool,
    setup_success: bool,
    test_success: bool,
    test_stderr: str,
    test_stdout: str,
) -> None:
    """Provide final recommendations based on all results."""
    print_banner("Final Recommendations")

    if test_success:
        print("🎉 SUCCESS! All tests are passing.")
        print("\nYour environment is working correctly. You can now:")
        print("  • Continue with development")
        print(
            "  • Run tests anytime with: python -m pytest tests/test_database_base.py -v"
        )
        print("  • Use manual verification: python scripts/verify_step_1_2a.py")
        return

    print("❌ Tests are still failing. Here's what to try:\n")

    # Analyze test failures
    suggestions = analyze_test_failure(test_stderr, test_stdout)

    if suggestions:
        print("🔧 Specific suggestions based on the errors:")
        for i, suggestion in enumerate(suggestions[:5], 1):  # Limit to top 5
            print(f"  {i}. {suggestion}")
        print()

    # General troubleshooting steps
    print("🛠️  General troubleshooting steps:")
    print("  1. Make sure you're in the backend directory: cd backend")
    print("  2. Activate virtual environment: source venv/bin/activate")
    print("  3. Install dependencies: pip install -r requirements-dev.txt")
    print("  4. Check working directory: pwd")
    print("  5. Try running diagnostics again: python scripts/diagnose_environment.py")

    # Environment-specific suggestions
    if not diagnostic_success:
        print("\n📊 Diagnostic issues detected:")
        print("  • Run: python scripts/diagnose_environment.py")
        print("  • Address any failed checks shown")

    if not setup_success:
        print("\n⚙️  Environment setup issues:")
        print("  • Virtual environment might not be activated")
        print("  • Dependencies might not be installed correctly")
        print("  • Try manual setup steps")

    # Docker fallback
    print("\n🐳 If all else fails, try Docker:")
    print(
        "  docker-compose -f docker-compose.dev.yml run backend-dev pytest tests/test_database_base.py -v"
    )

    # Manual verification
    print("\n✋ Try manual verification:")
    print("  python scripts/verify_step_1_2a.py")


def main() -> None:
    """Run the complete safe test sequence."""
    print_banner("Safe Test Runner - Home Inventory System")
    print("This script will diagnose, set up, and run tests safely.")

    # Change to backend directory if needed
    if not os.path.exists("app") and os.path.exists("backend"):
        print("📁 Changing to backend directory...")
        os.chdir("backend")

    # Step 1: Run diagnostics
    print_step("Step 1: Environment Diagnostics")
    diag_success, diag_stdout, diag_stderr = run_script(
        "scripts/diagnose_environment.py", "Environment Diagnostics"
    )

    if diag_success:
        print("✅ Diagnostics completed")
    else:
        print("❌ Diagnostics failed")
        if diag_stderr:
            print(f"Error: {diag_stderr[:300]}...")

    # Step 2: Set up environment
    print_step("Step 2: Environment Setup")
    setup_success, setup_stdout, setup_stderr = run_script(
        "scripts/setup_test_environment.py", "Environment Setup"
    )

    if setup_success:
        print("✅ Environment setup completed")
    else:
        print("❌ Environment setup had issues")
        if setup_stderr:
            print(f"Error: {setup_stderr[:300]}...")

    # Step 3: Run tests
    print_step("Step 3: Running Tests")
    test_success, test_stdout, test_stderr = run_pytest()

    if test_success:
        print("✅ All tests passed!")
        # Show test output
        print("\nTest Output:")
        print(test_stdout)
    else:
        print("❌ Tests failed")
        # Show error details
        if test_stderr:
            print("\nError Output:")
            print(test_stderr[:1000] + ("..." if len(test_stderr) > 1000 else ""))
        if test_stdout:
            print("\nTest Output:")
            print(test_stdout[:1000] + ("..." if len(test_stdout) > 1000 else ""))

    # Step 4: Manual verification (if tests failed)
    if not test_success:
        print_step("Step 4: Manual Verification")
        manual_success, manual_stdout, manual_stderr = run_script(
            "scripts/verify_step_1_2a.py", "Manual Verification"
        )

        if manual_success:
            print("✅ Manual verification passed")
            print(
                "This suggests the issue is with pytest configuration, not the code itself."
            )
        else:
            print("❌ Manual verification also failed")
            print("This suggests a deeper environment issue.")

    # Final recommendations
    provide_final_recommendations(
        diag_success, setup_success, test_success, test_stderr, test_stdout
    )

    # Exit with appropriate code
    sys.exit(0 if test_success else 1)


if __name__ == "__main__":
    main()
