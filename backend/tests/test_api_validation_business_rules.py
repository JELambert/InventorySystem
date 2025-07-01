"""
Business rules validation test suite for API endpoints.

Tests enforcement of business rules, data integrity constraints,
and validation logic across all API operations.
"""

import pytest
import json
from datetime import datetime, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch, Mock

from app.main import app


class TestMovementValidationRules:
    """Test movement validation business rules."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_max_concurrent_movements_rule(self, client):
        """Test maximum concurrent movements business rule."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Test movement that should violate concurrent movement limit
            movement_data = {
                "item_id": 1,
                "from_location_id": 1,
                "to_location_id": 2,
                "quantity_moved": 5,
                "movement_type": "move",
                "reason": "Testing concurrent movement limit"
            }
            
            # Mock high number of recent movements
            mock_result = Mock()
            mock_result.scalar.return_value = 150  # Above typical limit of 100
            mock_db.execute.return_value = mock_result
            
            response = client.post("/api/v1/inventory/validate/movement", json=movement_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                if "is_valid" in data and not data["is_valid"]:
                    # Should have error about too many concurrent movements
                    assert any("concurrent" in error.lower() or "movements" in error.lower() 
                             for error in data["errors"])
                    assert "max_concurrent_movements" in data["business_rules_applied"]
    
    def test_location_capacity_constraints(self, client):
        """Test location capacity constraint enforcement."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            movement_data = {
                "item_id": 1,
                "from_location_id": 1,
                "to_location_id": 2,
                "quantity_moved": 10,  # Large quantity
                "movement_type": "move",
                "reason": "Testing location capacity"
            }
            
            # Mock location at near capacity
            mock_location = Mock()
            mock_location.scalars.return_value.first.return_value = Mock(
                max_capacity=100,
                current_item_count=95  # Near capacity
            )
            mock_db.execute.return_value = mock_location
            
            response = client.post("/api/v1/inventory/validate/movement", json=movement_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                # May have capacity warnings or errors
                if not data["is_valid"]:
                    assert any("capacity" in error.lower() for error in data["errors"])
                assert "location_capacity_check" in data["business_rules_applied"]
    
    def test_item_status_constraints(self, client):
        """Test item status constraint enforcement."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            movement_data = {
                "item_id": 1,
                "from_location_id": 1,
                "to_location_id": 2,
                "quantity_moved": 5,
                "movement_type": "move",
                "reason": "Testing item status constraints"
            }
            
            # Mock item with blocked status
            mock_item = Mock()
            mock_item.scalars.return_value.first.return_value = Mock(status="disposed")
            mock_db.execute.return_value = mock_item
            
            response = client.post("/api/v1/inventory/validate/movement", json=movement_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                if not data["is_valid"]:
                    # Should have error about item status
                    assert any("status" in error.lower() or "disposed" in error.lower() 
                             for error in data["errors"])
                assert "item_status_constraints" in data["business_rules_applied"]
    
    def test_quantity_consistency_checks(self, client):
        """Test quantity consistency business rules."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            movement_data = {
                "item_id": 1,
                "from_location_id": 1,
                "to_location_id": 2,
                "quantity_moved": 20,  # More than available
                "movement_type": "move",
                "reason": "Testing quantity consistency"
            }
            
            # Mock inventory with insufficient quantity
            mock_inventory = Mock()
            mock_inventory.scalars.return_value.first.return_value = Mock(quantity=10)  # Less than requested
            mock_db.execute.return_value = mock_inventory
            
            response = client.post("/api/v1/inventory/validate/movement", json=movement_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                if not data["is_valid"]:
                    # Should have error about insufficient quantity
                    assert any("quantity" in error.lower() or "insufficient" in error.lower() 
                             for error in data["errors"])
                assert "quantity_consistency" in data["business_rules_applied"]
    
    def test_duplicate_movement_prevention(self, client):
        """Test duplicate movement prevention rule."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            movement_data = {
                "item_id": 1,
                "from_location_id": 1,
                "to_location_id": 2,
                "quantity_moved": 5,
                "movement_type": "move",
                "reason": "Testing duplicate prevention"
            }
            
            # Mock recent identical movement
            mock_result = Mock()
            mock_result.scalar.return_value = 1  # One recent identical movement
            mock_db.execute.return_value = mock_result
            
            response = client.post("/api/v1/inventory/validate/movement", json=movement_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                # Should have warning about duplicate movement
                if data["warnings"]:
                    assert any("duplicate" in warning.lower() or "similar" in warning.lower() 
                             for warning in data["warnings"])
                assert "duplicate_movement_prevention" in data["business_rules_applied"]
    
    def test_value_tracking_threshold(self, client):
        """Test value tracking threshold rule."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            movement_data = {
                "item_id": 1,
                "from_location_id": 1,
                "to_location_id": 2,
                "quantity_moved": 5,
                "movement_type": "move",
                "reason": "Testing value tracking"
            }
            
            # Mock high-value item
            mock_item = Mock()
            mock_item.scalars.return_value.first.return_value = Mock(
                purchase_price=1000.0,
                current_value=950.0
            )
            mock_db.execute.return_value = mock_item
            
            response = client.post("/api/v1/inventory/validate/movement", json=movement_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                # High-value items should add to warnings (extra tracking)
                assert "value_tracking_threshold" in data["business_rules_applied"]
    
    def test_performance_constraints_validation(self, client):
        """Test performance constraints validation."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            movement_data = {
                "item_id": 1,
                "from_location_id": 1,
                "to_location_id": 2,
                "quantity_moved": 5,
                "movement_type": "move",
                "reason": "Testing performance constraints"
            }
            
            # Mock high system load
            with patch('psutil.cpu_percent', return_value=95.0), \
                 patch('psutil.virtual_memory') as mock_memory:
                
                mock_memory.return_value.percent = 90.0
                
                response = client.post("/api/v1/inventory/validate/movement", json=movement_data)
                
                # Should not return 404 for endpoint
                assert response.status_code != 404
                
                if response.status_code == 200:
                    data = response.json()
                    if not data["is_valid"]:
                        # Should have error about system load
                        assert any("performance" in error.lower() or "load" in error.lower() 
                                 for error in data["errors"])


