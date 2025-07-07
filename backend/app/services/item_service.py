"""
Item Service for managing items with dual-write to PostgreSQL and Weaviate.

This service implements the dual-write pattern where PostgreSQL is the source of truth
and Weaviate provides semantic search capabilities.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, and_, or_, desc, asc

from app.models.item import Item, ItemType, ItemCondition, ItemStatus
from app.models.location import Location
from app.models.category import Category
from app.models.inventory import Inventory
from app.schemas.item import (
    ItemCreate, ItemCreateWithLocation, ItemUpdate, ItemResponse,
    ItemSearch, ItemBulkUpdate
)
from app.services.weaviate_service import get_weaviate_service, WeaviateService
from app.services.inventory_service import InventoryService

logger = logging.getLogger(__name__)


class ItemService:
    """Service for comprehensive item management with semantic search integration."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.inventory_service = InventoryService(db)
    
    async def create_item(
        self, 
        item_data: ItemCreate,
        location_id: Optional[int] = None,
        quantity: int = 1
    ) -> Item:
        """
        Create a new item with dual-write to PostgreSQL and Weaviate.
        
        Args:
            item_data: Item creation data
            location_id: Optional location to assign item to
            quantity: Quantity at location (if location specified)
            
        Returns:
            Created item
        """
        try:
            # 1. Create item in PostgreSQL (source of truth)
            item = Item(
                name=item_data.name,
                description=item_data.description,
                item_type=item_data.item_type,
                condition=item_data.condition,
                status=item_data.status,
                brand=item_data.brand,
                model=item_data.model,
                serial_number=item_data.serial_number,
                barcode=item_data.barcode,
                purchase_price=item_data.purchase_price,
                current_value=item_data.current_value,
                purchase_date=item_data.purchase_date,
                warranty_expiry=item_data.warranty_expiry,
                weight=item_data.weight,
                dimensions=item_data.dimensions,
                color=item_data.color,
                category_id=item_data.category_id,
                notes=item_data.notes,
                tags=item_data.tags
            )
            
            self.db.add(item)
            await self.db.commit()
            await self.db.refresh(item, ["category"])
            
            # 2. Create inventory entry if location specified
            if location_id:
                from app.schemas.inventory import InventoryCreate
                inventory_data = InventoryCreate(
                    item_id=item.id,
                    location_id=location_id,
                    quantity=quantity
                )
                await self.inventory_service.create_inventory_entry(inventory_data)
            
            # 3. Reload item with proper eager loading for relationships
            item_query = select(Item).options(
                selectinload(Item.category),
                selectinload(Item.inventory_entries).selectinload(Inventory.location)
            ).where(Item.id == item.id)
            result = await self.db.execute(item_query)
            item = result.scalar_one()
            
            # 4. Create Weaviate embedding (best effort)
            await self._sync_to_weaviate(item)
            
            logger.info(f"Created item {item.id}: {item.name}")
            return item
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create item: {e}")
            raise
    
    async def update_item(self, item_id: int, item_data: ItemUpdate) -> Item:
        """
        Update an item with dual-write to PostgreSQL and Weaviate.
        
        Args:
            item_id: ID of item to update
            item_data: Item update data
            
        Returns:
            Updated item
        """
        try:
            # Get existing item
            result = await self.db.execute(
                select(Item).options(
                    selectinload(Item.category),
                    selectinload(Item.inventory_entries).selectinload(Inventory.location)
                ).where(Item.id == item_id)
            )
            item = result.scalar_one_or_none()
            if not item:
                raise ValueError(f"Item {item_id} not found")
            
            # Update fields that are provided
            update_data = item_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(item, field):
                    setattr(item, field, value)
            
            # Update metadata
            item.updated_at = datetime.now()
            item.version = (item.version or 0) + 1
            
            await self.db.commit()
            await self.db.refresh(item, ["category", "inventory_entries"])
            
            # Sync to Weaviate
            await self._sync_to_weaviate(item)
            
            logger.info(f"Updated item {item.id}: {item.name}")
            return item
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update item {item_id}: {e}")
            raise
    
    async def delete_item(self, item_id: int, soft_delete: bool = True) -> bool:
        """
        Delete an item from PostgreSQL and Weaviate.
        
        Args:
            item_id: ID of item to delete
            soft_delete: Whether to soft delete (default) or hard delete
            
        Returns:
            True if successful
        """
        try:
            # Get existing item
            result = await self.db.execute(select(Item).where(Item.id == item_id))
            item = result.scalar_one_or_none()
            if not item:
                raise ValueError(f"Item {item_id} not found")
            
            if soft_delete:
                # Soft delete - mark as inactive
                item.is_active = False
                item.status = ItemStatus.DISPOSED
                item.updated_at = datetime.now()
                item.version = (item.version or 0) + 1
                await self.db.commit()
                
                # Remove from Weaviate
                weaviate_service = await get_weaviate_service()
                await weaviate_service.delete_item_embedding(item_id)
                
                logger.info(f"Soft deleted item {item_id}")
            else:
                # Hard delete
                await self.db.delete(item)
                await self.db.commit()
                
                # Remove from Weaviate
                weaviate_service = await get_weaviate_service()
                await weaviate_service.delete_item_embedding(item_id)
                
                logger.info(f"Hard deleted item {item_id}")
            
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete item {item_id}: {e}")
            raise
    
    async def get_item_by_id(
        self, 
        item_id: int, 
        include_inactive: bool = False
    ) -> Optional[Item]:
        """
        Get an item by ID with full relationships loaded.
        
        Args:
            item_id: ID of item to retrieve
            include_inactive: Whether to include soft-deleted items
            
        Returns:
            Item if found, None otherwise
        """
        query = select(Item).options(
            selectinload(Item.category),
            selectinload(Item.inventory_entries).selectinload(Inventory.location)
        ).where(Item.id == item_id)
        
        if not include_inactive:
            query = query.where(Item.is_active == True)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def search_items(self, search_params: ItemSearch) -> List[Item]:
        """
        Search items using traditional PostgreSQL search.
        
        Args:
            search_params: Search parameters
            
        Returns:
            List of matching items
        """
        query = select(Item).options(
            selectinload(Item.category),
            selectinload(Item.inventory_entries).selectinload(Inventory.location)
        )
        
        # Base filter for active items
        if not getattr(search_params, 'include_inactive', False):
            query = query.where(Item.is_active == True)
        
        # Text search
        if search_params.search_text:
            search_term = f"%{search_params.search_text}%"
            query = query.where(
                or_(
                    Item.name.ilike(search_term),
                    Item.description.ilike(search_term),
                    Item.notes.ilike(search_term),
                    Item.brand.ilike(search_term),
                    Item.model.ilike(search_term),
                    Item.tags.ilike(search_term)
                )
            )
        
        # Enum filters
        if search_params.item_type:
            query = query.where(Item.item_type == search_params.item_type)
        if search_params.condition:
            query = query.where(Item.condition == search_params.condition)
        if search_params.status:
            query = query.where(Item.status == search_params.status)
        if search_params.category_id:
            query = query.where(Item.category_id == search_params.category_id)
        
        # Value filters
        if search_params.min_value is not None:
            query = query.where(Item.current_value >= search_params.min_value)
        if search_params.max_value is not None:
            query = query.where(Item.current_value <= search_params.max_value)
        
        # Date filters
        if getattr(search_params, 'purchased_after', None):
            query = query.where(Item.purchase_date >= search_params.purchased_after)
        if getattr(search_params, 'purchased_before', None):
            query = query.where(Item.purchase_date <= search_params.purchased_before)
        
        # Apply limit
        limit = getattr(search_params, 'limit', 50)
        query = query.limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def bulk_sync_to_weaviate(
        self, 
        item_ids: Optional[List[int]] = None,
        force_update: bool = False
    ) -> Dict[str, int]:
        """
        Bulk sync items to Weaviate for semantic search.
        
        Args:
            item_ids: Specific item IDs to sync (None for all active items)
            force_update: Whether to force update existing embeddings
            
        Returns:
            Statistics about the sync operation
        """
        try:
            # Build query for items to sync
            query = select(Item).options(
                selectinload(Item.category),
                selectinload(Item.inventory_entries).selectinload(Inventory.location)
            ).where(Item.is_active == True)
            
            if item_ids:
                query = query.where(Item.id.in_(item_ids))
            
            result = await self.db.execute(query)
            items = result.scalars().all()
            
            if not items:
                return {"success": 0, "failed": 0, "skipped": 0}
            
            # Prepare items data for Weaviate
            items_data = []
            for item in items:
                category_name = item.category.name if item.category else ""
                location_names = [
                    entry.location.name for entry in (item.inventory_entries or [])
                    if entry.location
                ]
                items_data.append((item, category_name, location_names))
            
            # Sync to Weaviate
            weaviate_service = await get_weaviate_service()
            stats = await weaviate_service.batch_create_embeddings(items_data)
            
            logger.info(f"Bulk sync completed for {len(items)} items: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Bulk sync to Weaviate failed: {e}")
            return {"success": 0, "failed": len(items_data) if 'items_data' in locals() else 0, "skipped": 0}
    
    async def _sync_to_weaviate(self, item: Item) -> None:
        """
        Sync a single item to Weaviate (best effort).
        
        Args:
            item: Item to sync
        """
        try:
            weaviate_service = await get_weaviate_service()
            
            # Get category name
            category_name = ""
            if item.category:
                category_name = item.category.name
            elif item.category_id:
                # Load category if not already loaded
                result = await self.db.execute(
                    select(Category).where(Category.id == item.category_id)
                )
                category = result.scalar_one_or_none()
                if category:
                    category_name = category.name
            
            # Get location names
            location_names = []
            if hasattr(item, 'inventory_entries') and item.inventory_entries:
                location_names = [
                    entry.location.name for entry in item.inventory_entries
                    if entry.location
                ]
            
            # Create embedding
            success = await weaviate_service.create_item_embedding(
                item, category_name, location_names
            )
            
            if success:
                logger.debug(f"Synced item {item.id} to Weaviate")
            else:
                logger.warning(f"Failed to sync item {item.id} to Weaviate")
                
        except Exception as e:
            logger.warning(f"Weaviate sync failed for item {item.id}: {e}")
            # Don't raise - this is best effort