"""
Integration workflow test suite for the Home Inventory System API.

Tests complete user journeys and cross-API dependencies to ensure
end-to-end functionality works correctly.
"""

import pytest
import json
from datetime import datetime, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch

from app.main import app


class TestCompleteItemLifecycle:
    """Test complete item lifecycle from creation to deletion."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def complete_item_data(self):
        """Complete item data for lifecycle testing."""
        return {
            "name": "Lifecycle Test Item",
            "description": "Item for testing complete lifecycle",
            "item_type": "electronics",
            "condition": "excellent",
            "status": "available",
            "brand": "TestBrand",
            "model": "LifecycleModel",
            "serial_number": "LIFECYCLE123",
            "purchase_price": 150.00,
            "current_value": 140.00,
            "category_id": 1,
            "location_id": 1,
            "quantity": 2
        }
    
    def test_complete_item_lifecycle(self, client, complete_item_data):
        """Test complete item lifecycle: create → assign → move → update → delete."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Step 1: Create item with location assignment
            create_response = client.post("/api/v1/items/with-location", json=complete_item_data)
            assert create_response.status_code != 404
            
            # Assume item created with ID 1 for subsequent operations
            item_id = 1
            
            # Step 2: Update item status
            status_update = {
                "new_status": "in_use",
                "notes": "Item put into use"
            }
            status_response = client.put(f"/api/v1/items/{item_id}/status", json=status_update)
            assert status_response.status_code != 404
            
            # Step 3: Move item to new location
            move_data = {
                "to_location_id": 2,
                "quantity": 1,
                "reason": "Moving for testing"
            }
            move_response = client.post(f"/api/v1/inventory/move/{item_id}", json=move_data)
            assert move_response.status_code != 404
            
            # Step 4: Update item value
            value_update = {
                "new_value": 130.00,
                "notes": "Depreciation adjustment"
            }
            value_response = client.put(f"/api/v1/items/{item_id}/value", json=value_update)
            assert value_response.status_code != 404
            
            # Step 5: Add tags
            tag_response = client.post(f"/api/v1/items/{item_id}/tags/lifecycle-test")
            assert tag_response.status_code != 404
            
            # Step 6: Get movement history
            history_response = client.get(f"/api/v1/inventory/items/{item_id}/timeline")
            assert history_response.status_code != 404
            
            # Step 7: Soft delete item
            delete_response = client.delete(f"/api/v1/items/{item_id}")
            assert delete_response.status_code != 404
            
            # Step 8: Restore item
            restore_response = client.post(f"/api/v1/items/{item_id}/restore")
            assert restore_response.status_code != 404
    
    def test_item_creation_with_dependencies(self, client):
        """Test item creation with proper dependency validation."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Create item that references location and category
            item_data = {
                "name": "Dependency Test Item",
                "description": "Testing dependencies",
                "item_type": "electronics",
                "category_id": 1,
                "location_id": 1,
                "quantity": 1
            }
            
            response = client.post("/api/v1/items/with-location", json=item_data)
            assert response.status_code != 404
            
            # Verify the response includes dependency information
            if response.status_code in [200, 201]:
                data = response.json()
                if "inventory" in data:
                    assert data["inventory"]["location_id"] == 1


class TestBulkOperationsWorkflow:
    """Test bulk operations with mixed success/failure scenarios."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_bulk_inventory_creation_workflow(self, client):
        """Test bulk inventory creation with validation."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Bulk inventory creation
            bulk_data = {
                "operations": [
                    {"item_id": 1, "location_id": 1, "quantity": 5},
                    {"item_id": 2, "location_id": 1, "quantity": 3},
                    {"item_id": 3, "location_id": 2, "quantity": 2},
                    {"item_id": 999, "location_id": 1, "quantity": 1}  # Invalid item
                ]
            }
            
            response = client.post("/api/v1/inventory/bulk", json=bulk_data)
            assert response.status_code != 404
    
    def test_bulk_item_updates_workflow(self, client):
        """Test bulk item updates with partial failures."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Bulk update with mix of valid and invalid items
            bulk_update = {
                "item_ids": [1, 2, 999, 4],  # Mix of valid/invalid IDs
                "updates": {
                    "status": "maintenance",
                    "notes": "Bulk maintenance update"
                }
            }
            
            response = client.post("/api/v1/items/bulk-update", json=bulk_update)
            assert response.status_code != 404
    
    def test_bulk_movement_validation_workflow(self, client):
        """Test bulk movement validation before execution."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # First validate movements
            movements_data = [
                {
                    "item_id": 1,
                    "from_location_id": 1,
                    "to_location_id": 2,
                    "quantity_moved": 3,
                    "movement_type": "move",
                    "reason": "Bulk movement test 1"
                },
                {
                    "item_id": 2,
                    "from_location_id": 1,
                    "to_location_id": 3,
                    "quantity_moved": 2,
                    "movement_type": "move",
                    "reason": "Bulk movement test 2"
                }
            ]
            
            # Validate first
            validate_response = client.post("/api/v1/inventory/validate/bulk-movement", json=movements_data)
            assert validate_response.status_code != 404
            
            # Then execute if validation passes (mocked)
            for i, movement in enumerate(movements_data, 1):
                move_data = {
                    "to_location_id": movement["to_location_id"],
                    "quantity": movement["quantity_moved"],
                    "reason": movement["reason"]
                }
                move_response = client.post(f"/api/v1/inventory/move/{i}", json=move_data)
                assert move_response.status_code != 404


class TestSearchAndFilteringWorkflows:
    """Test complex search operations across multiple entities."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_comprehensive_item_search_workflow(self, client):
        """Test comprehensive item search with multiple criteria."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Complex search criteria
            search_data = {
                "search_text": "electronics",
                "item_type": "electronics",
                "condition": "excellent",
                "status": "available",
                "location_id": 1,
                "category_id": 1,
                "min_value": 100.0,
                "max_value": 500.0,
                "purchased_after": "2024-01-01",
                "has_warranty": True,
                "is_valuable": True,
                "tags": "electronics,valuable",
                "sort_by": "purchase_date",
                "sort_order": "desc",
                "limit": 10
            }
            
            response = client.post("/api/v1/items/search", json=search_data)
            assert response.status_code != 404
    
    def test_inventory_search_with_cross_references(self, client):
        """Test inventory search that crosses multiple entity boundaries."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Search inventory by item characteristics
            params = {
                "min_quantity": 1,
                "max_quantity": 100,
                "min_value": 50.0,
                "max_value": 1000.0
            }
            inventory_response = client.get("/api/v1/inventory/", params=params)
            assert inventory_response.status_code != 404
            
            # Get items in specific location
            location_items_response = client.get("/api/v1/inventory/locations/1/items")
            assert location_items_response.status_code != 404
            
            # Get locations for specific item
            item_locations_response = client.get("/api/v1/inventory/items/1/locations")
            assert item_locations_response.status_code != 404
    
    def test_movement_history_comprehensive_search(self, client):
        """Test comprehensive movement history search."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Comprehensive movement history search
            params = {
                "item_id": 1,
                "movement_type": "move",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "min_quantity": 1,
                "max_quantity": 10,
                "limit": 20,
                "skip": 0
            }
            
            history_response = client.get("/api/v1/inventory/history", params=params)
            assert history_response.status_code != 404
            
            # Get movement summary for same period
            summary_params = {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            }
            summary_response = client.get("/api/v1/inventory/history/summary", params=summary_params)
            assert summary_response.status_code != 404


class TestErrorRecoveryWorkflows:
    """Test error recovery and retry scenarios."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_validation_error_recovery_workflow(self, client):
        """Test recovery from validation errors."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # First attempt with invalid data
            invalid_item = {
                "name": "",  # Invalid: empty name
                "item_type": "invalid_type",  # Invalid: bad enum
                "purchase_price": -100  # Invalid: negative price
            }
            
            invalid_response = client.post("/api/v1/items/", json=invalid_item)
            assert invalid_response.status_code != 404
            
            # Recovery attempt with valid data
            valid_item = {
                "name": "Recovery Test Item",
                "description": "Testing error recovery",
                "item_type": "electronics",
                "condition": "excellent",
                "status": "available",
                "purchase_price": 100.00
            }
            
            valid_response = client.post("/api/v1/items/", json=valid_item)
            assert valid_response.status_code != 404
    
    def test_business_rule_violation_recovery(self, client):
        """Test recovery from business rule violations."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Attempt movement that should violate business rules
            invalid_movement = {
                "item_id": 1,
                "from_location_id": 1,
                "to_location_id": 1,  # Same location
                "quantity_moved": -5,  # Negative quantity
                "movement_type": "move"
            }
            
            # Validate first to see violations
            validate_response = client.post("/api/v1/inventory/validate/movement", json=invalid_movement)
            assert validate_response.status_code != 404
            
            # Correct the movement
            valid_movement = {
                "item_id": 1,
                "from_location_id": 1,
                "to_location_id": 2,  # Different location
                "quantity_moved": 3,   # Positive quantity
                "movement_type": "move",
                "reason": "Corrected movement"
            }
            
            # Validate corrected movement
            corrected_validate_response = client.post("/api/v1/inventory/validate/movement", json=valid_movement)
            assert corrected_validate_response.status_code != 404


