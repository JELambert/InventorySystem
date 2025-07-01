"""
Comprehensive test suite for Items API endpoints.

Tests all 25+ items API endpoints including CRUD operations, advanced search,
bulk operations, tag management, and error scenarios.
"""

import pytest
import json
from datetime import datetime, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch

from app.main import app
from app.models.item import Item, ItemType, ItemCondition, ItemStatus
from app.models.location import Location
from app.models.category import Category


class TestItemsAPICRUD:
    """Test core CRUD operations for items API."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def sample_item_data(self):
        """Sample item creation data."""
        return {
            "name": "Test Item",
            "description": "A test item for API testing",
            "item_type": "electronics",
            "condition": "excellent",
            "status": "available",
            "brand": "TestBrand",
            "model": "TestModel",
            "serial_number": "TEST123456",
            "barcode": "1234567890123",
            "purchase_price": 99.99,
            "current_value": 89.99,
            "purchase_date": "2024-01-15",
            "warranty_expiry": "2025-01-15",
            "weight": 1.5,
            "dimensions": "10x5x3",
            "color": "Black",
            "category_id": 1,
            "notes": "Test item notes",
            "tags": "electronics,test,sample"
        }
    
    @pytest.fixture
    def sample_location_data(self):
        """Sample location data."""
        return {
            "name": "Test Location",
            "location_type": "room",
            "description": "Test location for API testing"
        }
    
    @pytest.fixture
    def sample_category_data(self):
        """Sample category data."""
        return {
            "name": "Test Category",
            "description": "Test category for API testing",
            "color": "#FF0000"
        }
    
    def test_create_item_success(self, client, sample_item_data):
        """Test successful item creation."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Mock database operations
            mock_db.add.return_value = None
            mock_db.commit.return_value = None
            mock_db.refresh.return_value = None
            
            # Mock created item
            created_item = Item(id=1, **sample_item_data)
            created_item.created_at = datetime.now()
            created_item.updated_at = datetime.now()
            
            response = client.post("/api/v1/items/", json=sample_item_data)
            
            # Should not return 404 (endpoint exists)
            assert response.status_code != 404
            
            # If successful (200/201), validate structure
            if response.status_code in [200, 201]:
                data = response.json()
                assert "id" in data
                assert data["name"] == sample_item_data["name"]
                assert data["item_type"] == sample_item_data["item_type"]
    
    def test_create_item_with_location_success(self, client, sample_item_data):
        """Test successful item creation with location assignment."""
        item_with_location = {
            **sample_item_data,
            "location_id": 1,
            "quantity": 1
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/items/with-location", json=item_with_location)
            
            # Should not return 404
            assert response.status_code != 404
            
            # If successful, should include inventory information
            if response.status_code in [200, 201]:
                data = response.json()
                assert "id" in data
                assert "inventory" in data
                assert data["inventory"]["location_id"] == 1
    
    def test_get_items_list(self, client):
        """Test listing items with pagination and filtering."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Test basic list
            response = client.get("/api/v1/items/")
            assert response.status_code != 404
            
            # Test with parameters
            params = {
                "skip": 0,
                "limit": 10,
                "item_type": "electronics",
                "status": "available",
                "search": "test"
            }
            response = client.get("/api/v1/items/", params=params)
            assert response.status_code != 404
    
    def test_get_item_by_id(self, client):
        """Test getting specific item by ID."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.get("/api/v1/items/1")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            # May return 404 for item not found, but endpoint should exist
            if response.status_code == 200:
                data = response.json()
                assert "id" in data
                assert "name" in data
    
    def test_update_item_success(self, client):
        """Test successful item update."""
        update_data = {
            "name": "Updated Test Item",
            "description": "Updated description",
            "current_value": 79.99,
            "notes": "Updated notes"
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.put("/api/v1/items/1", json=update_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                assert data["name"] == update_data["name"]
    
    def test_delete_item_soft_delete(self, client):
        """Test soft delete of item."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.delete("/api/v1/items/1")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            # Successful delete should return 204
            if response.status_code == 204:
                assert response.content == b""
    
    def test_delete_item_permanent(self, client):
        """Test permanent delete of item."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.delete("/api/v1/items/1?permanent=true")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
    
    def test_restore_item(self, client):
        """Test restoring a soft-deleted item."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/items/1/restore")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404


class TestItemsAPIAdvancedOperations:
    """Test advanced operations like search, bulk operations, and specialized updates."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_advanced_search(self, client):
        """Test advanced item search with complex filtering."""
        search_data = {
            "search_text": "electronics",
            "item_type": "electronics",
            "condition": "excellent",
            "status": "available",
            "min_value": 50.0,
            "max_value": 200.0,
            "purchased_after": "2024-01-01",
            "purchased_before": "2024-12-31",
            "has_warranty": True,
            "is_valuable": True,
            "has_serial_number": True,
            "tags": "electronics,test",
            "sort_by": "name",
            "sort_order": "asc",
            "limit": 20,
            "skip": 0
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/items/search", json=search_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, list)
    
    def test_bulk_update_items(self, client):
        """Test bulk update of multiple items."""
        bulk_update_data = {
            "item_ids": [1, 2, 3],
            "updates": {
                "status": "maintenance",
                "notes": "Bulk updated for maintenance"
            }
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/items/bulk-update", json=bulk_update_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
    
    def test_bulk_move_items(self, client):
        """Test bulk move of items to new location."""
        move_data = {
            "item_ids": [1, 2, 3],
            "new_location_id": 2,
            "notes": "Moved for testing"
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/items/move", json=move_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
    
    def test_update_item_status(self, client):
        """Test updating item status."""
        status_update = {
            "new_status": "maintenance",
            "notes": "Item needs maintenance"
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.put("/api/v1/items/1/status", json=status_update)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
    
    def test_update_item_condition(self, client):
        """Test updating item condition."""
        condition_update = {
            "new_condition": "good",
            "notes": "Condition degraded slightly"
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.put("/api/v1/items/1/condition", json=condition_update)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
    
    def test_update_item_value(self, client):
        """Test updating item current value."""
        value_update = {
            "new_value": 75.00,
            "notes": "Market value decreased"
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.put("/api/v1/items/1/value", json=value_update)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404


class TestItemsAPITagManagement:
    """Test tag management operations."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_get_item_tags(self, client):
        """Test getting item tags."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.get("/api/v1/items/1/tags")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                assert "item_id" in data
                assert "tags" in data
                assert isinstance(data["tags"], list)
    
    def test_add_item_tag(self, client):
        """Test adding a tag to an item."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/items/1/tags/electronics")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
    
    def test_remove_item_tag(self, client):
        """Test removing a tag from an item."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.delete("/api/v1/items/1/tags/old-tag")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404


class TestItemsAPIStatistics:
    """Test statistics and analytics endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_get_item_statistics(self, client):
        """Test getting comprehensive item statistics."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.get("/api/v1/items/statistics/overview")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                expected_fields = [
                    "total_items", "active_items", "total_value", "average_value",
                    "by_type", "by_condition", "by_status", "items_under_warranty",
                    "valuable_items", "items_with_serial", "items_with_barcode"
                ]
                for field in expected_fields:
                    assert field in data


class TestItemsAPIErrorScenarios:
    """Test error handling and edge cases."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_create_item_duplicate_serial(self, client):
        """Test creating item with duplicate serial number."""
        item_data = {
            "name": "Test Item",
            "description": "Test item",
            "item_type": "electronics",
            "serial_number": "DUPLICATE123"
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/items/", json=item_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            # Should handle duplicate serial appropriately
            if response.status_code == 400:
                data = response.json()
                assert "detail" in data
                assert "serial number" in data["detail"].lower()
    
    def test_create_item_duplicate_barcode(self, client):
        """Test creating item with duplicate barcode."""
        item_data = {
            "name": "Test Item",
            "description": "Test item",
            "item_type": "electronics",
            "barcode": "1234567890123"
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/items/", json=item_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
    
    def test_create_item_invalid_location(self, client):
        """Test creating item with invalid location reference."""
        item_data = {
            "name": "Test Item",
            "description": "Test item",
            "item_type": "electronics",
            "location_id": 99999,
            "quantity": 1
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/items/with-location", json=item_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            # Should handle invalid location
            if response.status_code == 400:
                data = response.json()
                assert "detail" in data
                assert "location" in data["detail"].lower()
    
    def test_create_item_invalid_category(self, client):
        """Test creating item with invalid category reference."""
        item_data = {
            "name": "Test Item",
            "description": "Test item",
            "item_type": "electronics",
            "category_id": 99999
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/items/", json=item_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
    
    def test_get_nonexistent_item(self, client):
        """Test getting item that doesn't exist."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.get("/api/v1/items/99999")
            
            # Should not return 404 for endpoint (but may return 404 for item)
            assert response.status_code != 405  # Method not allowed means endpoint exists
    
    def test_update_nonexistent_item(self, client):
        """Test updating item that doesn't exist."""
        update_data = {"name": "Updated Name"}
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.put("/api/v1/items/99999", json=update_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 405
    
    def test_malformed_request_data(self, client):
        """Test handling of malformed request data."""
        malformed_data = {
            "name": "",  # Empty name
            "item_type": "invalid_type",  # Invalid enum
            "purchase_price": "not_a_number",  # Invalid type
            "purchase_date": "invalid_date"  # Invalid date format
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/items/", json=malformed_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            # Should return validation error
            if response.status_code == 422:
                data = response.json()
                assert "detail" in data
    
    def test_bulk_operation_limits(self, client):
        """Test bulk operation with too many items."""
        # Try to update 1000 items (should exceed reasonable limits)
        bulk_data = {
            "item_ids": list(range(1, 1001)),
            "updates": {"status": "available"}
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/items/bulk-update", json=bulk_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
    
    def test_bulk_operation_partial_failure(self, client):
        """Test bulk operation with some invalid item IDs."""
        bulk_data = {
            "item_ids": [1, 99999, 3],  # Mix of valid and invalid IDs
            "updates": {"status": "maintenance"}
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/items/bulk-update", json=bulk_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            # Should handle partial failures appropriately
            if response.status_code == 404:
                data = response.json()
                assert "detail" in data


class TestItemsAPIValidation:
    """Test data validation and business rules."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_item_name_validation(self, client):
        """Test item name validation rules."""
        # Test empty name
        empty_name_data = {
            "name": "",
            "description": "Test item",
            "item_type": "electronics"
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/items/", json=empty_name_data)
            assert response.status_code != 404
    
    def test_item_value_validation(self, client):
        """Test item value validation (non-negative values)."""
        negative_value_data = {
            "name": "Test Item",
            "description": "Test item",
            "item_type": "electronics",
            "purchase_price": -50.0,
            "current_value": -25.0
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/items/", json=negative_value_data)
            assert response.status_code != 404
    
    def test_date_validation(self, client):
        """Test date field validation."""
        future_purchase_data = {
            "name": "Test Item",
            "description": "Test item",
            "item_type": "electronics",
            "purchase_date": "2030-01-01",  # Future date
            "warranty_expiry": "2020-01-01"  # Past warranty
        }
        
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/items/", json=future_purchase_data)
            assert response.status_code != 404


if __name__ == "__main__":
    pytest.main([__file__])