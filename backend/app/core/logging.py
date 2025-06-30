"""
Logging configuration for the Home Inventory System.

Provides structured logging setup for development and production environments.
"""

import logging
import sys
from typing import Dict, Any
import os


class LoggingConfig:
    """Centralized logging configuration."""
    
    @staticmethod
    def get_log_level() -> str:
        """Get log level from environment."""
        return os.getenv("LOG_LEVEL", "INFO").upper()
    
    @staticmethod
    def is_development() -> bool:
        """Check if running in development environment."""
        return os.getenv("ENVIRONMENT", "development") == "development"
    
    @staticmethod
    def setup_logging() -> None:
        """Configure logging for the application."""
        log_level = LoggingConfig.get_log_level()
        is_dev = LoggingConfig.is_development()
        
        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, log_level),
            format=LoggingConfig._get_log_format(is_dev),
            stream=sys.stdout,
            force=True  # Override any existing configuration
        )
        
        # Configure SQLAlchemy logging
        if is_dev:
            # Show SQL queries in development
            logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
        else:
            # Reduce SQL logging in production
            logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        
        # Configure application logger
        app_logger = logging.getLogger("inventory_system")
        app_logger.setLevel(getattr(logging, log_level))
        
        # Log startup message
        app_logger.info(
            f"Logging configured - Level: {log_level}, Environment: "
            f"{'development' if is_dev else 'production'}"
        )
    
    @staticmethod
    def _get_log_format(is_development: bool) -> str:
        """Get appropriate log format for environment."""
        if is_development:
            # Detailed format for development
            return (
                "%(asctime)s - %(name)s - %(levelname)s - "
                "%(filename)s:%(lineno)d - %(message)s"
            )
        else:
            # Structured format for production
            return (
                "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
            )
    
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get a logger instance for a specific module."""
        return logging.getLogger(f"inventory_system.{name}")


# Convenience function for getting application loggers
def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module."""
    return LoggingConfig.get_logger(name)