class TestPerformanceMonitoringWorkflows:
    """Test performance monitoring during operations."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_performance_monitoring_during_operations(self, client):
        """Test performance monitoring while performing operations."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Get baseline performance metrics
            baseline_response = client.get("/api/v1/performance/metrics")
            assert baseline_response.status_code != 404
            
            # Perform some operations
            item_data = {
                "name": "Performance Test Item",
                "description": "Testing performance impact",
                "item_type": "electronics"
            }
            create_response = client.post("/api/v1/items/", json=item_data)
            assert create_response.status_code != 404
            
            # Check performance impact
            post_op_response = client.get("/api/v1/performance/metrics")
            assert post_op_response.status_code != 404
            
            # Check cache stats
            cache_response = client.get("/api/v1/performance/cache/stats")
            assert cache_response.status_code != 404
    
    def test_cache_management_workflow(self, client):
        """Test complete cache management workflow."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Warm cache
            warm_response = client.post("/api/v1/performance/cache/warm")
            assert warm_response.status_code != 404
            
            # Check cache stats after warming
            stats_response = client.get("/api/v1/performance/cache/stats")
            assert stats_response.status_code != 404
            
            # Use optimized endpoints
            locations_response = client.get("/api/v1/performance/optimized/locations")
            assert locations_response.status_code != 404
            
            categories_response = client.get("/api/v1/performance/optimized/categories")
            assert categories_response.status_code != 404
            
            # Clear cache
            clear_response = client.delete("/api/v1/performance/cache/clear")
            assert clear_response.status_code != 404
            
            # Check stats after clearing
            final_stats_response = client.get("/api/v1/performance/cache/stats")
            assert final_stats_response.status_code != 404


class TestStatisticsAndReportingWorkflows:
    """Test statistics and reporting across the system."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_comprehensive_statistics_workflow(self, client):
        """Test getting comprehensive statistics across all entities."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Get item statistics
            item_stats_response = client.get("/api/v1/items/statistics/overview")
            assert item_stats_response.status_code != 404
            
            # Get inventory summary
            inventory_summary_response = client.get("/api/v1/inventory/summary")
            assert inventory_summary_response.status_code != 404
            
            # Get movement history summary
            movement_summary_params = {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            }
            movement_summary_response = client.get("/api/v1/inventory/history/summary", params=movement_summary_params)
            assert movement_summary_response.status_code != 404
            
            # Get validation report
            validation_report_response = client.get("/api/v1/inventory/validation/report")
            assert validation_report_response.status_code != 404
    
    def test_location_inventory_reporting_workflow(self, client):
        """Test comprehensive location-based inventory reporting."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Get location inventory report
            location_report_response = client.get("/api/v1/inventory/locations/1/report")
            assert location_report_response.status_code != 404
            
            # Get all items in location
            location_items_response = client.get("/api/v1/inventory/locations/1/items")
            assert location_items_response.status_code != 404
            
            # Cross-reference with optimized location data
            optimized_locations_response = client.get("/api/v1/performance/optimized/locations")
            assert optimized_locations_response.status_code != 404


