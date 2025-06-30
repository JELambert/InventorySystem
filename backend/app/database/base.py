from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator
from app.database.config import DatabaseConfig
from app.core.logging import get_logger

# Get logger for database operations
logger = get_logger("database")

# SQLAlchemy declarative base
Base = declarative_base()

# Import models to ensure they are registered with the Base
from app.models import location  # noqa: F401
from app.models import category  # noqa: F401
from app.models import item  # noqa: F401

# Database configuration
DATABASE_URL = DatabaseConfig.get_database_url()
logger.info(f"Database URL configured: {DATABASE_URL}")

# Create async engine with config
engine = create_async_engine(
    DATABASE_URL,
    **DatabaseConfig.get_engine_config()
)

# Create async session factory with config
async_session = async_sessionmaker(
    bind=engine, 
    **DatabaseConfig.get_session_config()
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    logger.debug("Creating new database session")
    async with async_session() as session:
        try:
            yield session
        finally:
            logger.debug("Closing database session")
            await session.close()


# Alias for API compatibility
get_async_session = get_session


async def create_tables() -> None:
    """Create all tables in the database."""
    logger.info("Creating database tables")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


async def drop_tables() -> None:
    """Drop all tables in the database (for testing)."""
    logger.info("Dropping database tables")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}")
        raise


async def check_connection() -> bool:
    """Test database connection."""
    logger.debug("Testing database connection")
    try:
        from sqlalchemy import text

        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.debug("Database connection successful")
        return True
    except Exception as e:
        logger.warning(f"Database connection failed: {e}")
        return False
