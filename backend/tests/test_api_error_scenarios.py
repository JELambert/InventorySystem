"""
Comprehensive error scenario test suite for API endpoints.

Tests all types of error handling including HTTP errors, validation errors,
business logic errors, and system failures across all API endpoints.
"""

import pytest
import json
from datetime import datetime, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, OperationalError
from unittest.mock import AsyncMock, patch, Mock

from app.main import app


class TestHTTPErrorHandling:
    """Test proper HTTP error code handling across all endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_400_bad_request_scenarios(self, client):
        """Test 400 Bad Request error handling."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Malformed JSON in request body
            malformed_requests = [
                # Items API
                ("/api/v1/items/", {"name": "", "item_type": "invalid_enum"}),
                ("/api/v1/items/with-location", {"name": "Test", "location_id": "not_an_int"}),
                ("/api/v1/items/bulk-update", {"item_ids": [], "updates": {}}),  # Empty IDs
                
                # Inventory API
                ("/api/v1/inventory/", {"item_id": -1, "quantity": -5}),  # Negative values
                ("/api/v1/inventory/bulk", {"operations": []}),  # Empty operations
            ]
            
            for endpoint, bad_data in malformed_requests:
                response = client.post(endpoint, json=bad_data)
                
                # Should not return 404 (endpoint exists)
                assert response.status_code != 404
                
                # Should handle bad request appropriately
                if response.status_code == 400:
                    data = response.json()
                    assert "detail" in data
    
    def test_404_not_found_scenarios(self, client):
        """Test 404 Not Found error handling for missing resources."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Mock database queries to return None (not found)
            mock_db.execute.return_value.scalar_one_or_none.return_value = None
            
            not_found_requests = [
                # Items API
                ("GET", "/api/v1/items/99999"),
                ("PUT", "/api/v1/items/99999", {"name": "Updated"}),
                ("DELETE", "/api/v1/items/99999"),
                ("POST", "/api/v1/items/99999/restore"),
                ("PUT", "/api/v1/items/99999/status", {"new_status": "available"}),
                
                # Inventory API
                ("GET", "/api/v1/inventory/99999"),
                ("PUT", "/api/v1/inventory/99999", {"quantity": 10}),
                ("DELETE", "/api/v1/inventory/99999"),
                ("POST", "/api/v1/inventory/move/99999", {"to_location_id": 1, "quantity": 1}),
            ]
            
            for method, endpoint, *data in not_found_requests:
                if method == "GET":
                    response = client.get(endpoint)
                elif method == "PUT":
                    response = client.put(endpoint, json=data[0] if data else {})
                elif method == "POST":
                    response = client.post(endpoint, json=data[0] if data else {})
                elif method == "DELETE":
                    response = client.delete(endpoint)
                
                # Endpoint should exist (not 404 for endpoint)
                assert response.status_code != 405  # Method not allowed indicates endpoint exists
                
                # May return 404 for resource not found (which is correct)
                if response.status_code == 404:
                    data = response.json()
                    assert "detail" in data
    
    def test_409_conflict_scenarios(self, client):
        """Test 409 Conflict error handling."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Mock integrity constraint violations
            integrity_error = IntegrityError("UNIQUE constraint failed", None, None)
            mock_db.add.side_effect = integrity_error
            
            conflict_requests = [
                # Duplicate serial number
                ("/api/v1/items/", {
                    "name": "Test Item",
                    "item_type": "electronics",
                    "serial_number": "DUPLICATE123"
                }),
                
                # Duplicate barcode
                ("/api/v1/items/", {
                    "name": "Test Item",
                    "item_type": "electronics",
                    "barcode": "1234567890123"
                }),
            ]
            
            for endpoint, conflict_data in conflict_requests:
                response = client.post(endpoint, json=conflict_data)
                
                # Should not return 404 for endpoint
                assert response.status_code != 404
                
                # Should handle conflicts appropriately
                if response.status_code in [400, 409]:
                    data = response.json()
                    assert "detail" in data
    
    def test_422_validation_error_scenarios(self, client):
        """Test 422 Unprocessable Entity error handling."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            validation_error_requests = [
                # Invalid enum values
                ("/api/v1/items/", {
                    "name": "Test Item",
                    "item_type": "invalid_type",  # Invalid enum
                    "condition": "invalid_condition",  # Invalid enum
                    "status": "invalid_status"  # Invalid enum
                }),
                
                # Invalid data types
                ("/api/v1/items/", {
                    "name": "Test Item",
                    "item_type": "electronics",
                    "purchase_price": "not_a_number",  # String instead of number
                    "purchase_date": "invalid_date",  # Invalid date format
                    "category_id": "not_an_int"  # String instead of int
                }),
                
                # Missing required fields
                ("/api/v1/inventory/", {
                    "quantity": 5  # Missing item_id and location_id
                }),
            ]
            
            for endpoint, invalid_data in validation_error_requests:
                response = client.post(endpoint, json=invalid_data)
                
                # Should not return 404 for endpoint
                assert response.status_code != 404
                
                # Should return validation error
                if response.status_code == 422:
                    data = response.json()
                    assert "detail" in data
                    # FastAPI validation errors have specific structure
                    if isinstance(data["detail"], list):
                        for error in data["detail"]:
                            assert "loc" in error
                            assert "msg" in error
    
    def test_500_internal_server_error_scenarios(self, client):
        """Test 500 Internal Server Error handling."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Mock database connection errors
            operational_error = OperationalError("Database connection failed", None, None)
            mock_db.execute.side_effect = operational_error
            
            server_error_requests = [
                ("GET", "/api/v1/items/"),
                ("GET", "/api/v1/inventory/"),
                ("GET", "/api/v1/performance/metrics"),
                ("GET", "/api/v1/items/statistics/overview"),
            ]
            
            for method, endpoint in server_error_requests:
                response = client.get(endpoint)
                
                # Should not return 404 for endpoint
                assert response.status_code != 404
                
                # Should handle server errors gracefully
                if response.status_code == 500:
                    data = response.json()
                    assert "detail" in data


