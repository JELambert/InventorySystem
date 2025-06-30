#!/usr/bin/env python3
"""
Simple test runner that sets up Python path and runs tests.
This is the recommended way to run tests to avoid import issues.
"""

import os
import sys
import subprocess


def main():
    """Run tests with proper Python path setup."""
    # Add current directory to Python path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    # Set PYTHONPATH environment variable
    env = os.environ.copy()
    env["PYTHONPATH"] = current_dir

    # Allow specifying which tests to run via command line
    test_args = (
        sys.argv[1:] if len(sys.argv) > 1 else ["tests/test_database_base.py", "-v"]
    )

    # Run pytest with the modified environment
    cmd = [sys.executable, "-m", "pytest"] + test_args

    print("🧪 Running Tests with Python Path Fix")
    print(f"Command: {' '.join(cmd)}")
    print(f"PYTHONPATH: {current_dir}")
    print("-" * 60)

    try:
        result = subprocess.run(cmd, env=env, cwd=current_dir)

        if result.returncode == 0:
            print("\n✅ All tests passed!")
        else:
            print(f"\n❌ Tests failed with exit code {result.returncode}")

        return result.returncode
    except KeyboardInterrupt:
        print("\n❌ Test run interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
