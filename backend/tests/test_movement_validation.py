"""
Test suite for the movement validation system.

Tests business rule validation, movement validation scenarios, and validation reporting.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.movement_validator import (
    MovementValidator,
    MovementValidationResult,
    ValidationError
)
from app.schemas.movement_history import MovementHistoryCreate


class TestMovementValidationResult:
    """Test the MovementValidationResult class."""
    
    def test_validation_result_creation(self):
        """Test basic validation result creation."""
        result = MovementValidationResult(
            is_valid=True,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"],
            business_rules_applied=["rule1", "rule2"],
            validation_metadata={"key": "value"}
        )
        
        assert result.is_valid is True
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
        assert len(result.business_rules_applied) == 2
        assert result.validation_metadata["key"] == "value"
    
    def test_validation_result_defaults(self):
        """Test validation result with default values."""
        result = MovementValidationResult(is_valid=False)
        
        assert result.is_valid is False
        assert result.errors == []
        assert result.warnings == []
        assert result.business_rules_applied == []
        assert result.validation_metadata == {}


class TestMovementValidator:
    """Test the MovementValidator class functionality."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock(spec=AsyncSession)
        return session
    
    @pytest.fixture
    def validator(self, mock_db_session):
        """Create a MovementValidator instance with mocked database."""
        return MovementValidator(mock_db_session)
    
    @pytest.fixture
    def sample_movement_data(self):
        """Create sample movement data for testing."""
        return MovementHistoryCreate(
            item_id=1,
            from_location_id=1,
            to_location_id=2,
            quantity_moved=5,
            movement_type="move",
            reason="Testing movement",
            user_id="test_user"
        )
    
    def test_validator_initialization(self, validator):
        """Test validator initialization with business rules."""
        assert validator.db is not None
        assert isinstance(validator.business_rules, dict)
        
        # Check that default business rules are initialized
        expected_rules = [
            "max_concurrent_movements",
            "location_capacity_check",
            "item_status_constraints",
            "quantity_consistency_check",
            "duplicate_movement_detection",
            "value_tracking_threshold",
            "performance_constraint_check"
        ]
        
        for rule in expected_rules:
            assert rule in validator.business_rules
            assert "enabled" in validator.business_rules[rule]
    
    @pytest.mark.asyncio
    async def test_validate_movement_create_success(self, validator, sample_movement_data):
        """Test successful movement validation."""
        # Mock database queries to return valid data
        with patch.object(validator, '_check_max_concurrent_movements', return_value=True), \
             patch.object(validator, '_check_location_capacity', return_value=True), \
             patch.object(validator, '_check_item_status_constraints', return_value=True), \
             patch.object(validator, '_check_quantity_consistency', return_value=True), \
             patch.object(validator, '_check_duplicate_movement', return_value=True), \
             patch.object(validator, '_check_value_tracking_threshold', return_value=True), \
             patch.object(validator, '_check_performance_constraints', return_value=True):
            
            result = await validator.validate_movement_create(sample_movement_data)
            
            assert result.is_valid is True
            assert len(result.errors) == 0
            assert len(result.business_rules_applied) == 7
    
    @pytest.mark.asyncio
    async def test_validate_movement_create_with_errors(self, validator, sample_movement_data):
        """Test movement validation with business rule violations."""
        # Mock some business rules to fail
        with patch.object(validator, '_check_max_concurrent_movements', return_value=False), \
             patch.object(validator, '_check_location_capacity', return_value=False), \
             patch.object(validator, '_check_item_status_constraints', return_value=True), \
             patch.object(validator, '_check_quantity_consistency', return_value=True), \
             patch.object(validator, '_check_duplicate_movement', return_value=True), \
             patch.object(validator, '_check_value_tracking_threshold', return_value=True), \
             patch.object(validator, '_check_performance_constraints', return_value=True):
            
            result = await validator.validate_movement_create(sample_movement_data)
            
            assert result.is_valid is False
            assert len(result.errors) > 0
            assert len(result.business_rules_applied) == 7
    
    @pytest.mark.asyncio
    async def test_validate_movement_with_disabled_rules(self, validator, sample_movement_data):
        """Test validation with some business rules disabled."""
        # Disable some rules
        validator.business_rules["max_concurrent_movements"]["enabled"] = False
        validator.business_rules["location_capacity_check"]["enabled"] = False
        
        result = await validator.validate_movement_create(sample_movement_data)
        
        # Should not apply disabled rules
        assert "max_concurrent_movements" not in result.business_rules_applied
        assert "location_capacity_check" not in result.business_rules_applied
    
    @pytest.mark.asyncio
    async def test_validate_bulk_movement(self, validator):
        """Test bulk movement validation."""
        movements = [
            MovementHistoryCreate(
                item_id=1,
                from_location_id=1,
                to_location_id=2,
                quantity_moved=5,
                movement_type="move",
                reason="Bulk movement 1"
            ),
            MovementHistoryCreate(
                item_id=2,
                from_location_id=2,
                to_location_id=3,
                quantity_moved=3,
                movement_type="move",
                reason="Bulk movement 2"
            )
        ]
        
        # Mock individual validations
        with patch.object(validator, 'validate_movement_create') as mock_validate:
            mock_validate.side_effect = [
                MovementValidationResult(is_valid=True),
                MovementValidationResult(is_valid=False, errors=["Test error"])
            ]
            
            overall_result, individual_results = await validator.validate_bulk_movement(movements)
            
            assert len(individual_results) == 2
            assert individual_results[0].is_valid is True
            assert individual_results[1].is_valid is False
            assert overall_result.is_valid is False  # One failure makes overall invalid
    
    @pytest.mark.asyncio
    async def test_validate_bulk_movement_atomic(self, validator):
        """Test atomic bulk movement validation."""
        movements = [
            MovementHistoryCreate(
                item_id=1,
                from_location_id=1,
                to_location_id=2,
                quantity_moved=5,
                movement_type="move"
            )
        ]
        
        with patch.object(validator, 'validate_movement_create') as mock_validate:
            mock_validate.return_value = MovementValidationResult(is_valid=True)
            
            overall_result, individual_results = await validator.validate_bulk_movement(
                movements, 
                enforce_atomic_validation=True
            )
            
            assert overall_result.is_valid is True
            assert len(individual_results) == 1
    
    @pytest.mark.asyncio
    async def test_get_validation_report(self, validator):
        """Test validation report generation."""
        with patch.object(validator, '_get_validation_statistics') as mock_stats, \
             patch.object(validator, '_get_recent_validation_failures') as mock_failures:
            
            mock_stats.return_value = {
                "total_validations": 100,
                "successful_validations": 95,
                "failed_validations": 5
            }
            mock_failures.return_value = [
                {"error": "Test error", "timestamp": datetime.utcnow()}
            ]
            
            report = await validator.get_validation_report()
            
            assert "business_rules_configuration" in report
            assert "validation_statistics" in report
            assert "recent_failures" in report
            assert "system_health" in report
    
    @pytest.mark.asyncio
    async def test_apply_business_rule_overrides(self, validator):
        """Test applying business rule overrides."""
        overrides = {
            "max_concurrent_movements": {
                "enabled": False,
                "limit": 200
            },
            "location_capacity_check": {
                "enabled": True,
                "strict_mode": True
            }
        }
        
        await validator.apply_business_rule_overrides(overrides)
        
        assert validator.business_rules["max_concurrent_movements"]["enabled"] is False
        assert validator.business_rules["max_concurrent_movements"]["limit"] == 200
        assert validator.business_rules["location_capacity_check"]["strict_mode"] is True


