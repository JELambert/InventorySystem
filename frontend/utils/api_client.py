"""
API client for communicating with the FastAPI backend.
"""

import requests
import logging
import time
from typing import List, Dict, Any, Optional, Union
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.config import AppConfig

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Custom exception for API-related errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[dict] = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(self.message)


class APIClient:
    """HTTP client for the Home Inventory System API."""
    
    def __init__(self):
        """Initialize the API client with configuration."""
        self.base_url = AppConfig.API_BASE_URL
        self.timeout = AppConfig.API_TIMEOUT
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """Create a configured requests session with retry logic."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=AppConfig.API_RETRY_COUNT,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"{AppConfig.APP_TITLE}/1.0"
        })
        
        return session
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[dict] = None,
        params: Optional[dict] = None
    ) -> Union[dict, list]:
        """Make an HTTP request to the API."""
        url = AppConfig.get_api_url(endpoint)
        
        try:
            logger.debug(f"Making {method} request to {url}")
            
            if method.upper() == "GET":
                response = self.session.get(url, params=params, timeout=self.timeout)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, params=params, timeout=self.timeout)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, params=params, timeout=self.timeout)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, params=params, timeout=self.timeout)
            else:
                raise APIError(f"Unsupported HTTP method: {method}")
            
            # Handle response
            if response.status_code == 204:  # No content
                return {}
            
            if not response.ok:
                error_data = {}
                try:
                    error_data = response.json()
                except:
                    pass
                
                error_message = error_data.get('detail', f"HTTP {response.status_code}")
                raise APIError(
                    message=error_message,
                    status_code=response.status_code,
                    response_data=error_data
                )
            
            return response.json()
            
        except requests.exceptions.ConnectionError:
            raise APIError("Unable to connect to the API server. Please check if the backend is running.")
        except requests.exceptions.Timeout:
            raise APIError(f"Request timed out after {self.timeout} seconds.")
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {str(e)}")
    
    # Health and Status Methods
    
    def health_check(self) -> bool:
        """Check if the API is healthy and accessible."""
        try:
            # Health endpoint is at root level, not under /api/v1/
            url = f"{self.base_url.rstrip('/')}/health"
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("status") == "healthy"
            else:
                return False
        except Exception:
            return False
    
    def get_location_stats(self) -> dict:
        """Get location statistics summary."""
        return self._make_request("GET", "locations/stats/summary")
    
    # Location CRUD Methods
    
    def get_locations(
        self, 
        skip: int = 0, 
        limit: int = 100,
        location_type: Optional[str] = None,
        parent_id: Optional[int] = None
    ) -> List[dict]:
        """Get a list of locations with optional filtering."""
        params = {"skip": skip, "limit": limit}
        
        if location_type:
            params["location_type"] = location_type
        if parent_id is not None:
            params["parent_id"] = parent_id
        
        return self._make_request("GET", "locations/", params=params)
    
    def get_location(self, location_id: int) -> dict:
        """Get a specific location by ID."""
        return self._make_request("GET", f"locations/{location_id}")
    
    def create_location(self, location_data: dict) -> dict:
        """Create a new location."""
        return self._make_request("POST", "locations/", data=location_data)
    
    def update_location(self, location_id: int, location_data: dict) -> dict:
        """Update an existing location."""
        return self._make_request("PUT", f"locations/{location_id}", data=location_data)
    
    def delete_location(self, location_id: int) -> bool:
        """Delete a location."""
        try:
            self._make_request("DELETE", f"locations/{location_id}")
            return True
        except APIError:
            return False
    
    def get_location_children(self, location_id: int) -> List[dict]:
        """Get all direct children of a location."""
        return self._make_request("GET", f"locations/{location_id}/children")
    
    def get_location_tree(self, location_id: int, max_depth: int = 5) -> dict:
        """Get a location tree structure."""
        params = {"max_depth": max_depth}
        return self._make_request("GET", f"locations/{location_id}/tree", params=params)
    
    def search_locations(self, search_data: dict) -> List[dict]:
        """Search locations with advanced filtering."""
        return self._make_request("POST", "locations/search", data=search_data)
    
    def validate_location(self, location_id: int) -> dict:
        """Validate a location's hierarchy and constraints."""
        return self._make_request("POST", f"locations/{location_id}/validate")
    
    # Category Methods
    
    def get_categories(self, page: int = 1, per_page: int = 20, include_inactive: bool = False, 
                      search: Optional[str] = None) -> dict:
        """Get a paginated list of categories."""
        params = {
            "page": page,
            "per_page": per_page,
            "include_inactive": include_inactive
        }
        if search:
            params["search"] = search
        return self._make_request("GET", "categories/", params=params)
    
    def get_category(self, category_id: int) -> dict:
        """Get a specific category by ID."""
        return self._make_request("GET", f"categories/{category_id}")
    
    def create_category(self, category_data: dict) -> dict:
        """Create a new category."""
        return self._make_request("POST", "categories/", data=category_data)
    
    def update_category(self, category_id: int, category_data: dict) -> dict:
        """Update an existing category."""
        return self._make_request("PUT", f"categories/{category_id}", data=category_data)
    
    def delete_category(self, category_id: int, permanent: bool = False) -> bool:
        """Delete a category (soft delete by default)."""
        try:
            params = {"permanent": permanent} if permanent else {}
            self._make_request("DELETE", f"categories/{category_id}", params=params)
            return True
        except APIError:
            return False
    
    def restore_category(self, category_id: int) -> dict:
        """Restore an inactive category."""
        return self._make_request("POST", f"categories/{category_id}/restore")
    
    def get_category_stats(self) -> dict:
        """Get category statistics and analytics."""
        return self._make_request("GET", "categories/stats")
    
    # Utility Methods
    
    def get_connection_info(self) -> dict:
        """Get information about the API connection."""
        return {
            "base_url": self.base_url,
            "timeout": self.timeout,
            "is_connected": self.health_check()
        }