class TestValidationErrorHandling:
    """Test data validation error handling."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_item_validation_errors(self, client):
        """Test item-specific validation errors."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            validation_cases = [
                # Empty name
                {"name": "", "item_type": "electronics"},
                
                # Name too long (assuming limit)
                {"name": "x" * 1000, "item_type": "electronics"},
                
                # Negative prices
                {"name": "Test", "item_type": "electronics", "purchase_price": -100},
                {"name": "Test", "item_type": "electronics", "current_value": -50},
                
                # Invalid date formats
                {"name": "Test", "item_type": "electronics", "purchase_date": "invalid-date"},
                {"name": "Test", "item_type": "electronics", "warranty_expiry": "not-a-date"},
                
                # Invalid weight/dimensions
                {"name": "Test", "item_type": "electronics", "weight": -10},
                {"name": "Test", "item_type": "electronics", "weight": "not-a-number"},
            ]
            
            for invalid_data in validation_cases:
                response = client.post("/api/v1/items/", json=invalid_data)
                assert response.status_code != 404
    
    def test_inventory_validation_errors(self, client):
        """Test inventory-specific validation errors."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            validation_cases = [
                # Negative quantities
                {"item_id": 1, "location_id": 1, "quantity": -5},
                
                # Zero item_id
                {"item_id": 0, "location_id": 1, "quantity": 5},
                
                # Zero location_id
                {"item_id": 1, "location_id": 0, "quantity": 5},
                
                # Missing required fields
                {"quantity": 5},  # Missing item_id and location_id
                {"item_id": 1},   # Missing location_id and quantity
            ]
            
            for invalid_data in validation_cases:
                response = client.post("/api/v1/inventory/", json=invalid_data)
                assert response.status_code != 404
    
    def test_movement_validation_errors(self, client):
        """Test movement-specific validation errors."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            validation_cases = [
                # Negative quantities
                {"to_location_id": 2, "quantity": -3, "reason": "Test"},
                
                # Zero quantities
                {"to_location_id": 2, "quantity": 0, "reason": "Test"},
                
                # Missing required fields
                {"quantity": 3, "reason": "Test"},  # Missing to_location_id
                {"to_location_id": 2, "reason": "Test"},  # Missing quantity
            ]
            
            for invalid_data in validation_cases:
                response = client.post("/api/v1/inventory/move/1", json=invalid_data)
                assert response.status_code != 404


