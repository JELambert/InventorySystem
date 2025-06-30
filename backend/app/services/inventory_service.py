"""
Inventory Service for managing item-location-quantity relationships.

Handles business logic for inventory operations including adding items to locations,
moving items between locations, and tracking quantities.
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, and_, or_, desc, asc
from decimal import Decimal

from app.models.inventory import Inventory
from app.models.item import Item, ItemType, ItemCondition, ItemStatus
from app.models.location import Location
from app.schemas.inventory import (
    InventoryCreate, InventoryUpdate, InventoryResponse, InventoryWithDetails,
    InventorySearch, InventoryMove, InventorySummary, InventoryBulkOperation,
    ItemLocationHistory, LocationInventoryReport
)


class InventoryService:
    """Service for inventory management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_inventory_entry(self, inventory_data: InventoryCreate) -> Inventory:
        """
        Create a new inventory entry for an item at a location.
        
        Args:
            inventory_data: Inventory creation data
            
        Returns:
            Created inventory entry
            
        Raises:
            ValueError: If item or location doesn't exist, or entry already exists
        """
        # Check if item exists
        result = await self.db.execute(select(Item).where(Item.id == inventory_data.item_id))
        item = result.scalar_one_or_none()
        if not item:
            raise ValueError(f"Item with ID {inventory_data.item_id} not found")
        
        # Check if location exists
        result = await self.db.execute(select(Location).where(Location.id == inventory_data.location_id))
        location = result.scalar_one_or_none()
        if not location:
            raise ValueError(f"Location with ID {inventory_data.location_id} not found")
        
        # Check if entry already exists
        result = await self.db.execute(
            select(Inventory).where(
                and_(
                    Inventory.item_id == inventory_data.item_id,
                    Inventory.location_id == inventory_data.location_id
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError(f"Inventory entry already exists for item {inventory_data.item_id} at location {inventory_data.location_id}")
        
        # Create new inventory entry
        inventory_entry = Inventory(
            item_id=inventory_data.item_id,
            location_id=inventory_data.location_id,
            quantity=inventory_data.quantity
        )
        
        self.db.add(inventory_entry)
        await self.db.commit()
        await self.db.refresh(inventory_entry)
        
        return inventory_entry

    async def get_inventory_entry(self, inventory_id: int) -> Optional[Inventory]:
        """Get an inventory entry by ID with related data."""
        result = await self.db.execute(
            select(Inventory)
            .options(selectinload(Inventory.item), selectinload(Inventory.location))
            .where(Inventory.id == inventory_id)
        )
        return result.scalar_one_or_none()

    async def update_inventory_entry(self, inventory_id: int, update_data: InventoryUpdate) -> Optional[Inventory]:
        """
        Update an inventory entry.
        
        Args:
            inventory_id: ID of inventory entry to update
            update_data: Update data
            
        Returns:
            Updated inventory entry or None if not found
        """
        inventory_entry = await self.get_inventory_entry(inventory_id)
        if not inventory_entry:
            return None
        
        # Update quantity if provided
        if update_data.quantity is not None:
            inventory_entry.quantity = update_data.quantity
        
        # Move to new location if provided
        if update_data.location_id is not None:
            # Check if new location exists
            result = await self.db.execute(select(Location).where(Location.id == update_data.location_id))
            location = result.scalar_one_or_none()
            if not location:
                raise ValueError(f"Location with ID {update_data.location_id} not found")
            
            # Check if entry already exists at new location
            result = await self.db.execute(
                select(Inventory).where(
                    and_(
                        Inventory.item_id == inventory_entry.item_id,
                        Inventory.location_id == update_data.location_id,
                        Inventory.id != inventory_id
                    )
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                raise ValueError(f"Item already exists at location {update_data.location_id}")
            
            inventory_entry.location_id = update_data.location_id
        
        inventory_entry.updated_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(inventory_entry)
        
        return inventory_entry

    async def delete_inventory_entry(self, inventory_id: int) -> bool:
        """Delete an inventory entry."""
        inventory_entry = await self.get_inventory_entry(inventory_id)
        if not inventory_entry:
            return False
        
        await self.db.delete(inventory_entry)
        await self.db.commit()
        return True

    async def search_inventory(self, search_params: InventorySearch) -> List[Inventory]:
        """
        Search inventory entries based on criteria.
        
        Args:
            search_params: Search parameters
            
        Returns:
            List of matching inventory entries
        """
        query = select(Inventory).options(
            selectinload(Inventory.item),
            selectinload(Inventory.location)
        )
        
        # Apply filters
        conditions = []
        
        if search_params.item_id:
            conditions.append(Inventory.item_id == search_params.item_id)
        
        if search_params.location_id:
            conditions.append(Inventory.location_id == search_params.location_id)
        
        if search_params.min_quantity:
            conditions.append(Inventory.quantity >= search_params.min_quantity)
        
        if search_params.max_quantity:
            conditions.append(Inventory.quantity <= search_params.max_quantity)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Apply value filters (requires join with items)
        if search_params.min_value or search_params.max_value:
            query = query.join(Item, Inventory.item_id == Item.id)
            
            if search_params.min_value:
                # Calculate total value (item.current_value * quantity >= min_value)
                conditions.append(
                    func.coalesce(Item.current_value, 0) * Inventory.quantity >= search_params.min_value
                )
            
            if search_params.max_value:
                conditions.append(
                    func.coalesce(Item.current_value, 0) * Inventory.quantity <= search_params.max_value
                )
        
        query = query.order_by(Inventory.updated_at.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def move_item(self, item_id: int, move_data: InventoryMove) -> Inventory:
        """
        Move items between locations.
        
        Args:
            item_id: ID of item to move
            move_data: Move operation data
            
        Returns:
            Updated or created inventory entry at destination
            
        Raises:
            ValueError: If validation fails
        """
        if not move_data.validate_different_locations():
            raise ValueError("Source and destination locations must be different")
        
        # Get source inventory entry
        result = await self.db.execute(
            select(Inventory).where(
                and_(
                    Inventory.item_id == item_id,
                    Inventory.location_id == move_data.from_location_id
                )
            )
        )
        source_entry = result.scalar_one_or_none()
        if not source_entry:
            raise ValueError(f"Item {item_id} not found at location {move_data.from_location_id}")
        
        if source_entry.quantity < move_data.quantity:
            raise ValueError(f"Insufficient quantity. Available: {source_entry.quantity}, Requested: {move_data.quantity}")
        
        # Check if destination location exists
        result = await self.db.execute(select(Location).where(Location.id == move_data.to_location_id))
        if not result.scalar_one_or_none():
            raise ValueError(f"Destination location {move_data.to_location_id} not found")
        
        # Get or create destination entry
        result = await self.db.execute(
            select(Inventory).where(
                and_(
                    Inventory.item_id == item_id,
                    Inventory.location_id == move_data.to_location_id
                )
            )
        )
        dest_entry = result.scalar_one_or_none()
        
        if dest_entry:
            # Add to existing entry
            dest_entry.quantity += move_data.quantity
            dest_entry.updated_at = datetime.now()
        else:
            # Create new entry
            dest_entry = Inventory(
                item_id=item_id,
                location_id=move_data.to_location_id,
                quantity=move_data.quantity
            )
            self.db.add(dest_entry)
        
        # Update source entry
        if source_entry.quantity == move_data.quantity:
            # Remove source entry if moving all items
            await self.db.delete(source_entry)
        else:
            # Reduce quantity at source
            source_entry.quantity -= move_data.quantity
            source_entry.updated_at = datetime.now()
        
        await self.db.commit()
        await self.db.refresh(dest_entry)
        
        return dest_entry

    async def get_item_locations(self, item_id: int) -> List[Inventory]:
        """Get all locations where an item is stored."""
        result = await self.db.execute(
            select(Inventory)
            .options(selectinload(Inventory.location))
            .where(Inventory.item_id == item_id)
            .order_by(Inventory.quantity.desc())
        )
        return result.scalars().all()

    async def get_location_items(self, location_id: int) -> List[Inventory]:
        """Get all items stored in a location."""
        result = await self.db.execute(
            select(Inventory)
            .options(selectinload(Inventory.item))
            .where(Inventory.location_id == location_id)
            .order_by(Inventory.updated_at.desc())
        )
        return result.scalars().all()

    async def get_inventory_summary(self) -> InventorySummary:
        """Get overall inventory summary statistics."""
        # Total unique items
        result = await self.db.execute(
            select(func.count(func.distinct(Inventory.item_id)))
        )
        total_items = result.scalar() or 0
        
        # Total quantity across all items
        result = await self.db.execute(
            select(func.sum(Inventory.quantity))
        )
        total_quantity = result.scalar() or 0
        
        # Total locations with items
        result = await self.db.execute(
            select(func.count(func.distinct(Inventory.location_id)))
        )
        total_locations = result.scalar() or 0
        
        # Total value (sum of item.current_value * quantity)
        result = await self.db.execute(
            select(func.sum(func.coalesce(Item.current_value, 0) * Inventory.quantity))
            .select_from(Inventory)
            .join(Item, Inventory.item_id == Item.id)
        )
        total_value = result.scalar()
        if total_value:
            total_value = float(total_value)
        
        # Summary by location
        result = await self.db.execute(
            select(
                Location.id,
                Location.name,
                func.count(Inventory.item_id).label('item_count'),
                func.sum(Inventory.quantity).label('total_quantity')
            )
            .select_from(Inventory)
            .join(Location, Inventory.location_id == Location.id)
            .group_by(Location.id, Location.name)
            .order_by(func.sum(Inventory.quantity).desc())
        )
        by_location = [
            {
                "location_id": row.id,
                "location_name": row.name,
                "item_count": row.item_count,
                "total_quantity": row.total_quantity
            }
            for row in result.fetchall()
        ]
        
        # Summary by item type
        result = await self.db.execute(
            select(
                Item.item_type,
                func.count(func.distinct(Inventory.item_id)).label('item_count'),
                func.sum(Inventory.quantity).label('total_quantity')
            )
            .select_from(Inventory)
            .join(Item, Inventory.item_id == Item.id)
            .group_by(Item.item_type)
            .order_by(func.sum(Inventory.quantity).desc())
        )
        by_item_type = [
            {
                "item_type": row.item_type.value,
                "item_count": row.item_count,
                "total_quantity": row.total_quantity
            }
            for row in result.fetchall()
        ]
        
        return InventorySummary(
            total_items=total_items,
            total_quantity=total_quantity,
            total_locations=total_locations,
            total_value=total_value,
            by_location=by_location,
            by_item_type=by_item_type
        )

    async def bulk_create_inventory(self, bulk_data: InventoryBulkOperation) -> List[Inventory]:
        """
        Create multiple inventory entries in a single transaction.
        
        Args:
            bulk_data: Bulk operation data
            
        Returns:
            List of created inventory entries
            
        Raises:
            ValueError: If validation fails
        """
        errors = bulk_data.validate_operations()
        if errors:
            raise ValueError(f"Validation failed: {'; '.join(errors)}")
        
        created_entries = []
        
        for operation in bulk_data.operations:
            try:
                entry = await self.create_inventory_entry(operation)
                created_entries.append(entry)
            except ValueError as e:
                # Rollback on any error
                await self.db.rollback()
                raise ValueError(f"Bulk operation failed: {str(e)}")
        
        return created_entries

    async def get_location_inventory_report(self, location_id: int) -> Optional[LocationInventoryReport]:
        """Generate comprehensive inventory report for a location."""
        # Get location details
        result = await self.db.execute(select(Location).where(Location.id == location_id))
        location = result.scalar_one_or_none()
        if not location:
            return None
        
        # Get all inventory entries for this location
        inventory_entries = await self.get_location_items(location_id)
        
        # Calculate summary stats
        total_items = len(inventory_entries)
        total_quantity = sum(entry.quantity for entry in inventory_entries)
        
        # Calculate total value
        total_value = 0.0
        for entry in inventory_entries:
            if entry.item and entry.item.current_value:
                total_value += float(entry.item.current_value) * entry.quantity
        
        return LocationInventoryReport(
            location_id=location_id,
            location_name=location.name,
            location_path=location.full_path,
            total_items=total_items,
            total_quantity=total_quantity,
            total_value=total_value if total_value > 0 else None,
            items=[
                InventoryWithDetails(
                    id=entry.id,
                    item_id=entry.item_id,
                    location_id=entry.location_id,
                    quantity=entry.quantity,
                    updated_at=entry.updated_at,
                    total_value=entry.total_value,
                    item=entry.item,
                    location=entry.location
                )
                for entry in inventory_entries
            ],
            utilization=None  # Could be calculated based on location capacity if implemented
        )