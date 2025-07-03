"""
Tests for the Movement Service.
"""

import pytest
from datetime import datetime, timedelta, date
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.movement_service import MovementService
from app.models.item_movement_history import ItemMovementHistory
from app.models.item import Item, ItemType, ItemStatus
from app.models.location import Location, LocationType
from app.models.inventory import Inventory
from app.schemas.movement_history import (
    MovementHistoryCreate, MovementHistorySearch, BulkMovementCreate,
    MovementHistorySummary
)

# Movement types as strings
class MovementType:
    ADD = "add"
    REMOVE = "remove"
    TRANSFER = "transfer"
    ADJUST = "adjust"


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock(spec=AsyncSession)
    db.add = Mock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    db.scalar_one_or_none = AsyncMock()
    db.scalars = AsyncMock()
    return db


@pytest.fixture
def sample_item():
    """Create a sample item."""
    return Item(
        id=1,
        name="Test Item",
        item_type=ItemType.ELECTRONICS,
        status=ItemStatus.AVAILABLE
    )


@pytest.fixture
def sample_locations():
    """Create sample locations."""
    return {
        "from": Location(id=1, name="Storage Room", location_type=LocationType.ROOM),
        "to": Location(id=2, name="Office", location_type=LocationType.ROOM)
    }


@pytest.fixture
def sample_movement_create():
    """Create sample movement data."""
    return MovementHistoryCreate(
        item_id=1,
        from_location_id=1,
        to_location_id=2,
        quantity_moved=5,
        quantity_before=10,
        quantity_after=5,
        movement_type=MovementType.TRANSFER,
        reason="Office setup",
        notes="Moving items to new office",
        estimated_value=Decimal("500.00"),
        user_id="user123",
        system_notes="Automated transfer"
    )


@pytest.fixture
def sample_movement_history():
    """Create sample movement history entry."""
    return ItemMovementHistory(
        id=1,
        item_id=1,
        from_location_id=1,
        to_location_id=2,
        quantity_moved=5,
        quantity_before=10,
        quantity_after=5,
        movement_type=MovementType.TRANSFER,
        reason="Office setup",
        timestamp=datetime.now()
    )