class TestBusinessRuleValidations:
    """Test individual business rule validation methods."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock(spec=AsyncSession)
        return session
    
    @pytest.fixture
    def validator(self, mock_db_session):
        """Create a MovementValidator instance."""
        return MovementValidator(mock_db_session)
    
    @pytest.mark.asyncio
    async def test_check_max_concurrent_movements(self, validator):
        """Test max concurrent movements check."""
        movement_data = MovementHistoryCreate(
            item_id=1,
            from_location_id=1,
            to_location_id=2,
            quantity_moved=5,
            movement_type="move"
        )
        
        # Mock database query to return movement count
        mock_result = Mock()
        mock_result.scalar.return_value = 50  # Below limit of 100
        validator.db.execute.return_value = mock_result
        
        result = await validator._check_max_concurrent_movements(movement_data)
        assert result is True
        
        # Test with count above limit
        mock_result.scalar.return_value = 150  # Above limit
        result = await validator._check_max_concurrent_movements(movement_data)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_location_capacity(self, validator):
        """Test location capacity check."""
        movement_data = MovementHistoryCreate(
            item_id=1,
            from_location_id=1,
            to_location_id=2,
            quantity_moved=5,
            movement_type="move"
        )
        
        # Mock location data
        mock_location = Mock()
        mock_location.scalars.return_value.first.return_value = Mock(
            max_capacity=100,
            current_item_count=50
        )
        validator.db.execute.return_value = mock_location
        
        result = await validator._check_location_capacity(movement_data)
        assert result is True
        
        # Test with location at capacity
        mock_location.scalars.return_value.first.return_value.current_item_count = 95
        result = await validator._check_location_capacity(movement_data)
        assert result is True  # Still has room for 5 items
        
        # Test with location over capacity
        mock_location.scalars.return_value.first.return_value.current_item_count = 98
        result = await validator._check_location_capacity(movement_data)
        assert result is False  # Would exceed capacity
    
    @pytest.mark.asyncio
    async def test_check_item_status_constraints(self, validator):
        """Test item status constraints check."""
        movement_data = MovementHistoryCreate(
            item_id=1,
            from_location_id=1,
            to_location_id=2,
            quantity_moved=5,
            movement_type="move"
        )
        
        # Mock item with allowed status
        mock_item = Mock()
        mock_item.scalars.return_value.first.return_value = Mock(status="available")
        validator.db.execute.return_value = mock_item
        
        result = await validator._check_item_status_constraints(movement_data)
        assert result is True
        
        # Test with blocked status
        mock_item.scalars.return_value.first.return_value.status = "disposed"
        result = await validator._check_item_status_constraints(movement_data)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_quantity_consistency(self, validator):
        """Test quantity consistency check."""
        movement_data = MovementHistoryCreate(
            item_id=1,
            from_location_id=1,
            to_location_id=2,
            quantity_moved=5,
            movement_type="move"
        )
        
        # Mock inventory entry with sufficient quantity
        mock_inventory = Mock()
        mock_inventory.scalars.return_value.first.return_value = Mock(quantity=10)
        validator.db.execute.return_value = mock_inventory
        
        result = await validator._check_quantity_consistency(movement_data)
        assert result is True
        
        # Test with insufficient quantity
        mock_inventory.scalars.return_value.first.return_value.quantity = 3
        result = await validator._check_quantity_consistency(movement_data)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_duplicate_movement_detection(self, validator):
        """Test duplicate movement detection."""
        movement_data = MovementHistoryCreate(
            item_id=1,
            from_location_id=1,
            to_location_id=2,
            quantity_moved=5,
            movement_type="move"
        )
        
        # Mock no recent identical movements
        mock_result = Mock()
        mock_result.scalar.return_value = 0
        validator.db.execute.return_value = mock_result
        
        result = await validator._check_duplicate_movement(movement_data)
        assert result is True
        
        # Test with recent duplicate
        mock_result.scalar.return_value = 1
        result = await validator._check_duplicate_movement(movement_data)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_value_tracking_threshold(self, validator):
        """Test value tracking threshold check."""
        movement_data = MovementHistoryCreate(
            item_id=1,
            from_location_id=1,
            to_location_id=2,
            quantity_moved=5,
            movement_type="move"
        )
        
        # Mock high-value item
        mock_item = Mock()
        mock_item.scalars.return_value.first.return_value = Mock(
            purchase_price=1000.0,
            current_value=950.0
        )
        validator.db.execute.return_value = mock_item
        
        # Should pass for high-value items (adds to warnings, not errors)
        result = await validator._check_value_tracking_threshold(movement_data)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_performance_constraints(self, validator):
        """Test performance constraints check."""
        movement_data = MovementHistoryCreate(
            item_id=1,
            from_location_id=1,
            to_location_id=2,
            quantity_moved=5,
            movement_type="move"
        )
        
        # Mock acceptable system load
        with patch('psutil.cpu_percent', return_value=30.0), \
             patch('psutil.virtual_memory') as mock_memory:
            
            mock_memory.return_value.percent = 40.0
            
            result = await validator._check_performance_constraints(movement_data)
            assert result is True
        
        # Test with high system load
        with patch('psutil.cpu_percent', return_value=95.0), \
             patch('psutil.virtual_memory') as mock_memory:
            
            mock_memory.return_value.percent = 90.0
            
            result = await validator._check_performance_constraints(movement_data)
            assert result is False


class TestValidationError:
    """Test the ValidationError exception class."""
    
    def test_validation_error_creation(self):
        """Test ValidationError creation."""
        error = ValidationError(
            message="Validation failed",
            error_code="BUSINESS_RULE_VIOLATION",
            details={"rule": "max_capacity"}
        )
        
        assert str(error) == "Validation failed"
        assert error.message == "Validation failed"
        assert error.error_code == "BUSINESS_RULE_VIOLATION"
        assert error.details["rule"] == "max_capacity"


class TestBusinessRuleValidation:
    """Test business rule validation functionality."""
    
    def test_business_rule_application(self):
        """Test business rule application and tracking."""
        result = MovementValidationResult(is_valid=True)
        
        # Test adding business rules
        result.add_business_rule("max_concurrent_movements")
        result.add_business_rule("location_capacity_check")
        
        assert "max_concurrent_movements" in result.business_rules_applied
        assert "location_capacity_check" in result.business_rules_applied
        assert len(result.business_rules_applied) == 2


if __name__ == "__main__":
    pytest.main([__file__])