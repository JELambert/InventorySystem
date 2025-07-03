"""
Tests for the Item Service.
"""

import pytest
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.services.item_service import ItemService
from app.services.inventory_service import InventoryService
from app.models.item import Item, ItemType, ItemCondition, ItemStatus
from app.models.category import Category
from app.models.location import Location, LocationType
from app.models.inventory import Inventory
from app.schemas.item import (
    ItemCreate, ItemUpdate, ItemSearch, ItemBulkUpdate,
    ItemCreateWithLocation
)
from app.schemas.inventory import InventoryCreate


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
def mock_inventory_service():
    """Create a mock inventory service."""
    service = Mock(spec=InventoryService)
    service.create_inventory_entry = AsyncMock()
    service.update_inventory_entry = AsyncMock()
    service.delete_inventory_entries_for_item = AsyncMock()
    return service


@pytest.fixture
def mock_weaviate_service():
    """Create a mock Weaviate service."""
    service = AsyncMock()
    service.create_item_embedding = AsyncMock(return_value=True)
    service.delete_item_embedding = AsyncMock(return_value=True)
    service.health_check = AsyncMock(return_value=True)
    return service


@pytest.fixture
def sample_item_create():
    """Create sample item creation data."""
    return ItemCreate(
        name="Test Item",
        description="A test item",
        item_type=ItemType.ELECTRONICS,
        condition=ItemCondition.EXCELLENT,
        status=ItemStatus.AVAILABLE,
        brand="TestBrand",
        model="TestModel",
        serial_number="SN123",
        barcode="BC123",
        purchase_price=Decimal("99.99"),
        current_value=Decimal("79.99"),
        purchase_date=date.today(),
        warranty_expiry=date.today(),
        weight=1.5,
        dimensions="10x20x30",
        color="Black",
        category_id=1,
        notes="Test notes",
        tags="tag1,tag2"
    )