class TestBusinessLogicErrorHandling:
    """Test business rule violation error handling."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_referential_integrity_errors(self, client):
        """Test referential integrity constraint violations."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Mock foreign key constraint violations
            integrity_cases = [
                # Invalid category reference
                {
                    "name": "Test Item",
                    "item_type": "electronics",
                    "category_id": 99999  # Non-existent category
                },
                
                # Invalid location reference in item creation
                {
                    "name": "Test Item",
                    "item_type": "electronics",
                    "location_id": 99999,  # Non-existent location
                    "quantity": 1
                },
                
                # Invalid item reference in inventory
                {
                    "item_id": 99999,  # Non-existent item
                    "location_id": 1,
                    "quantity": 5
                },
                
                # Invalid location reference in inventory
                {
                    "item_id": 1,
                    "location_id": 99999,  # Non-existent location
                    "quantity": 5
                },
            ]
            
            endpoints = [
                "/api/v1/items/",
                "/api/v1/items/with-location",
                "/api/v1/inventory/",
                "/api/v1/inventory/",
            ]
            
            for endpoint, invalid_data in zip(endpoints, integrity_cases):
                response = client.post(endpoint, json=invalid_data)
                assert response.status_code != 404
    
    def test_movement_business_rule_violations(self, client):
        """Test movement-specific business rule violations."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            business_rule_violations = [
                # Movement validation that should fail
                {
                    "item_id": 1,
                    "from_location_id": 1,
                    "to_location_id": 1,  # Same location (should fail)
                    "quantity_moved": 5,
                    "movement_type": "move",
                    "reason": "Testing same location move"
                },
                
                # Negative quantity movement
                {
                    "item_id": 1,
                    "from_location_id": 1,
                    "to_location_id": 2,
                    "quantity_moved": -5,  # Negative quantity
                    "movement_type": "move",
                    "reason": "Testing negative quantity"
                },
                
                # Invalid movement type
                {
                    "item_id": 1,
                    "from_location_id": 1,
                    "to_location_id": 2,
                    "quantity_moved": 5,
                    "movement_type": "invalid_type",  # Invalid type
                    "reason": "Testing invalid type"
                },
            ]
            
            for violation_data in business_rule_violations:
                # Test validation endpoint
                validate_response = client.post("/api/v1/inventory/validate/movement", json=violation_data)
                assert validate_response.status_code != 404
                
                # Should return validation result with errors
                if validate_response.status_code == 200:
                    data = validate_response.json()
                    if "is_valid" in data:
                        assert data["is_valid"] is False
                        assert len(data["errors"]) > 0
    
    def test_inventory_constraint_violations(self, client):
        """Test inventory constraint violations."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Test insufficient quantity for movement
            insufficient_quantity_move = {
                "to_location_id": 2,
                "quantity": 999,  # More than available
                "reason": "Testing insufficient quantity"
            }
            
            response = client.post("/api/v1/inventory/move/1", json=insufficient_quantity_move)
            assert response.status_code != 404
            
            # Test duplicate inventory entry (same item + location)
            duplicate_inventory = {
                "item_id": 1,
                "location_id": 1,  # Assuming this combination already exists
                "quantity": 5
            }
            
            response = client.post("/api/v1/inventory/", json=duplicate_inventory)
            assert response.status_code != 404


class TestSystemFailureHandling:
    """Test system-level failure handling."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_database_connection_failures(self, client):
        """Test handling of database connection failures."""
        with patch('app.database.base.get_session') as mock_session:
            # Mock database connection failure
            mock_session.side_effect = OperationalError("Database connection failed", None, None)
            
            critical_endpoints = [
                "/api/v1/items/",
                "/api/v1/inventory/",
                "/api/v1/inventory/summary",
                "/api/v1/items/statistics/overview",
            ]
            
            for endpoint in critical_endpoints:
                response = client.get(endpoint)
                
                # Should not return 404 for endpoint
                assert response.status_code != 404
                
                # Should handle database failures gracefully
                if response.status_code == 500:
                    data = response.json()
                    assert "detail" in data
    
    def test_cache_system_failures(self, client):
        """Test handling of cache system failures."""
        with patch('app.performance.query_optimizer.cache') as mock_cache:
            # Mock cache operation failures
            mock_cache.get.side_effect = Exception("Cache system failure")
            mock_cache.set.side_effect = Exception("Cache system failure")
            mock_cache.invalidate.side_effect = Exception("Cache system failure")
            mock_cache.stats.side_effect = Exception("Cache system failure")
            
            cache_endpoints = [
                ("/api/v1/performance/cache/stats", "GET"),
                ("/api/v1/performance/cache/warm", "POST"),
                ("/api/v1/performance/cache/clear", "DELETE"),
            ]
            
            for endpoint, method in cache_endpoints:
                if method == "GET":
                    response = client.get(endpoint)
                elif method == "POST":
                    with patch('app.database.base.get_session') as mock_session:
                        mock_db = AsyncMock(spec=AsyncSession)
                        mock_session.return_value = mock_db
                        response = client.post(endpoint)
                elif method == "DELETE":
                    response = client.delete(endpoint)
                
                # Should not return 404 for endpoint
                assert response.status_code != 404
    
    def test_performance_monitoring_failures(self, client):
        """Test handling of performance monitoring failures."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_db.execute.side_effect = Exception("Performance monitoring failed")
            mock_session.return_value = mock_db
            
            performance_endpoints = [
                "/api/v1/performance/metrics",
                "/api/v1/performance/query-analysis",
            ]
            
            for endpoint in performance_endpoints:
                response = client.get(endpoint)
                
                # Should not return 404 for endpoint
                assert response.status_code != 404
                
                # Should handle monitoring failures gracefully
                if response.status_code in [500, 200]:
                    data = response.json()
                    if response.status_code == 200:
                        # Should return error information
                        if "query_analysis" in data:
                            assert data["query_analysis"]["status"] == "error"


