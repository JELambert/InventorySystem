import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.base import (
    get_session,
    create_tables,
    drop_tables,
    check_connection,
    Base,
)
from app.database.config import DatabaseConfig


@pytest.mark.asyncio
async def test_database_connection() -> None:
    """Test that we can connect to the database."""
    connection_ok = await check_connection()
    assert connection_ok is True


@pytest.mark.asyncio
async def test_session_creation() -> None:
    """Test that we can create a database session."""
    async for session in get_session():
        assert isinstance(session, AsyncSession)
        assert session is not None
        break  # Only test the first yielded session


@pytest.mark.asyncio
async def test_create_and_drop_tables() -> None:
    """Test table creation and deletion."""
    # Create tables
    await create_tables()

    # Verify we can connect after table creation
    connection_ok = await check_connection()
    assert connection_ok is True

    # Drop tables
    await drop_tables()

    # Should still be able to connect
    connection_ok = await check_connection()
    assert connection_ok is True


def test_database_config() -> None:
    """Test database configuration functions."""
    # Test database URL retrieval
    db_url = DatabaseConfig.get_database_url()
    assert isinstance(db_url, str)
    assert "sqlite" in db_url.lower()

    # Test engine configuration
    engine_config = DatabaseConfig.get_engine_config()
    assert isinstance(engine_config, dict)
    assert "echo" in engine_config
    assert "future" in engine_config

    # Test session configuration
    session_config = DatabaseConfig.get_session_config()
    assert isinstance(session_config, dict)
    assert "expire_on_commit" in session_config


def test_base_declarative() -> None:
    """Test that SQLAlchemy Base is properly configured."""
    assert Base is not None
    assert hasattr(Base, "metadata")
    assert hasattr(Base, "registry")