class TestMovementService:
    """Test cases for MovementService."""
    
    @pytest.mark.asyncio
    async def test_record_movement_success(
        self, mock_db, sample_item, sample_locations, sample_movement_create
    ):
        """Test successful movement recording."""
        # Setup
        service = MovementService(mock_db)
        
        # Mock item and location queries
        mock_results = []
        
        # Item query result
        item_result = Mock()
        item_result.scalar_one_or_none.return_value = sample_item
        mock_results.append(item_result)
        
        # From location query result
        from_loc_result = Mock()
        from_loc_result.scalar_one_or_none.return_value = sample_locations["from"]
        mock_results.append(from_loc_result)
        
        # To location query result
        to_loc_result = Mock()
        to_loc_result.scalar_one_or_none.return_value = sample_locations["to"]
        mock_results.append(to_loc_result)
        
        mock_db.execute.side_effect = mock_results
        
        # Execute
        result = await service.record_movement(sample_movement_create)
        
        # Verify
        assert mock_db.execute.call_count == 3  # Item + 2 locations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        
        # Verify movement data
        movement_added = mock_db.add.call_args[0][0]
        assert movement_added.item_id == 1
        assert movement_added.from_location_id == 1
        assert movement_added.to_location_id == 2
        assert movement_added.quantity_moved == 5
    
    @pytest.mark.asyncio
    async def test_record_movement_item_not_found(
        self, mock_db, sample_movement_create
    ):
        """Test movement recording with non-existent item."""
        # Setup
        service = MovementService(mock_db)
        
        # Mock empty item query
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Execute and verify
        with pytest.raises(ValueError) as exc_info:
            await service.record_movement(sample_movement_create)
        
        assert "Item with ID 1 not found" in str(exc_info.value)
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_record_movement_location_not_found(
        self, mock_db, sample_item, sample_movement_create
    ):
        """Test movement recording with non-existent location."""
        # Setup
        service = MovementService(mock_db)
        
        # Mock queries
        mock_results = []
        
        # Item exists
        item_result = Mock()
        item_result.scalar_one_or_none.return_value = sample_item
        mock_results.append(item_result)
        
        # From location doesn't exist
        loc_result = Mock()
        loc_result.scalar_one_or_none.return_value = None
        mock_results.append(loc_result)
        
        mock_db.execute.side_effect = mock_results
        
        # Execute and verify
        with pytest.raises(ValueError) as exc_info:
            await service.record_movement(sample_movement_create)
        
        assert "From location with ID 1 not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_record_item_creation(
        self, mock_db, sample_item, sample_locations
    ):
        """Test recording item creation movement."""
        # Setup
        service = MovementService(mock_db)
        
        # Mock queries
        mock_results = []
        
        # Item query
        item_result = Mock()
        item_result.scalar_one_or_none.return_value = sample_item
        mock_results.append(item_result)
        
        # Location query
        loc_result = Mock()
        loc_result.scalar_one_or_none.return_value = sample_locations["to"]
        mock_results.append(loc_result)
        
        mock_db.execute.side_effect = mock_results
        
        # Execute
        result = await service.record_item_creation(
            item_id=1,
            location_id=2,
            quantity=10,
            reason="Initial stock",
            user_id="user123"
        )
        
        # Verify
        movement_added = mock_db.add.call_args[0][0]
        assert movement_added.item_id == 1
        assert movement_added.from_location_id is None
        assert movement_added.to_location_id == 2
        assert movement_added.quantity_moved == 10
        assert movement_added.quantity_before == 0
        assert movement_added.quantity_after == 10
        assert movement_added.movement_type == MovementType.ADD
    
    @pytest.mark.asyncio
    async def test_record_item_removal(
        self, mock_db, sample_item, sample_locations
    ):
        """Test recording item removal movement."""
        # Setup
        service = MovementService(mock_db)
        
        # Mock queries
        mock_results = []
        
        # Item query
        item_result = Mock()
        item_result.scalar_one_or_none.return_value = sample_item
        mock_results.append(item_result)
        
        # Location query
        loc_result = Mock()
        loc_result.scalar_one_or_none.return_value = sample_locations["from"]
        mock_results.append(loc_result)
        
        mock_db.execute.side_effect = mock_results
        
        # Execute
        result = await service.record_item_removal(
            item_id=1,
            location_id=1,
            quantity=5,
            quantity_before=10,
            reason="Damaged",
            user_id="user123"
        )
        
        # Verify
        movement_added = mock_db.add.call_args[0][0]
        assert movement_added.from_location_id == 1
        assert movement_added.to_location_id is None
        assert movement_added.quantity_moved == 5
        assert movement_added.quantity_before == 10
        assert movement_added.quantity_after == 5
        assert movement_added.movement_type == MovementType.REMOVE
    
    @pytest.mark.asyncio
    async def test_get_movement_history_for_item(
        self, mock_db, sample_movement_history
    ):
        """Test getting movement history for an item."""
        # Setup
        service = MovementService(mock_db)
        
        # Mock query result
        movements = [sample_movement_history]
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=movements)))
        mock_db.execute.return_value = mock_result
        
        # Execute
        result = await service.get_movement_history_for_item(
            item_id=1,
            skip=0,
            limit=10
        )
        
        # Verify
        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].item_id == 1
    
    @pytest.mark.asyncio
    async def test_search_movements(self, mock_db, sample_movement_history):
        """Test searching movement history."""
        # Setup
        service = MovementService(mock_db)
        
        # Mock search results
        movements = [sample_movement_history]
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=movements)))
        mock_result.scalar = Mock(return_value=1)  # Total count
        mock_db.execute.return_value = mock_result
        
        search_params = MovementHistorySearch(
            item_ids=[1],
            movement_types=[MovementType.TRANSFER],
            date_from=datetime.now() - timedelta(days=7),
            date_to=datetime.now()
        )
        
        # Execute
        results, total = await service.search_movements(search_params, skip=0, limit=10)
        
        # Verify
        assert len(results) == 1
        assert total == 1
        assert results[0].movement_type == MovementType.TRANSFER
    
    @pytest.mark.asyncio
    async def test_get_movement_summary(self, mock_db):
        """Test getting movement summary statistics."""
        # Setup
        service = MovementService(mock_db)
        
        # Mock aggregation results
        mock_results = []
        
        # Total movements count
        count_result = Mock()
        count_result.scalar = Mock(return_value=100)
        mock_results.append(count_result)
        
        # Movement type stats
        type_stats = [
            (MovementType.ADD, 30),
            (MovementType.REMOVE, 20),
            (MovementType.TRANSFER, 45),
            (MovementType.ADJUST, 5)
        ]
        type_result = Mock()
        type_result.all = Mock(return_value=type_stats)
        mock_results.append(type_result)
        
        # Total value moved
        value_result = Mock()
        value_result.scalar = Mock(return_value=Decimal("10000.00"))
        mock_results.append(value_result)
        
        # Most moved items
        item_stats = [
            (1, "Item 1", 25),
            (2, "Item 2", 20)
        ]
        items_result = Mock()
        items_result.all = Mock(return_value=item_stats)
        mock_results.append(items_result)
        
        # Active locations
        location_stats = [
            (1, "Storage", 50),
            (2, "Office", 40)
        ]
        locations_result = Mock()
        locations_result.all = Mock(return_value=location_stats)
        mock_results.append(locations_result)
        
        mock_db.execute.side_effect = mock_results
        
        # Execute
        summary = await service.get_movement_summary(
            date_from=datetime.now() - timedelta(days=30),
            date_to=datetime.now()
        )
        
        # Verify
        assert summary.total_movements == 100
        assert summary.movements_by_type[MovementType.ADD] == 30
        assert summary.movements_by_type[MovementType.TRANSFER] == 45
        assert summary.total_value_moved == Decimal("10000.00")
        assert len(summary.most_moved_items) == 2
        assert len(summary.most_active_locations) == 2
    
    @pytest.mark.asyncio
    async def test_bulk_record_movements(
        self, mock_db, sample_item, sample_locations
    ):
        """Test bulk movement recording."""
        # Setup
        service = MovementService(mock_db)
        
        # Mock validation queries
        mock_db.execute.return_value.scalars.return_value.all.return_value = [sample_item]
        
        bulk_data = BulkMovementCreate(
            movements=[
                MovementHistoryCreate(
                    item_id=1,
                    from_location_id=1,
                    to_location_id=2,
                    quantity_moved=5,
                    quantity_before=10,
                    quantity_after=5,
                    movement_type=MovementType.TRANSFER
                )
            ]
        )
        
        # Mock record_movement
        with patch.object(service, 'record_movement', return_value=sample_movement_history):
            # Execute
            results = await service.bulk_record_movements(bulk_data)
            
            # Verify
            assert results["success"] == 1
            assert results["failed"] == 0
            assert len(results["errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_get_item_movement_timeline(
        self, mock_db, sample_item, sample_movement_history
    ):
        """Test getting item movement timeline."""
        # Setup
        service = MovementService(mock_db)
        
        # Mock item query
        item_result = Mock()
        item_result.scalar_one_or_none.return_value = sample_item
        
        # Mock movements query
        movements = [sample_movement_history]
        movements_result = Mock()
        movements_result.scalars = Mock(return_value=Mock(all=Mock(return_value=movements)))
        
        mock_db.execute.side_effect = [item_result, movements_result]
        
        # Execute
        timeline = await service.get_item_movement_timeline(item_id=1)
        
        # Verify
        assert timeline.item_id == 1
        assert timeline.item_name == "Test Item"
        assert len(timeline.movements) == 1
        assert timeline.total_movements == 1