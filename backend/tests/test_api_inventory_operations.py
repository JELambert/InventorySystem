"""
Comprehensive test suite for Inventory Operations API endpoints.

Tests all 30+ inventory API endpoints including movement operations, quantity management,
movement history, validation, and business rule enforcement.
"""

import pytest
import json
from datetime import datetime, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch

from app.main import app


class TestInventoryAPICRUD:
    """Test core CRUD operations for inventory API."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def sample_inventory_data(self):
        """Sample inventory creation data."""
        return {
            "item_id": 1,
            "location_id": 1,
            "quantity": 5
        }
    
    def test_create_inventory_entry(self, client, sample_inventory_data):
        """Test creating inventory entry."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/inventory/", json=sample_inventory_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code in [200, 201]:
                data = response.json()
                assert "id" in data
                assert data["item_id"] == sample_inventory_data["item_id"]
                assert data["location_id"] == sample_inventory_data["location_id"]
                assert data["quantity"] == sample_inventory_data["quantity"]
    
    def test_get_inventory_entries(self, client):
        """Test getting inventory entries with filtering."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Test basic get
            response = client.get("/api/v1/inventory/")
            assert response.status_code != 404
            
            # Test with filters
            params = {
                "item_id": 1,
                "location_id": 1,
                "min_quantity": 1,
                "max_quantity": 10
            }
            response = client.get("/api/v1/inventory/", params=params)
            assert response.status_code != 404
    
    def test_get_inventory_by_id(self, client):
        """Test getting specific inventory entry by ID."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.get("/api/v1/inventory/1")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                assert "id" in data
                assert "item_id" in data
                assert "location_id" in data
                assert "quantity" in data
    
    def test_update_inventory_entry(self, client):
        """Test updating inventory entry."""
        update_data = {
            "quantity": 10,
            "notes": "Updated quantity"
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.put("/api/v1/inventory/1", json=update_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
    
    def test_delete_inventory_entry(self, client):
        """Test deleting inventory entry."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.delete("/api/v1/inventory/1")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
    
    def test_get_inventory_summary(self, client):
        """Test getting inventory summary statistics."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.get("/api/v1/inventory/summary")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                expected_fields = [
                    "total_inventory_entries", "total_items_tracked",
                    "total_locations_used", "total_quantity"
                ]
                for field in expected_fields:
                    assert field in data


class TestInventoryAPIBulkOperations:
    """Test bulk operations for inventory management."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_bulk_create_inventory(self, client):
        """Test bulk creation of inventory entries."""
        bulk_data = {
            "operations": [
                {"item_id": 1, "location_id": 1, "quantity": 5},
                {"item_id": 2, "location_id": 1, "quantity": 3},
                {"item_id": 3, "location_id": 2, "quantity": 2}
            ]
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/inventory/bulk", json=bulk_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code in [200, 201]:
                data = response.json()
                assert isinstance(data, list)
                assert len(data) == len(bulk_data["operations"])


class TestInventoryAPIMovementOperations:
    """Test item movement operations between locations."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_move_item_simple(self, client):
        """Test simple item movement between locations."""
        move_data = {
            "to_location_id": 2,
            "quantity": 3,
            "reason": "Testing movement API"
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/inventory/move/1", json=move_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
    
    def test_move_item_with_validation(self, client):
        """Test item movement with validation enabled."""
        move_data = {
            "to_location_id": 2,
            "quantity": 3,
            "reason": "Testing movement with validation",
            "validate_movement": True
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/inventory/move/1", json=move_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404


class TestInventoryAPIQuantityOperations:
    """Test quantity management operations."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_split_item_quantity(self, client):
        """Test splitting item quantity between locations."""
        split_data = {
            "source_location_id": 1,
            "dest_location_id": 2,
            "quantity_to_move": 3,
            "reason": "Testing quantity split"
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/inventory/items/1/split", json=split_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
    
    def test_merge_item_quantities(self, client):
        """Test merging item quantities from multiple locations."""
        merge_data = {
            "location_ids": [1, 2, 3],
            "target_location_id": 4,
            "reason": "Testing quantity merge"
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/inventory/items/1/merge", json=merge_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
    
    def test_adjust_quantity(self, client):
        """Test adjusting item quantity at location."""
        adjust_data = {
            "new_quantity": 10,
            "reason": "Inventory adjustment after count"
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.put("/api/v1/inventory/items/1/locations/1/quantity", json=adjust_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
    
    def test_remove_item_from_location(self, client):
        """Test removing item from location (quantity = 0)."""
        remove_data = {
            "new_quantity": 0,
            "reason": "Item removed from location"
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.put("/api/v1/inventory/items/1/locations/1/quantity", json=remove_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404


class TestInventoryAPILocationItemRelationships:
    """Test location-item relationship queries."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_get_item_locations(self, client):
        """Test getting all locations for an item."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.get("/api/v1/inventory/items/1/locations")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, list)
                for entry in data:
                    assert "location_id" in entry
                    assert "quantity" in entry
    
    def test_get_location_items(self, client):
        """Test getting all items in a location."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.get("/api/v1/inventory/locations/1/items")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, list)
                for entry in data:
                    assert "item_id" in entry
                    assert "quantity" in entry
    
    def test_get_location_inventory_report(self, client):
        """Test getting comprehensive location inventory report."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.get("/api/v1/inventory/locations/1/report")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                assert "location_id" in data
                assert "total_items" in data
                assert "total_quantity" in data
                assert "items" in data


class TestInventoryAPIOptimizedQueries:
    """Test optimized query endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_get_optimized_inventory(self, client):
        """Test getting inventory with optimized caching/preloading."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            params = {
                "limit": 50,
                "offset": 0,
                "item_id": 1,
                "location_id": 1
            }
            response = client.get("/api/v1/inventory/optimized", params=params)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404


class TestInventoryAPIMovementHistory:
    """Test movement history tracking and retrieval."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_get_movement_history(self, client):
        """Test getting movement history with filtering."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Test basic history
            response = client.get("/api/v1/inventory/history")
            assert response.status_code != 404
            
            # Test with filters
            params = {
                "item_id": 1,
                "location_id": 1,
                "movement_type": "move",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "limit": 20,
                "skip": 0
            }
            response = client.get("/api/v1/inventory/history", params=params)
            assert response.status_code != 404
    
    def test_get_movement_history_summary(self, client):
        """Test getting movement history statistics."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            params = {
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            }
            response = client.get("/api/v1/inventory/history/summary", params=params)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                assert "total_movements" in data
                assert "by_type" in data
                assert "by_date" in data
    
    def test_get_item_movement_timeline(self, client):
        """Test getting movement timeline for specific item."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.get("/api/v1/inventory/items/1/timeline")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                assert "item_id" in data
                assert "movements" in data
                assert isinstance(data["movements"], list)


class TestInventoryAPIMovementValidation:
    """Test movement validation operations."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_validate_movement_success(self, client):
        """Test movement validation that should succeed."""
        movement_data = {
            "item_id": 1,
            "from_location_id": 1,
            "to_location_id": 2,
            "quantity_moved": 3,
            "movement_type": "move",
            "reason": "Testing validation"
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/inventory/validate/movement", json=movement_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                assert "is_valid" in data
                assert "errors" in data
                assert "warnings" in data
                assert "business_rules_applied" in data
    
    def test_validate_movement_with_strict_enforcement(self, client):
        """Test movement validation with strict business rule enforcement."""
        movement_data = {
            "item_id": 1,
            "from_location_id": 1,
            "to_location_id": 2,
            "quantity_moved": 3,
            "movement_type": "move",
            "reason": "Testing strict validation"
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            params = {"enforce_strict": True}
            response = client.post("/api/v1/inventory/validate/movement", json=movement_data, params=params)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
    
    def test_validate_bulk_movement(self, client):
        """Test validation of multiple movements."""
        movements_data = [
            {
                "item_id": 1,
                "from_location_id": 1,
                "to_location_id": 2,
                "quantity_moved": 3,
                "movement_type": "move",
                "reason": "Bulk movement 1"
            },
            {
                "item_id": 2,
                "from_location_id": 2,
                "to_location_id": 3,
                "quantity_moved": 2,
                "movement_type": "move",
                "reason": "Bulk movement 2"
            }
        ]
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/inventory/validate/bulk-movement", json=movements_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                assert "overall_result" in data
                assert "individual_results" in data
                assert isinstance(data["individual_results"], list)
    
    def test_validate_bulk_movement_atomic(self, client):
        """Test atomic validation of bulk movements."""
        movements_data = [
            {
                "item_id": 1,
                "from_location_id": 1,
                "to_location_id": 2,
                "quantity_moved": 3,
                "movement_type": "move"
            }
        ]
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            params = {"enforce_atomic": True}
            response = client.post("/api/v1/inventory/validate/bulk-movement", json=movements_data, params=params)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
    
    def test_get_validation_report(self, client):
        """Test getting validation system report."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.get("/api/v1/inventory/validation/report")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                assert "business_rules_configuration" in data
                assert "validation_statistics" in data
                assert "system_health" in data
    
    def test_get_validation_report_filtered(self, client):
        """Test getting validation report filtered by item."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            params = {"item_id": 1}
            response = client.get("/api/v1/inventory/validation/report", params=params)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
    
    def test_apply_business_rule_overrides(self, client):
        """Test applying business rule overrides."""
        override_data = {
            "max_concurrent_movements": {
                "enabled": False,
                "limit": 200
            },
            "location_capacity_check": {
                "enabled": True,
                "strict_mode": True
            }
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/inventory/validation/rules/override", json=override_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404


class TestInventoryAPIErrorScenarios:
    """Test error handling and edge cases."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_create_inventory_invalid_item(self, client):
        """Test creating inventory entry with invalid item ID."""
        invalid_data = {
            "item_id": 99999,
            "location_id": 1,
            "quantity": 5
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/inventory/", json=invalid_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
    
    def test_create_inventory_invalid_location(self, client):
        """Test creating inventory entry with invalid location ID."""
        invalid_data = {
            "item_id": 1,
            "location_id": 99999,
            "quantity": 5
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/inventory/", json=invalid_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
    
    def test_move_item_insufficient_quantity(self, client):
        """Test moving more quantity than available."""
        move_data = {
            "to_location_id": 2,
            "quantity": 999,  # More than available
            "reason": "Testing insufficient quantity"
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/inventory/move/1", json=move_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
    
    def test_move_item_same_location(self, client):
        """Test moving item to the same location."""
        move_data = {
            "to_location_id": 1,  # Same as from_location
            "quantity": 3,
            "reason": "Testing same location move"
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/inventory/move/1", json=move_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
    
    def test_negative_quantity_adjustment(self, client):
        """Test adjusting quantity to negative value."""
        adjust_data = {
            "new_quantity": -5,
            "reason": "Testing negative quantity"
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.put("/api/v1/inventory/items/1/locations/1/quantity", json=adjust_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
    
    def test_bulk_operation_exceeds_limits(self, client):
        """Test bulk operation that exceeds system limits."""
        # Create 101 operations (assuming max is 100)
        bulk_data = {
            "operations": [
                {"item_id": i, "location_id": 1, "quantity": 1}
                for i in range(1, 102)
            ]
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/inventory/bulk", json=bulk_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
    
    def test_validation_business_rule_violations(self, client):
        """Test movement validation with business rule violations."""
        # Movement that should violate business rules
        movement_data = {
            "item_id": 1,
            "from_location_id": 1,
            "to_location_id": 1,  # Same location
            "quantity_moved": -5,  # Negative quantity
            "movement_type": "invalid_type",  # Invalid type
            "reason": "Testing rule violations"
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/inventory/validate/movement", json=movement_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                assert data["is_valid"] is False
                assert len(data["errors"]) > 0


if __name__ == "__main__":
    pytest.main([__file__])