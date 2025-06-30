from typing import Dict, Any
import os
import sys
from pathlib import Path


class DatabaseConfig:
    """Database configuration settings."""

    @staticmethod
    def get_database_path() -> str:
        """Get the database file path."""
        # Default to data directory relative to backend folder
        default_path = Path(__file__).parent.parent.parent / "data" / "inventory.db"
        return os.getenv("DATABASE_PATH", str(default_path))

    @staticmethod
    def get_database_url() -> str:
        """Get database URL based on environment."""
        # Always use SQLite in-memory for testing
        if DatabaseConfig.is_testing():
            return DatabaseConfig.get_test_database_url()
        
        # Check for full DATABASE_URL first (for custom PostgreSQL URL)
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            return database_url
        
        # Always use PostgreSQL for development and production
        return DatabaseConfig.get_postgres_url()

    @staticmethod
    def get_postgres_url() -> str:
        """Get PostgreSQL URL for development and production."""
        # Use Proxmox PostgreSQL instance
        host = os.getenv("POSTGRES_HOST", "192.168.68.88")
        port = os.getenv("POSTGRES_PORT", "5432")
        database = os.getenv("POSTGRES_DB", "inventory_system")
        username = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "vaultlock1")
        
        return f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{database}"

    @staticmethod
    def is_testing() -> bool:
        """Check if we're in a testing environment."""
        return (
            os.getenv("TESTING") == "true" or
            os.getenv("PYTEST_CURRENT_TEST") is not None or 
            "pytest" in os.getenv("_", "").lower() or
            "pytest" in str(os.getenv("_")) or
            hasattr(sys, '_called_from_test') or
            any('pytest' in arg for arg in sys.argv) or
            "test" in sys.argv[0].lower()
        )

    @staticmethod
    def get_test_database_url() -> str:
        """Get database URL for testing (always SQLite in-memory)."""
        return "sqlite+aiosqlite:///:memory:"

    @staticmethod
    def get_engine_config() -> Dict[str, Any]:
        """Get SQLAlchemy engine configuration."""
        is_development = os.getenv("ENVIRONMENT", "development") == "development"
        database_url = DatabaseConfig.get_database_url()
        
        base_config = {
            "echo": is_development,  # Log SQL in development
            "future": True,  # Use SQLAlchemy 2.0 style
        }
        
        # PostgreSQL-specific configuration
        if "postgresql" in database_url:
            base_config.update({
                "pool_pre_ping": True,  # Verify connections before use
                "pool_size": 5,  # Connection pool size
                "max_overflow": 10,  # Maximum overflow connections
                "pool_timeout": 30,  # Connection timeout in seconds
                "pool_recycle": 3600,  # Recycle connections after 1 hour
            })
        # SQLite configuration
        else:
            base_config.update({
                "pool_pre_ping": True,  # Verify connections before use
            })
        
        return base_config

    @staticmethod
    def get_session_config() -> Dict[str, Any]:
        """Get SQLAlchemy session configuration."""
        return {
            "expire_on_commit": False,  # Keep objects accessible after commit
            "autoflush": True,  # Auto-flush before queries
            "autocommit": False,  # Manual transaction control
        }
