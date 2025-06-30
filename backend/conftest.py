"""
Test configuration for pytest.

Ensures tests always use SQLite in-memory database.
"""

import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment to use SQLite in-memory database."""
    # Force SQLite for all tests
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    # Mark that we're in testing mode
    os.environ["TESTING"] = "true"
    yield
    # Clean up after tests
    os.environ.pop("DATABASE_URL", None)
    os.environ.pop("TESTING", None)