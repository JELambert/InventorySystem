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
    
    # Item CRUD Methods
    
    def get_items(
        self, 
        skip: int = 0, 
        limit: int = 100,
        item_type: Optional[str] = None,
        category_id: Optional[int] = None,
        search: Optional[str] = None,
        condition: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[dict]:
        """Get a list of items with optional filtering."""
        params = {"skip": skip, "limit": limit}
        
        if item_type:
            params["item_type"] = item_type
        if category_id is not None:
            params["category_id"] = category_id
        if search:
            params["search"] = search
        if condition:
            params["condition"] = condition
        if status:
            params["status"] = status
        
        return self._make_request("GET", "items/", params=params)
    
    def get_item(self, item_id: int) -> dict:
        """Get a specific item by ID."""
        return self._make_request("GET", f"items/{item_id}")
    
    def create_item(self, item_data: dict) -> dict:
        """Create a new item."""
        return self._make_request("POST", "items/", data=item_data)
    
    def create_item_with_location(self, item_data: dict) -> dict:
        """
        Create a new item and assign it to a location via inventory service.
        
        Args:
            item_data: Item data including location_id and quantity fields
            
        Returns:
            dict: Created item data with inventory information
            
        Raises:
            APIError: If location doesn't exist, validation fails, or duplicate serial/barcode
        """
        return self._make_request("POST", "items/with-location", data=item_data)
    
    def update_item(self, item_id: int, item_data: dict) -> dict:
        """Update an existing item."""
        return self._make_request("PUT", f"items/{item_id}", data=item_data)
    
    def delete_item(self, item_id: int) -> bool:
        """Delete an item."""
        try:
            self._make_request("DELETE", f"items/{item_id}")
            return True
        except APIError:
            return False
    
    def search_items(self, search_data: dict) -> List[dict]:
        """Search items with advanced filtering."""
        return self._make_request("POST", "items/search", data=search_data)
    
    def get_item_statistics(self) -> dict:
        """Get item statistics and analytics."""
        return self._make_request("GET", "items/statistics/overview")
    
    def update_item_status(self, item_id: int, new_status: str, notes: Optional[str] = None) -> dict:
        """Update item status."""
        data = {"new_status": new_status}
        if notes:
            data["notes"] = notes
        return self._make_request("PUT", f"items/{item_id}/status", data=data)
    
    def update_item_condition(self, item_id: int, new_condition: str, notes: Optional[str] = None) -> dict:
        """Update item condition."""
        data = {"new_condition": new_condition}
        if notes:
            data["notes"] = notes
        return self._make_request("PUT", f"items/{item_id}/condition", data=data)
    
    def update_item_value(self, item_id: int, new_value: float, notes: Optional[str] = None) -> dict:
        """Update item value."""
        data = {"new_value": new_value}
        if notes:
            data["notes"] = notes
        return self._make_request("PUT", f"items/{item_id}/value", data=data)
    
    def add_item_tag(self, item_id: int, tag: str) -> dict:
        """Add a tag to an item."""
        data = {"tag": tag}
        return self._make_request("POST", f"items/{item_id}/tags", data=data)
    
    def remove_item_tag(self, item_id: int, tag: str) -> dict:
        """Remove a tag from an item."""
        data = {"tag": tag}
        return self._make_request("DELETE", f"items/{item_id}/tags", data=data)
    
    def get_item_tags(self, item_id: int) -> List[str]:
        """Get all tags for an item."""
        return self._make_request("GET", f"items/{item_id}/tags")
    
    def bulk_update_items(self, updates: List[dict]) -> dict:
        """Bulk update multiple items."""
        data = {"updates": updates}
        return self._make_request("PUT", "items/bulk", data=data)
    
    def export_items(self, export_format: str = "csv", filters: Optional[dict] = None) -> dict:
        """Export items to specified format."""
        data = {"format": export_format}
        if filters:
            data["filters"] = filters
        return self._make_request("POST", "items/export", data=data)
    
    # Inventory Management Methods
    
    def get_inventory(
        self,
        item_id: Optional[int] = None,
        location_id: Optional[int] = None,
        min_quantity: Optional[int] = None,
        max_quantity: Optional[int] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> List[dict]:
        """Get inventory entries with optional filtering."""
        params = {}
        if item_id is not None:
            params["item_id"] = item_id
        if location_id is not None:
            params["location_id"] = location_id
        if min_quantity is not None:
            params["min_quantity"] = min_quantity
        if max_quantity is not None:
            params["max_quantity"] = max_quantity
        if min_value is not None:
            params["min_value"] = min_value
        if max_value is not None:
            params["max_value"] = max_value
        
        return self._make_request("GET", "inventory/", params=params)
    
    def get_inventory_entry(self, inventory_id: int) -> dict:
        """Get a specific inventory entry by ID."""
        return self._make_request("GET", f"inventory/{inventory_id}")
    
    def create_inventory_entry(self, item_id: int, location_id: int, quantity: int = 1) -> dict:
        """Create a new inventory entry."""
        data = {
            "item_id": item_id,
            "location_id": location_id,
            "quantity": quantity
        }
        return self._make_request("POST", "inventory/", data=data)
    
    def update_inventory_entry(self, inventory_id: int, update_data: dict) -> dict:
        """Update an inventory entry."""
        return self._make_request("PUT", f"inventory/{inventory_id}", data=update_data)
    
    def delete_inventory_entry(self, inventory_id: int) -> bool:
        """Delete an inventory entry."""
        try:
            self._make_request("DELETE", f"inventory/{inventory_id}")
            return True
        except APIError:
            return False
    
    def move_item(self, item_id: int, from_location_id: int, to_location_id: int, quantity: int) -> dict:
        """Move items between locations."""
        data = {
            "from_location_id": from_location_id,
            "to_location_id": to_location_id,
            "quantity": quantity
        }
        return self._make_request("POST", f"inventory/move/{item_id}", data=data)
    
    def get_item_locations(self, item_id: int) -> List[dict]:
        """Get all locations where an item is stored."""
        return self._make_request("GET", f"inventory/items/{item_id}/locations")
    
    def get_location_items(self, location_id: int) -> List[dict]:
        """Get all items stored in a location."""
        return self._make_request("GET", f"inventory/locations/{location_id}/items")
    
    def get_inventory_summary(self) -> dict:
        """Get overall inventory summary statistics."""
        return self._make_request("GET", "inventory/summary")
    
    def get_location_inventory_report(self, location_id: int) -> dict:
        """Generate comprehensive inventory report for a location."""
        return self._make_request("GET", f"inventory/locations/{location_id}/report")
    
    def bulk_create_inventory(self, operations: List[dict]) -> List[dict]:
        """Create multiple inventory entries in a single transaction."""
        data = {"operations": operations}
        return self._make_request("POST", "inventory/bulk", data=data)
    
    def get_items_with_inventory(self, **kwargs) -> List[dict]:
        """
        Get items enriched with inventory information.
        
        Args:
            **kwargs: Same parameters as get_items()
            
        Returns:
            List of items with inventory_entries field added
        """
        # Get basic items
        items = self.get_items(**kwargs)
        
        # Enrich with inventory information
        for item in items:
            try:
                inventory_entries = self.get_inventory(item_id=item['id'])
                # Add location details to inventory entries
                for entry in inventory_entries:
                    if entry.get('location_id'):
                        try:
                            location = self.get_location(entry['location_id'])
                            entry['location'] = location
                        except:
                            entry['location'] = {'name': 'Unknown Location', 'id': entry['location_id']}
                
                item['inventory_entries'] = inventory_entries
            except:
                item['inventory_entries'] = []
        
        return items
    
    # Utility Methods
    
    def get_connection_info(self) -> dict:
        """Get information about the API connection."""
        return {
            "base_url": self.base_url,
            "timeout": self.timeout,
            "is_connected": self.health_check()
        }