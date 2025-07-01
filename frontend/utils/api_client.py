"""
API client for communicating with the FastAPI backend.
"""

import requests
import logging
import time
import hashlib
from typing import List, Dict, Any, Optional, Union, Callable
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime, timedelta
from functools import wraps

from utils.config import AppConfig
from utils.error_handling import (
    ErrorContext, ErrorSeverity, ErrorCategory, RetryStrategy, CircuitBreaker, 
    ErrorReporter, safe_execute, RetryManager
)
from utils.notifications import notification_manager

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Custom exception for API-related errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[dict] = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(self.message)


class APIClient:
    """HTTP client for the Home Inventory System API with enhanced error handling."""
    
    def __init__(self):
        """Initialize the API client with configuration."""
        self.base_url = AppConfig.API_BASE_URL
        self.timeout = AppConfig.API_TIMEOUT
        self.session = self._create_session()
        self.circuit_breakers = {}  # Per-endpoint circuit breakers
        self.request_stats = {}     # Request statistics
        self.correlation_id_counter = 0
        
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
    
    def _generate_correlation_id(self) -> str:
        """Generate unique correlation ID for request tracking."""
        self.correlation_id_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{timestamp}_{self.correlation_id_counter:04d}"
    
    def _get_circuit_breaker(self, endpoint: str) -> CircuitBreaker:
        """Get or create circuit breaker for endpoint."""
        if endpoint not in self.circuit_breakers:
            self.circuit_breakers[endpoint] = CircuitBreaker(
                failure_threshold=5,
                recovery_timeout=60
            )
        return self.circuit_breakers[endpoint]
    
    def _record_request_stats(self, endpoint: str, method: str, success: bool, duration: float):
        """Record request statistics for monitoring."""
        key = f"{method}:{endpoint}"
        if key not in self.request_stats:
            self.request_stats[key] = {
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'avg_duration': 0.0,
                'last_request': None
            }
        
        stats = self.request_stats[key]
        stats['total_requests'] += 1
        stats['last_request'] = datetime.now()
        
        if success:
            stats['successful_requests'] += 1
        else:
            stats['failed_requests'] += 1
        
        # Update average duration (simple moving average)
        stats['avg_duration'] = (
            (stats['avg_duration'] * (stats['total_requests'] - 1) + duration) / 
            stats['total_requests']
        )
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[dict] = None,
        params: Optional[dict] = None,
        retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        max_retries: int = 3,
        timeout_override: Optional[int] = None,
        silent: bool = False
    ) -> Union[dict, list]:
        """Make an HTTP request to the API with enhanced error handling and retries."""
        url = AppConfig.get_api_url(endpoint)
        correlation_id = self._generate_correlation_id()
        circuit_breaker = self._get_circuit_breaker(endpoint)
        timeout = timeout_override or self.timeout
        
        # Check circuit breaker
        if not circuit_breaker.can_execute():
            error_msg = f"Circuit breaker is OPEN for endpoint {endpoint}. Service may be unavailable."
            if not silent:
                notification_manager.warning(error_msg)
            raise APIError(error_msg, 503)
        
        def make_single_request() -> Union[dict, list]:
            start_time = time.time()
            
            try:
                # Add correlation ID to headers
                headers = {'X-Correlation-ID': correlation_id}
                
                logger.debug(f"Making {method} request to {url} [ID: {correlation_id}]")
                
                if method.upper() == "GET":
                    response = self.session.get(url, params=params, timeout=timeout, headers=headers)
                elif method.upper() == "POST":
                    response = self.session.post(url, json=data, params=params, timeout=timeout, headers=headers)
                elif method.upper() == "PUT":
                    response = self.session.put(url, json=data, params=params, timeout=timeout, headers=headers)
                elif method.upper() == "DELETE":
                    response = self.session.delete(url, params=params, timeout=timeout, headers=headers)
                else:
                    raise APIError(f"Unsupported HTTP method: {method}")
                
                duration = time.time() - start_time
                
                # Handle response
                if response.status_code == 204:  # No content
                    circuit_breaker.record_success()
                    self._record_request_stats(endpoint, method, True, duration)
                    return {}
                
                if not response.ok:
                    error_data = {}
                    try:
                        error_data = response.json()
                    except:
                        pass
                    
                    # Record failure for circuit breaker and stats
                    if response.status_code >= 500:
                        circuit_breaker.record_failure()
                    
                    self._record_request_stats(endpoint, method, False, duration)
                    
                    error_message = error_data.get('detail', f"HTTP {response.status_code}")
                    api_error = APIError(
                        message=error_message,
                        status_code=response.status_code,
                        response_data=error_data
                    )
                    
                    # Report error with context
                    error_context = ErrorContext(
                        error=api_error,
                        severity=ErrorSeverity.HIGH if response.status_code >= 500 else ErrorSeverity.MEDIUM,
                        category=ErrorCategory.NETWORK,
                        context_data={
                            'endpoint': endpoint,
                            'method': method,
                            'correlation_id': correlation_id,
                            'status_code': response.status_code
                        }
                    )
                    ErrorReporter.report_error(error_context)
                    
                    raise api_error
                
                # Success
                circuit_breaker.record_success()
                self._record_request_stats(endpoint, method, True, duration)
                
                return response.json()
                
            except requests.exceptions.ConnectionError as e:
                duration = time.time() - start_time
                circuit_breaker.record_failure()
                self._record_request_stats(endpoint, method, False, duration)
                
                connection_error = APIError("Unable to connect to the API server. Please check if the backend is running.")
                error_context = ErrorContext(
                    error=connection_error,
                    severity=ErrorSeverity.HIGH,
                    category=ErrorCategory.NETWORK,
                    context_data={
                        'endpoint': endpoint,
                        'method': method,
                        'correlation_id': correlation_id,
                        'original_error': str(e)
                    }
                )
                ErrorReporter.report_error(error_context)
                raise connection_error
                
            except requests.exceptions.Timeout as e:
                duration = time.time() - start_time
                circuit_breaker.record_failure()
                self._record_request_stats(endpoint, method, False, duration)
                
                timeout_error = APIError(f"Request timed out after {timeout} seconds.")
                error_context = ErrorContext(
                    error=timeout_error,
                    severity=ErrorSeverity.MEDIUM,
                    category=ErrorCategory.NETWORK,
                    context_data={
                        'endpoint': endpoint,
                        'method': method,
                        'correlation_id': correlation_id,
                        'timeout': timeout
                    }
                )
                ErrorReporter.report_error(error_context)
                raise timeout_error
                
            except requests.exceptions.RequestException as e:
                duration = time.time() - start_time
                circuit_breaker.record_failure()
                self._record_request_stats(endpoint, method, False, duration)
                
                request_error = APIError(f"Request failed: {str(e)}")
                error_context = ErrorContext(
                    error=request_error,
                    severity=ErrorSeverity.MEDIUM,
                    category=ErrorCategory.NETWORK,
                    context_data={
                        'endpoint': endpoint,
                        'method': method,
                        'correlation_id': correlation_id,
                        'original_error': str(e)
                    }
                )
                ErrorReporter.report_error(error_context)
                raise request_error
        
        # Execute with retry logic
        if silent:
            # For silent requests, handle errors without user notification
            attempt = 0
            last_error = None
            
            while attempt <= max_retries:
                try:
                    return make_single_request()
                except Exception as e:
                    last_error = e
                    if attempt < max_retries and RetryManager.should_retry(e, attempt, max_retries):
                        delay = RetryManager.calculate_delay(attempt, retry_strategy)
                        if delay > 0:
                            time.sleep(delay)
                        attempt += 1
                        continue
                    else:
                        break
            
            # Silent failure - just raise the last error without user notification
            if last_error:
                raise last_error
        else:
            return safe_execute(
                make_single_request,
                error_message=f"API request to {endpoint} failed",
                retry_strategy=retry_strategy,
                max_retries=max_retries
            )
    
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
    
    # Advanced Quantity Operations
    
    def split_item_quantity(self, item_id: int, split_data: dict, user_id: Optional[str] = None) -> List[dict]:
        """
        Split item quantity between two locations.
        
        Args:
            item_id: ID of item to split
            split_data: Dictionary with source_location_id, dest_location_id, quantity_to_move, reason
            user_id: Optional user performing the operation
            
        Returns:
            List of [source_entry, dest_entry] after split
        """
        params = {}
        if user_id:
            params["user_id"] = user_id
        
        return self._make_request("POST", f"inventory/items/{item_id}/split", data=split_data, params=params)
    
    def merge_item_quantities(self, item_id: int, merge_data: dict, user_id: Optional[str] = None) -> dict:
        """
        Merge item quantities from multiple locations into one target location.
        
        Args:
            item_id: ID of item to merge
            merge_data: Dictionary with location_ids (list), target_location_id, reason
            user_id: Optional user performing the operation
            
        Returns:
            Target inventory entry with merged quantity
        """
        params = {}
        if user_id:
            params["user_id"] = user_id
        
        return self._make_request("POST", f"inventory/items/{item_id}/merge", data=merge_data, params=params)
    
    def adjust_item_quantity(self, item_id: int, location_id: int, adjustment_data: dict, user_id: Optional[str] = None) -> dict:
        """
        Adjust item quantity at a specific location.
        
        Args:
            item_id: ID of item to adjust
            location_id: Location ID where adjustment occurs
            adjustment_data: Dictionary with new_quantity, reason
            user_id: Optional user performing the operation
            
        Returns:
            Updated inventory entry or removal confirmation
        """
        params = {}
        if user_id:
            params["user_id"] = user_id
        
        return self._make_request("PUT", f"inventory/items/{item_id}/locations/{location_id}/quantity", 
                                 data=adjustment_data, params=params)
    
    # Movement History Methods
    
    def get_movement_history(
        self,
        item_id: Optional[int] = None,
        location_id: Optional[int] = None,
        from_location_id: Optional[int] = None,
        to_location_id: Optional[int] = None,
        movement_type: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_quantity: Optional[int] = None,
        max_quantity: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[dict]:
        """
        Get movement history with filtering and pagination.
        
        Args:
            item_id: Filter by item ID
            location_id: Filter by either source or destination location ID
            from_location_id: Filter by source location ID
            to_location_id: Filter by destination location ID
            movement_type: Filter by movement type
            user_id: Filter by user ID
            start_date: Filter movements after this date (ISO format)
            end_date: Filter movements before this date (ISO format)
            min_quantity: Minimum quantity moved
            max_quantity: Maximum quantity moved
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of movement history entries with details
        """
        params = {"skip": skip, "limit": limit}
        
        if item_id is not None:
            params["item_id"] = item_id
        if location_id is not None:
            params["location_id"] = location_id
        if from_location_id is not None:
            params["from_location_id"] = from_location_id
        if to_location_id is not None:
            params["to_location_id"] = to_location_id
        if movement_type:
            params["movement_type"] = movement_type
        if user_id:
            params["user_id"] = user_id
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if min_quantity is not None:
            params["min_quantity"] = min_quantity
        if max_quantity is not None:
            params["max_quantity"] = max_quantity
        
        return self._make_request("GET", "inventory/history", params=params)
    
    def get_movement_history_summary(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> dict:
        """
        Get movement history summary statistics.
        
        Args:
            start_date: Optional start date for filtering (ISO format)
            end_date: Optional end date for filtering (ISO format)
            
        Returns:
            Summary statistics and recent activity
        """
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        return self._make_request("GET", "inventory/history/summary", params=params)
    
    def get_item_movement_timeline(self, item_id: int) -> dict:
        """
        Get complete movement timeline for a specific item.
        
        Args:
            item_id: ID of the item
            
        Returns:
            Complete movement timeline with current status
        """
        return self._make_request("GET", f"inventory/items/{item_id}/timeline")
    
    # Utility Methods
    
    def get_connection_info(self) -> dict:
        """Get comprehensive information about the API connection."""
        return {
            "base_url": self.base_url,
            "timeout": self.timeout,
            "is_connected": self.health_check(),
            "circuit_breakers": {
                endpoint: {
                    "state": cb.state,
                    "failure_count": cb.failure_count,
                    "last_failure": cb.last_failure_time.isoformat() if cb.last_failure_time else None
                }
                for endpoint, cb in self.circuit_breakers.items()
            },
            "request_stats": self.request_stats
        }
    
    def reset_circuit_breakers(self):
        """Reset all circuit breakers to CLOSED state."""
        for cb in self.circuit_breakers.values():
            cb.failure_count = 0
            cb.state = "CLOSED"
            cb.last_failure_time = None
        notification_manager.info("All circuit breakers have been reset")
    
    def get_api_health_report(self) -> dict:
        """Get comprehensive API health report."""
        total_requests = sum(stats['total_requests'] for stats in self.request_stats.values())
        successful_requests = sum(stats['successful_requests'] for stats in self.request_stats.values())
        failed_requests = sum(stats['failed_requests'] for stats in self.request_stats.values())
        
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
        
        # Check circuit breaker health
        open_breakers = [endpoint for endpoint, cb in self.circuit_breakers.items() if cb.state == "OPEN"]
        
        return {
            "overall_health": "healthy" if success_rate > 90 and not open_breakers else "degraded",
            "success_rate": round(success_rate, 2),
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "open_circuit_breakers": open_breakers,
            "endpoint_performance": {
                endpoint: {
                    "success_rate": round((stats['successful_requests'] / stats['total_requests'] * 100), 2)
                    if stats['total_requests'] > 0 else 0,
                    "avg_duration_ms": round(stats['avg_duration'] * 1000, 2),
                    "total_requests": stats['total_requests']
                }
                for endpoint, stats in self.request_stats.items()
            }
        }
    
    # Movement Validation Methods
    
    def validate_movement(
        self, 
        movement_data: Dict[str, Any], 
        enforce_strict: bool = True
    ) -> dict:
        """
        Validate a movement operation without executing it.
        
        Args:
            movement_data: Movement data to validate
            enforce_strict: Whether to enforce strict business rule validation
            
        Returns:
            Validation result with errors, warnings, and business rules applied
        """
        params = {"enforce_strict": enforce_strict}
        return self._make_request("POST", "inventory/validate/movement", data=movement_data, params=params)
    
    def validate_bulk_movement(
        self, 
        movements: List[Dict[str, Any]], 
        enforce_atomic: bool = True
    ) -> dict:
        """
        Validate multiple movement operations as a batch.
        
        Args:
            movements: List of movements to validate
            enforce_atomic: Whether all movements must pass validation
            
        Returns:
            Overall validation result plus individual results for each movement
        """
        params = {"enforce_atomic": enforce_atomic}
        return self._make_request("POST", "inventory/validate/bulk-movement", data=movements, params=params)
    
    def get_validation_report(self, item_id: Optional[int] = None) -> dict:
        """
        Get comprehensive validation system report.
        
        Args:
            item_id: Optional filter by specific item
            
        Returns:
            Validation system report with business rules, statistics, and health metrics
        """
        params = {}
        if item_id:
            params["item_id"] = item_id
        
        return self._make_request("GET", "inventory/validation/report", params=params)
    
    def apply_business_rule_overrides(self, overrides: Dict[str, Any]) -> dict:
        """
        Apply temporary business rule overrides.
        
        Args:
            overrides: Dictionary of rule overrides
            
        Returns:
            Result of applying overrides with active rules
        """
        return self._make_request("POST", "inventory/validation/rules/override", data=overrides)
    
    # Performance and Optimization Methods
    
    def get_performance_metrics(self) -> dict:
        """
        Get current performance metrics and analysis.
        
        Returns:
            Performance metrics including cache stats and query analysis
        """
        try:
            return self._make_request("GET", "performance/metrics", max_retries=1, silent=True)
        except Exception as e:
            logger.debug(f"Performance metrics unavailable: {e}")
            # Return minimal fallback metrics instead of raising error
            return {
                "cache_stats": {"status": "unavailable"},
                "query_analysis": {"status": "unavailable"}, 
                "optimization_status": {"caching_enabled": False}
            }
    
    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Cache statistics including hit rates and entry counts
        """
        try:
            return self._make_request("GET", "performance/cache/stats", max_retries=1, silent=True)
        except Exception as e:
            logger.debug(f"Cache stats unavailable: {e}")
            return {"status": "unavailable", "message": "Cache statistics not available"}
    
    def warm_cache(self) -> dict:
        """
        Warm up cache with frequently accessed data.
        
        Returns:
            Result of cache warming operation
        """
        try:
            return self._make_request("POST", "performance/cache/warm", max_retries=1, silent=True)
        except Exception as e:
            logger.debug(f"Cache warming unavailable: {e}")
            return {"status": "unavailable", "message": "Cache warming not available"}
    
    def clear_cache(self, pattern: Optional[str] = None) -> dict:
        """
        Clear cache entries.
        
        Args:
            pattern: Optional pattern to clear specific entries
            
        Returns:
            Result of cache clearing operation
        """
        try:
            params = {}
            if pattern:
                params["pattern"] = pattern
            
            return self._make_request("DELETE", "performance/cache/clear", params=params, max_retries=1, silent=True)
        except Exception as e:
            logger.debug(f"Cache clearing unavailable: {e}")
            return {"status": "unavailable", "message": "Cache clearing not available"}
    
    def analyze_queries(self) -> dict:
        """
        Analyze query performance and get optimization recommendations.
        
        Returns:
            Query analysis with performance recommendations
        """
        try:
            return self._make_request("GET", "performance/query-analysis", max_retries=1, silent=True)
        except Exception as e:
            logger.debug(f"Query analysis unavailable: {e}")
            return {"status": "unavailable", "message": "Query analysis not available"}
    
    def create_performance_indexes(self) -> dict:
        """
        Create recommended database indexes for performance optimization.
        
        Returns:
            Result of index creation with list of created indexes
        """
        try:
            return self._make_request("POST", "performance/optimize/indexes", max_retries=1, silent=True)
        except Exception as e:
            logger.debug(f"Performance index creation unavailable: {e}")
            return {"status": "unavailable", "message": "Performance index creation not available"}
    
    def get_optimized_locations(self) -> List[dict]:
        """
        Get locations with counts using optimized cached query.
        
        Returns:
            List of locations with item counts (cached)
        """
        return self._make_request("GET", "performance/optimized/locations")
    
    def get_optimized_categories(self) -> List[dict]:
        """
        Get categories using optimized cached query.
        
        Returns:
            List of categories (cached)
        """
        return self._make_request("GET", "performance/optimized/categories")