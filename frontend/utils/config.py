"""
Configuration management for the Streamlit frontend application.
"""

import os
from typing import Optional


class AppConfig:
    """Application configuration settings."""
    
    # API Configuration
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    API_TIMEOUT: int = int(os.getenv("API_TIMEOUT", "30"))
    API_RETRY_COUNT: int = int(os.getenv("API_RETRY_COUNT", "3"))
    
    # Frontend Configuration
    APP_TITLE: str = "Home Inventory System"
    APP_ICON: str = "🏠"
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Development Configuration
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    SHOW_API_ERRORS: bool = os.getenv("SHOW_API_ERRORS", "true").lower() == "true"
    
    @classmethod
    def get_api_url(cls, endpoint: str) -> str:
        """Get full API URL for an endpoint."""
        base_url = cls.API_BASE_URL.rstrip('/')
        endpoint = endpoint.lstrip('/')
        return f"{base_url}/api/v1/{endpoint}"
    
    @classmethod
    def is_development(cls) -> bool:
        """Check if running in development mode."""
        return cls.DEBUG or "localhost" in cls.API_BASE_URL or "127.0.0.1" in cls.API_BASE_URL