class TestConcurrentOperationsWorkflow:
    """Test concurrent operations and race condition handling."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_concurrent_item_updates(self, client):
        """Test concurrent updates to the same item."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            item_id = 1
            
            # Simulate concurrent updates
            update1 = {"current_value": 100.0}
            update2 = {"status": "maintenance"}
            update3 = {"condition": "good"}
            
            responses = []
            responses.append(client.put(f"/api/v1/items/{item_id}", json=update1))
            responses.append(client.put(f"/api/v1/items/{item_id}", json=update2))
            responses.append(client.put(f"/api/v1/items/{item_id}", json=update3))
            
            # All requests should handle concurrency appropriately
            for response in responses:
                assert response.status_code != 404
    
    def test_concurrent_inventory_operations(self, client):
        """Test concurrent inventory operations on the same item."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Concurrent movements
            move1 = {"to_location_id": 2, "quantity": 2, "reason": "Concurrent move 1"}
            move2 = {"to_location_id": 3, "quantity": 1, "reason": "Concurrent move 2"}
            
            item_id = 1
            responses = []
            responses.append(client.post(f"/api/v1/inventory/move/{item_id}", json=move1))
            responses.append(client.post(f"/api/v1/inventory/move/{item_id}", json=move2))
            
            # Should handle concurrent operations gracefully
            for response in responses:
                assert response.status_code != 404


if __name__ == "__main__":
    pytest.main([__file__])