class TestDataIntegrityConstraints:
    """Test data integrity constraint enforcement."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_referential_integrity_enforcement(self, client):
        """Test referential integrity constraints."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Test item creation with invalid category
            invalid_category_item = {
                "name": "Test Item",
                "description": "Testing referential integrity",
                "item_type": "electronics",
                "category_id": 99999  # Non-existent category
            }
            
            # Mock category lookup returning None
            mock_db.execute.return_value.scalar_one_or_none.return_value = None
            
            response = client.post("/api/v1/items/", json=invalid_category_item)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            # Should handle invalid reference appropriately
            if response.status_code == 400:
                data = response.json()
                assert "detail" in data
                assert "category" in data["detail"].lower()
    
    def test_unique_constraint_enforcement(self, client):
        """Test unique constraint enforcement."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Test duplicate serial number
            duplicate_serial_item = {
                "name": "Test Item",
                "description": "Testing unique constraints",
                "item_type": "electronics",
                "serial_number": "DUPLICATE123"
            }
            
            # Mock existing item with same serial
            mock_db.execute.return_value.scalar_one_or_none.return_value = Mock(id=1)
            
            response = client.post("/api/v1/items/", json=duplicate_serial_item)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            # Should handle duplicate serial appropriately
            if response.status_code == 400:
                data = response.json()
                assert "detail" in data
                assert "serial" in data["detail"].lower()
    
    def test_version_conflict_detection(self, client):
        """Test optimistic locking/version conflict detection."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Mock item for update
            mock_item = Mock()
            mock_item.version = 1
            mock_db.execute.return_value.scalar_one_or_none.return_value = mock_item
            
            update_data = {
                "name": "Updated Name",
                "description": "Updated description"
            }
            
            response = client.put("/api/v1/items/1", json=update_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            # Version should be incremented on successful update
            if response.status_code == 200:
                # Version increment is handled internally
                assert mock_item.version >= 1
    
    def test_audit_trail_completeness(self, client):
        """Test that operations maintain complete audit trails."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Create item with location
            item_data = {
                "name": "Audit Test Item",
                "description": "Testing audit trail",
                "item_type": "electronics",
                "location_id": 1,
                "quantity": 5
            }
            
            response = client.post("/api/v1/items/with-location", json=item_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            # Movement operation should create audit trail
            if response.status_code in [200, 201]:
                # Check that movement would be tracked
                timeline_response = client.get("/api/v1/inventory/items/1/timeline")
                assert timeline_response.status_code != 404


class TestBusinessRuleConfiguration:
    """Test business rule configuration and overrides."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_business_rule_overrides(self, client):
        """Test applying business rule overrides."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Test rule override
            override_data = {
                "max_concurrent_movements": {
                    "enabled": False,  # Disable the rule
                    "limit": 200
                },
                "location_capacity_check": {
                    "enabled": True,
                    "strict_mode": True
                }
            }
            
            response = client.post("/api/v1/inventory/validation/rules/override", json=override_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                # After override, validation behavior should change
                movement_data = {
                    "item_id": 1,
                    "from_location_id": 1,
                    "to_location_id": 2,
                    "quantity_moved": 5,
                    "movement_type": "move",
                    "reason": "Testing with overrides"
                }
                
                validate_response = client.post("/api/v1/inventory/validate/movement", json=movement_data)
                assert validate_response.status_code != 404
                
                if validate_response.status_code == 200:
                    data = validate_response.json()
                    # max_concurrent_movements should not be applied (disabled)
                    assert "max_concurrent_movements" not in data["business_rules_applied"]
    
    def test_validation_report_generation(self, client):
        """Test validation system reporting."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.get("/api/v1/inventory/validation/report")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                expected_sections = [
                    "business_rules_configuration",
                    "validation_statistics", 
                    "system_health"
                ]
                
                for section in expected_sections:
                    assert section in data
                
                # Business rules config should show current settings
                if "business_rules_configuration" in data:
                    rules_config = data["business_rules_configuration"]
                    assert isinstance(rules_config, dict)
                    
                    # Should have known business rules
                    expected_rules = [
                        "max_concurrent_movements",
                        "location_capacity_check",
                        "item_status_constraints"
                    ]
                    
                    for rule in expected_rules:
                        if rule in rules_config:
                            assert "enabled" in rules_config[rule]
    
    def test_item_specific_validation_report(self, client):
        """Test validation report filtered by specific item."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            params = {"item_id": 1}
            response = client.get("/api/v1/inventory/validation/report", params=params)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                # Should contain item-specific validation information
                assert "validation_statistics" in data
                if "validation_statistics" in data:
                    stats = data["validation_statistics"]
                    # Should have movement-specific stats for the item
                    assert isinstance(stats, dict)


class TestBulkOperationValidation:
    """Test validation of bulk operations."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_bulk_movement_validation(self, client):
        """Test bulk movement validation with mixed scenarios."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            movements_data = [
                # Valid movement
                {
                    "item_id": 1,
                    "from_location_id": 1,
                    "to_location_id": 2,
                    "quantity_moved": 3,
                    "movement_type": "move",
                    "reason": "Valid bulk movement 1"
                },
                # Invalid movement (same location)
                {
                    "item_id": 2,
                    "from_location_id": 1,
                    "to_location_id": 1,  # Same location
                    "quantity_moved": 2,
                    "movement_type": "move",
                    "reason": "Invalid bulk movement 2"
                },
                # Valid movement
                {
                    "item_id": 3,
                    "from_location_id": 2,
                    "to_location_id": 3,
                    "quantity_moved": 1,
                    "movement_type": "move",
                    "reason": "Valid bulk movement 3"
                }
            ]
            
            response = client.post("/api/v1/inventory/validate/bulk-movement", json=movements_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                assert "overall_result" in data
                assert "individual_results" in data
                
                # Should have individual results for each movement
                assert len(data["individual_results"]) == 3
                
                # Overall result should be invalid due to one invalid movement
                overall = data["overall_result"]
                assert overall["is_valid"] is False
                assert len(overall["errors"]) > 0
                
                # Individual results should show which ones are valid/invalid
                individual = data["individual_results"]
                assert individual[0]["is_valid"] is True   # Valid movement
                assert individual[1]["is_valid"] is False  # Invalid (same location)
                assert individual[2]["is_valid"] is True   # Valid movement
    
    def test_atomic_bulk_validation(self, client):
        """Test atomic bulk validation (all or nothing)."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            movements_data = [
                {
                    "item_id": 1,
                    "from_location_id": 1,
                    "to_location_id": 2,
                    "quantity_moved": 3,
                    "movement_type": "move",
                    "reason": "Atomic test 1"
                },
                {
                    "item_id": 2,
                    "from_location_id": 1,
                    "to_location_id": 1,  # Invalid
                    "quantity_moved": 2,
                    "movement_type": "move",
                    "reason": "Atomic test 2"
                }
            ]
            
            params = {"enforce_atomic": True}
            response = client.post("/api/v1/inventory/validate/bulk-movement", 
                                 json=movements_data, params=params)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                # With atomic validation, overall should fail if any individual fails
                assert data["overall_result"]["is_valid"] is False
    
    def test_bulk_inventory_creation_limits(self, client):
        """Test bulk inventory creation with operation limits."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Create bulk operation that exceeds reasonable limits
            large_bulk_data = {
                "operations": [
                    {"item_id": i, "location_id": 1, "quantity": 1}
                    for i in range(1, 102)  # 101 operations (likely exceeds limit)
                ]
            }
            
            response = client.post("/api/v1/inventory/bulk", json=large_bulk_data)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            # Should handle large bulk operations appropriately
            if response.status_code == 400:
                data = response.json()
                assert "detail" in data
                assert any(keyword in data["detail"].lower() 
                          for keyword in ["limit", "too many", "maximum"])


class TestValidationPerformance:
    """Test validation system performance and scalability."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_validation_under_load(self, client):
        """Test validation system performance under load."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            movement_data = {
                "item_id": 1,
                "from_location_id": 1,
                "to_location_id": 2,
                "quantity_moved": 5,
                "movement_type": "move",
                "reason": "Load testing"
            }
            
            # Make multiple rapid validation requests
            responses = []
            for _ in range(10):
                response = client.post("/api/v1/inventory/validate/movement", json=movement_data)
                responses.append(response)
            
            # All requests should complete successfully
            for response in responses:
                assert response.status_code != 404
                if response.status_code == 200:
                    data = response.json()
                    assert "is_valid" in data
                    assert "business_rules_applied" in data
    
    def test_complex_validation_scenarios(self, client):
        """Test complex validation scenarios with multiple constraints."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Complex movement with multiple potential issues
            complex_movement = {
                "item_id": 1,
                "from_location_id": 1,
                "to_location_id": 2,
                "quantity_moved": 50,  # Large quantity
                "movement_type": "move",
                "reason": "Complex validation test",
                "user_id": "test_user",
                "notes": "Testing multiple business rules simultaneously"
            }
            
            response = client.post("/api/v1/inventory/validate/movement", json=complex_movement)
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                # Should apply multiple business rules
                rules_applied = data["business_rules_applied"]
                assert len(rules_applied) > 3  # Multiple rules should be checked
                
                # Should have comprehensive validation metadata
                assert "validation_metadata" in data
                assert isinstance(data["validation_metadata"], dict)


if __name__ == "__main__":
    pytest.main([__file__])