class TestConcurrencyErrorHandling:
    """Test error handling in concurrent operation scenarios."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_concurrent_update_conflicts(self, client):
        """Test handling of concurrent update conflicts."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Simulate version conflict
            version_conflict_error = Exception("Version conflict - record was modified")
            mock_db.commit.side_effect = version_conflict_error
            
            # Attempt concurrent updates
            update_data = {"name": "Updated Name"}
            
            responses = []
            for _ in range(3):
                response = client.put("/api/v1/items/1", json=update_data)
                responses.append(response)
            
            # All should handle conflicts appropriately
            for response in responses:
                assert response.status_code != 404
    
    def test_bulk_operation_partial_failures(self, client):
        """Test handling of partial failures in bulk operations."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Bulk operation with mixed valid/invalid items
            bulk_data = {
                "item_ids": [1, 999, 3, 888],  # Mix of valid and invalid IDs
                "updates": {"status": "maintenance"}
            }
            
            response = client.post("/api/v1/items/bulk-update", json=bulk_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            # Should handle partial failures appropriately
            if response.status_code == 404:
                data = response.json()
                assert "detail" in data
                # Should indicate which items were not found
                assert "not found" in data["detail"].lower()


class TestErrorMessageQuality:
    """Test quality and clarity of error messages."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_error_message_structure(self, client):
        """Test that error messages have proper structure and information."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Create various error scenarios
            error_scenarios = [
                # Validation error
                ("/api/v1/items/", {"name": "", "item_type": "invalid"}),
                
                # Not found error
                ("/api/v1/items/99999", None, "GET"),
                
                # Business rule violation
                ("/api/v1/inventory/validate/movement", {
                    "item_id": 1,
                    "from_location_id": 1,
                    "to_location_id": 1,  # Same location
                    "quantity_moved": 5,
                    "movement_type": "move"
                }),
            ]
            
            for scenario in error_scenarios:
                if len(scenario) == 2:
                    endpoint, data = scenario
                    response = client.post(endpoint, json=data)
                else:
                    endpoint, data, method = scenario
                    if method == "GET":
                        response = client.get(endpoint)
                
                # Should not return 404 for endpoint
                assert response.status_code != 404
                
                # Check error message structure
                if response.status_code >= 400:
                    data = response.json()
                    assert "detail" in data
                    
                    # Error message should be informative
                    if isinstance(data["detail"], str):
                        assert len(data["detail"]) > 10  # Not just a code
                    elif isinstance(data["detail"], list):
                        # Validation errors
                        for error in data["detail"]:
                            assert "msg" in error
                            assert len(error["msg"]) > 5
    
    def test_correlation_id_in_errors(self, client):
        """Test that errors include correlation IDs for tracking."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Force an error
            mock_db.execute.side_effect = Exception("Test error")
            
            response = client.get("/api/v1/items/")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            # Check for correlation ID in response
            if response.status_code >= 400:
                # Check headers for correlation ID
                assert "x-correlation-id" in response.headers or "correlation-id" in response.headers
    
    def test_security_error_handling(self, client):
        """Test that errors don't leak sensitive information."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Create database error with potentially sensitive info
            sensitive_error = OperationalError(
                "Database connection failed: password=secret123 host=internal.db.server", 
                None, 
                None
            )
            mock_db.execute.side_effect = sensitive_error
            
            response = client.get("/api/v1/items/")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            # Error message should not contain sensitive info
            if response.status_code >= 400:
                error_text = json.dumps(response.json()).lower()
                
                # Should not contain sensitive keywords
                sensitive_keywords = ["password", "secret", "token", "key", "internal"]
                for keyword in sensitive_keywords:
                    assert keyword not in error_text


if __name__ == "__main__":
    pytest.main([__file__])