@pytest.fixture
def sample_item():
    """Create a sample item model."""
    item = Item(
        id=1,
        name="Test Item",
        description="A test item",
        item_type=ItemType.ELECTRONICS,
        condition=ItemCondition.EXCELLENT,
        status=ItemStatus.AVAILABLE,
        category_id=1,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    item.category = Category(id=1, name="Electronics")
    return item


class TestItemService:
    """Test cases for ItemService."""
    
    @pytest.mark.asyncio
    async def test_create_item_success(
        self, mock_db, mock_inventory_service, mock_weaviate_service, 
        sample_item_create, sample_item
    ):
        """Test successful item creation."""
        # Setup
        service = ItemService(mock_db)
        service.inventory_service = mock_inventory_service
        
        # Mock refresh to add category
        async def mock_refresh(item, attrs):
            if "category" in attrs:
                item.category = Category(id=1, name="Electronics")
        
        mock_db.refresh.side_effect = mock_refresh
        
        with patch('app.services.item_service.get_weaviate_service', return_value=mock_weaviate_service):
            # Execute
            result = await service.create_item(sample_item_create)
            
            # Verify PostgreSQL operations
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            assert mock_db.refresh.call_count >= 1
            
            # Verify Weaviate sync was attempted
            mock_weaviate_service.create_item_embedding.assert_called_once()
            
            # Verify no rollback
            mock_db.rollback.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_create_item_with_location(
        self, mock_db, mock_inventory_service, mock_weaviate_service,
        sample_item_create
    ):
        """Test item creation with location assignment."""
        # Setup
        service = ItemService(mock_db)
        service.inventory_service = mock_inventory_service
        
        # Mock refresh
        async def mock_refresh(item, attrs):
            item.id = 1
            if "category" in attrs:
                item.category = Category(id=1, name="Electronics")
            if "inventory_entries" in attrs:
                item.inventory_entries = [Inventory(location_id=5, quantity=3)]
        
        mock_db.refresh.side_effect = mock_refresh
        
        with patch('app.services.item_service.get_weaviate_service', return_value=mock_weaviate_service):
            # Execute
            result = await service.create_item(
                sample_item_create,
                location_id=5,
                quantity=3
            )
            
            # Verify inventory creation
            mock_inventory_service.create_inventory_entry.assert_called_once()
            call_args = mock_inventory_service.create_inventory_entry.call_args[0][0]
            assert call_args.item_id == 1
            assert call_args.location_id == 5
            assert call_args.quantity == 3
    
    @pytest.mark.asyncio
    async def test_create_item_database_error(
        self, mock_db, mock_inventory_service, sample_item_create
    ):
        """Test item creation with database error."""
        # Setup
        service = ItemService(mock_db)
        service.inventory_service = mock_inventory_service
        
        # Mock database error
        mock_db.commit.side_effect = IntegrityError("", "", "")
        
        # Execute and verify rollback
        with pytest.raises(IntegrityError):
            await service.create_item(sample_item_create)
        
        mock_db.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_item_success(
        self, mock_db, mock_weaviate_service, sample_item
    ):
        """Test successful item update."""
        # Setup
        service = ItemService(mock_db)
        
        # Mock database query
        mock_result = Mock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=sample_item)
        mock_db.execute.return_value = mock_result
        
        update_data = ItemUpdate(
            name="Updated Item",
            description="Updated description"
        )
        
        with patch('app.services.item_service.get_weaviate_service', return_value=mock_weaviate_service):
            # Execute
            result = await service.update_item(1, update_data)
            
            # Verify
            assert result.name == "Updated Item"
            assert result.description == "Updated description"
            mock_db.commit.assert_called_once()
            mock_weaviate_service.create_item_embedding.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_item_not_found(self, mock_db):
        """Test updating non-existent item."""
        # Setup
        service = ItemService(mock_db)
        
        # Mock empty query result
        mock_result = Mock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=None)
        mock_db.execute.return_value = mock_result
        
        update_data = ItemUpdate(name="Updated")
        
        # Execute
        result = await service.update_item(999, update_data)
        
        # Verify
        assert result is None
        mock_db.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_delete_item_success(
        self, mock_db, mock_inventory_service, mock_weaviate_service, sample_item
    ):
        """Test successful item deletion."""
        # Setup
        service = ItemService(mock_db)
        service.inventory_service = mock_inventory_service
        
        # Mock database query
        mock_result = Mock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=sample_item)
        mock_db.execute.return_value = mock_result
        mock_db.delete = AsyncMock()
        
        with patch('app.services.item_service.get_weaviate_service', return_value=mock_weaviate_service):
            # Execute
            result = await service.delete_item(1)
            
            # Verify
            assert result is True
            mock_inventory_service.delete_inventory_entries_for_item.assert_called_once_with(1)
            mock_db.delete.assert_called_once_with(sample_item)
            mock_db.commit.assert_called_once()
            mock_weaviate_service.delete_item_embedding.assert_called_once_with(1)
    
    @pytest.mark.asyncio
    async def test_get_item_with_details(self, mock_db, sample_item):
        """Test getting item with full details."""
        # Setup
        service = ItemService(mock_db)
        
        # Mock database query with relationships
        sample_item.inventory_entries = [
            Inventory(location_id=1, quantity=5, location=Location(name="Room 1"))
        ]
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = AsyncMock(return_value=sample_item)
        mock_db.execute.return_value = mock_result
        
        # Execute
        result = await service.get_item(1)
        
        # Verify
        assert result.id == 1
        assert result.name == "Test Item"
        assert len(result.inventory_entries) == 1
    
    @pytest.mark.asyncio
    async def test_search_items_basic(self, mock_db):
        """Test basic item search."""
        # Setup
        service = ItemService(mock_db)
        
        # Mock search results
        items = [
            Item(id=1, name="Item 1", item_type=ItemType.ELECTRONICS),
            Item(id=2, name="Item 2", item_type=ItemType.ELECTRONICS)
        ]
        
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=items)))
        mock_result.scalar = Mock(return_value=2)  # Total count
        mock_db.execute.return_value = mock_result
        
        search_params = ItemSearch(
            search_term="Item",
            item_types=[ItemType.ELECTRONICS]
        )
        
        # Execute
        result, total = await service.search_items(search_params, skip=0, limit=10)
        
        # Verify
        assert len(result) == 2
        assert total == 2
        assert result[0].name == "Item 1"
    
    @pytest.mark.asyncio
    async def test_bulk_update_items(self, mock_db, mock_weaviate_service):
        """Test bulk item update."""
        # Setup
        service = ItemService(mock_db)
        
        # Mock items
        items = [
            Item(id=1, name="Item 1", status=ItemStatus.AVAILABLE),
            Item(id=2, name="Item 2", status=ItemStatus.AVAILABLE)
        ]
        
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=items)))
        mock_db.execute.return_value = mock_result
        
        bulk_update = ItemBulkUpdate(
            item_ids=[1, 2],
            status=ItemStatus.UNAVAILABLE
        )
        
        with patch('app.services.item_service.get_weaviate_service', return_value=mock_weaviate_service):
            # Execute
            result = await service.bulk_update_items(bulk_update)
            
            # Verify
            assert result["updated"] == 2
            assert result["failed"] == 0
            assert all(item.status == ItemStatus.UNAVAILABLE for item in items)
            mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_sync_to_weaviate_success(
        self, mock_db, mock_weaviate_service, sample_item
    ):
        """Test successful Weaviate synchronization."""
        # Setup
        service = ItemService(mock_db)
        sample_item.category = Category(id=1, name="Electronics")
        sample_item.inventory_entries = [
            Inventory(location=Location(name="Room 1", full_path="House > Room 1"))
        ]
        
        with patch('app.services.item_service.get_weaviate_service', return_value=mock_weaviate_service):
            # Execute
            await service._sync_to_weaviate(sample_item)
            
            # Verify
            mock_weaviate_service.create_item_embedding.assert_called_once()
            call_args = mock_weaviate_service.create_item_embedding.call_args
            assert call_args[0][0] == sample_item
            assert call_args[0][1] == "Electronics"
            assert "House > Room 1" in call_args[0][2]
    
    @pytest.mark.asyncio
    async def test_sync_to_weaviate_service_unavailable(
        self, mock_db, sample_item
    ):
        """Test Weaviate sync when service is unavailable."""
        # Setup
        service = ItemService(mock_db)
        
        # Mock Weaviate service not available
        mock_weaviate = AsyncMock()
        mock_weaviate.health_check.return_value = False
        
        with patch('app.services.item_service.get_weaviate_service', return_value=mock_weaviate):
            # Execute (should not raise exception)
            await service._sync_to_weaviate(sample_item)
            
            # Verify no embedding creation attempted
            mock_weaviate.create_item_embedding.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_items_by_location(self, mock_db):
        """Test getting items by location."""
        # Setup
        service = ItemService(mock_db)
        
        # Mock items with locations
        items = [
            Item(id=1, name="Item 1"),
            Item(id=2, name="Item 2")
        ]
        
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=items)))
        mock_db.execute.return_value = mock_result
        
        # Execute
        result = await service.get_items_by_location(location_id=5)
        
        # Verify
        assert len(result) == 2
        assert result[0].name == "Item 1"