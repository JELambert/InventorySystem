"""
Movement Service for managing item movement history and audit trails.

Handles business logic for tracking item movements including location changes,
quantity adjustments, and comprehensive audit trail management.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, and_, or_, desc, asc
from decimal import Decimal

from app.models.item_movement_history import ItemMovementHistory
from app.models.item import Item
from app.models.location import Location
from app.models.inventory import Inventory
from app.schemas.movement_history import (
    MovementHistoryCreate, MovementHistoryResponse, MovementHistoryWithDetails,
    MovementHistorySearch, MovementHistorySummary, BulkMovementCreate,
    MovementTypeStats, ItemMovementTimeline
)
from app.schemas.item import ItemSummary
from app.schemas.location import LocationSummary


class MovementService:
    """Service for movement history management operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _convert_movement_to_details(self, movement: ItemMovementHistory) -> MovementHistoryWithDetails:
        """
        Convert a raw ItemMovementHistory object to MovementHistoryWithDetails schema.
        
        Args:
            movement: Raw database movement object
            
        Returns:
            MovementHistoryWithDetails: Properly serialized movement object
            
        Raises:
            ValueError: If conversion fails due to missing required data
        """
        try:
            # Convert Item to ItemSummary
            item_summary = None
            if movement.item:
                item_summary = ItemSummary(
                    id=movement.item.id,
                    name=movement.item.name,
                    item_type=movement.item.item_type,
                    condition=movement.item.condition,
                    status=movement.item.status,
                    brand=movement.item.brand,
                    model=movement.item.model,
                    current_value=movement.item.current_value,
                    category_id=movement.item.category_id,
                    created_at=movement.item.created_at
                )
            
            # Convert from_location to LocationSummary
            from_location_summary = None
            if movement.from_location:
                from_location_summary = LocationSummary(
                    id=movement.from_location.id,
                    name=movement.from_location.name,
                    location_type=movement.from_location.location_type,
                    child_count=0,  # Default for movement history context
                    item_count=0   # Default for movement history context
                )
            
            # Convert to_location to LocationSummary
            to_location_summary = None
            if movement.to_location:
                to_location_summary = LocationSummary(
                    id=movement.to_location.id,
                    name=movement.to_location.name,
                    location_type=movement.to_location.location_type,
                    child_count=0,  # Default for movement history context
                    item_count=0   # Default for movement history context
                )
            
            return MovementHistoryWithDetails(
                id=movement.id,
                item_id=movement.item_id,
                from_location_id=movement.from_location_id,
                to_location_id=movement.to_location_id,
                quantity_moved=movement.quantity_moved,
                quantity_before=movement.quantity_before,
                quantity_after=movement.quantity_after,
                movement_type=movement.movement_type,
                reason=movement.reason,
                notes=movement.notes,
                estimated_value=movement.estimated_value,
                user_id=movement.user_id,
                system_notes=movement.system_notes,
                created_at=movement.created_at,
                movement_description=movement.movement_description,
                item=item_summary,
                from_location=from_location_summary,
                to_location=to_location_summary
            )
        except Exception as e:
            # Log the error with context for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to convert movement {movement.id} to schema: {e}")
            logger.error(f"Movement data: item_id={movement.item_id}, from_location_id={movement.from_location_id}, to_location_id={movement.to_location_id}")
            
            # Re-raise with more context
            raise ValueError(f"Failed to convert movement history to schema: {e}") from e

    async def record_movement(
        self, 
        movement_data: MovementHistoryCreate,
        auto_commit: bool = True
    ) -> ItemMovementHistory:
        """
        Record a new movement in the history.
        
        Args:
            movement_data: Movement data to record
            auto_commit: Whether to commit the transaction automatically
            
        Returns:
            Created movement history entry
            
        Raises:
            ValueError: If referenced item or locations don't exist
        """
        # Verify item exists
        result = await self.db.execute(select(Item).where(Item.id == movement_data.item_id))
        item = result.scalar_one_or_none()
        if not item:
            raise ValueError(f"Item with ID {movement_data.item_id} not found")
        
        # Verify locations exist if specified
        if movement_data.from_location_id:
            result = await self.db.execute(select(Location).where(Location.id == movement_data.from_location_id))
            from_location = result.scalar_one_or_none()
            if not from_location:
                raise ValueError(f"From location with ID {movement_data.from_location_id} not found")
        
        if movement_data.to_location_id:
            result = await self.db.execute(select(Location).where(Location.id == movement_data.to_location_id))
            to_location = result.scalar_one_or_none()
            if not to_location:
                raise ValueError(f"To location with ID {movement_data.to_location_id} not found")
        
        # Create movement history entry
        movement_entry = ItemMovementHistory(
            item_id=movement_data.item_id,
            from_location_id=movement_data.from_location_id,
            to_location_id=movement_data.to_location_id,
            quantity_moved=movement_data.quantity_moved,
            quantity_before=movement_data.quantity_before,
            quantity_after=movement_data.quantity_after,
            movement_type=movement_data.movement_type,
            reason=movement_data.reason,
            notes=movement_data.notes,
            estimated_value=movement_data.estimated_value,
            user_id=movement_data.user_id,
            system_notes=movement_data.system_notes
        )
        
        self.db.add(movement_entry)
        
        if auto_commit:
            await self.db.commit()
            await self.db.refresh(movement_entry)
        
        return movement_entry

    async def record_item_creation(
        self, 
        item_id: int, 
        location_id: int, 
        quantity: int,
        reason: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> ItemMovementHistory:
        """Record movement for new item creation."""
        movement_data = MovementHistoryCreate(
            item_id=item_id,
            from_location_id=None,
            to_location_id=location_id,
            quantity_moved=quantity,
            quantity_before=0,
            quantity_after=quantity,
            movement_type="create",
            reason=reason or "Initial item creation",
            user_id=user_id,
            system_notes="Automatically recorded during item creation"
        )
        
        return await self.record_movement(movement_data)

    async def record_item_move(
        self,
        item_id: int,
        from_location_id: int,
        to_location_id: int,
        quantity: int,
        quantity_before_from: int,
        quantity_after_from: int,
        quantity_before_to: int,
        quantity_after_to: int,
        reason: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[ItemMovementHistory]:
        """Record movement for item relocation."""
        movements = []
        
        # Record removal from source location
        removal_data = MovementHistoryCreate(
            item_id=item_id,
            from_location_id=from_location_id,
            to_location_id=None,
            quantity_moved=quantity,
            quantity_before=quantity_before_from,
            quantity_after=quantity_after_from,
            movement_type="move",
            reason=reason or "Item relocation",
            user_id=user_id,
            system_notes=f"Moved {quantity} items to location {to_location_id}"
        )
        
        removal = await self.record_movement(removal_data, auto_commit=False)
        movements.append(removal)
        
        # Record addition to destination location
        addition_data = MovementHistoryCreate(
            item_id=item_id,
            from_location_id=None,
            to_location_id=to_location_id,
            quantity_moved=quantity,
            quantity_before=quantity_before_to,
            quantity_after=quantity_after_to,
            movement_type="move",
            reason=reason or "Item relocation",
            user_id=user_id,
            system_notes=f"Received {quantity} items from location {from_location_id}"
        )
        
        addition = await self.record_movement(addition_data, auto_commit=False)
        movements.append(addition)
        
        await self.db.commit()
        for movement in movements:
            await self.db.refresh(movement)
        
        return movements

    async def record_quantity_adjustment(
        self,
        item_id: int,
        location_id: int,
        quantity_before: int,
        quantity_after: int,
        reason: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> ItemMovementHistory:
        """Record movement for quantity adjustment."""
        quantity_change = quantity_after - quantity_before
        
        movement_data = MovementHistoryCreate(
            item_id=item_id,
            from_location_id=location_id if quantity_change < 0 else None,
            to_location_id=location_id if quantity_change > 0 else None,
            quantity_moved=abs(quantity_change),
            quantity_before=quantity_before,
            quantity_after=quantity_after,
            movement_type="adjust",
            reason=reason or "Quantity adjustment",
            user_id=user_id,
            system_notes=f"Quantity adjusted from {quantity_before} to {quantity_after}"
        )
        
        return await self.record_movement(movement_data)

    async def get_movement_history(
        self, 
        search_params: MovementHistorySearch,
        skip: int = 0,
        limit: int = 100
    ) -> List[ItemMovementHistory]:
        """
        Get movement history entries with filtering and pagination.
        
        Args:
            search_params: Search and filter parameters
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of movement history entries with related data
        """
        query = select(ItemMovementHistory).options(
            selectinload(ItemMovementHistory.item),
            selectinload(ItemMovementHistory.from_location),
            selectinload(ItemMovementHistory.to_location)
        )
        
        # Apply filters
        if search_params.item_id:
            query = query.where(ItemMovementHistory.item_id == search_params.item_id)
        
        if search_params.location_id:
            query = query.where(
                or_(
                    ItemMovementHistory.from_location_id == search_params.location_id,
                    ItemMovementHistory.to_location_id == search_params.location_id
                )
            )
        
        if search_params.from_location_id:
            query = query.where(ItemMovementHistory.from_location_id == search_params.from_location_id)
        
        if search_params.to_location_id:
            query = query.where(ItemMovementHistory.to_location_id == search_params.to_location_id)
        
        if search_params.movement_type:
            query = query.where(ItemMovementHistory.movement_type == search_params.movement_type)
        
        if search_params.user_id:
            query = query.where(ItemMovementHistory.user_id == search_params.user_id)
        
        if search_params.start_date:
            query = query.where(ItemMovementHistory.created_at >= search_params.start_date)
        
        if search_params.end_date:
            query = query.where(ItemMovementHistory.created_at <= search_params.end_date)
        
        if search_params.min_quantity:
            query = query.where(ItemMovementHistory.quantity_moved >= search_params.min_quantity)
        
        if search_params.max_quantity:
            query = query.where(ItemMovementHistory.quantity_moved <= search_params.max_quantity)
        
        # Order by most recent first
        query = query.order_by(desc(ItemMovementHistory.created_at))
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_item_movement_timeline(self, item_id: int) -> ItemMovementTimeline:
        """
        Get complete movement timeline for a specific item.
        
        Args:
            item_id: ID of the item
            
        Returns:
            Complete movement timeline with current status
        """
        # Get item details
        result = await self.db.execute(select(Item).where(Item.id == item_id))
        item = result.scalar_one_or_none()
        if not item:
            raise ValueError(f"Item with ID {item_id} not found")
        
        # Get all movements for this item
        search_params = MovementHistorySearch(item_id=item_id)
        movements = await self.get_movement_history(search_params, limit=1000)
        
        # Get current locations
        current_locations_query = select(Inventory).options(
            selectinload(Inventory.location)
        ).where(Inventory.item_id == item_id)
        
        result = await self.db.execute(current_locations_query)
        current_inventory = result.scalars().all()
        
        current_locations = [
            {
                "location_id": inv.location_id,
                "location_name": inv.location.name if inv.location else "Unknown",
                "quantity": inv.quantity,
                "updated_at": inv.updated_at.isoformat() if inv.updated_at else None
            }
            for inv in current_inventory
        ]
        
        # Convert to response format using our conversion helper
        movement_details = [
            self._convert_movement_to_details(movement)
            for movement in movements
        ]
        
        return ItemMovementTimeline(
            item_id=item_id,
            item_name=item.name,
            movements=movement_details,
            current_locations=current_locations,
            total_movements=len(movements)
        )

    async def get_movement_summary(
        self, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> MovementHistorySummary:
        """
        Get summary statistics for movement history.
        
        Args:
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            
        Returns:
            Summary statistics and recent movements
        """
        # Base query for filtered movements
        base_query = select(ItemMovementHistory)
        
        if start_date:
            base_query = base_query.where(ItemMovementHistory.created_at >= start_date)
        if end_date:
            base_query = base_query.where(ItemMovementHistory.created_at <= end_date)
        
        # Get total movements
        total_movements_result = await self.db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total_movements = total_movements_result.scalar()
        
        # Get total items moved
        total_items_result = await self.db.execute(
            select(func.sum(ItemMovementHistory.quantity_moved)).select_from(base_query.subquery())
        )
        total_items_moved = total_items_result.scalar() or 0
        
        # Get unique items
        unique_items_result = await self.db.execute(
            select(func.count(func.distinct(ItemMovementHistory.item_id))).select_from(base_query.subquery())
        )
        unique_items = unique_items_result.scalar()
        
        # Get unique locations
        unique_locations_result = await self.db.execute(
            select(func.count(func.distinct(
                func.coalesce(ItemMovementHistory.from_location_id, ItemMovementHistory.to_location_id)
            ))).select_from(base_query.subquery())
        )
        unique_locations = unique_locations_result.scalar()
        
        # Get movement types summary
        movement_types_result = await self.db.execute(
            select(
                ItemMovementHistory.movement_type,
                func.count().label('count'),
                func.sum(ItemMovementHistory.quantity_moved).label('total_quantity')
            ).select_from(base_query.subquery())
            .group_by(ItemMovementHistory.movement_type)
        )
        
        movement_types = []
        for row in movement_types_result:
            percentage = (row.count / total_movements * 100) if total_movements > 0 else 0
            movement_types.append({
                "movement_type": row.movement_type,
                "count": row.count,
                "total_quantity": row.total_quantity,
                "percentage": round(percentage, 2)
            })
        
        # Get recent movements
        recent_movements = await self.get_movement_history(
            MovementHistorySearch(), skip=0, limit=10
        )
        
        # Get date range
        date_range_result = await self.db.execute(
            select(
                func.min(ItemMovementHistory.created_at).label('earliest'),
                func.max(ItemMovementHistory.created_at).label('latest')
            ).select_from(base_query.subquery())
        )
        date_range_row = date_range_result.first()
        
        date_range = {}
        if date_range_row and date_range_row.earliest:
            date_range = {
                "earliest": date_range_row.earliest.isoformat(),
                "latest": date_range_row.latest.isoformat() if date_range_row.latest else None
            }
        
        # Convert recent movements to proper schema objects
        converted_recent_movements = [
            self._convert_movement_to_details(movement)
            for movement in recent_movements
        ]
        
        return MovementHistorySummary(
            total_movements=total_movements,
            total_items_moved=int(total_items_moved),
            unique_items=unique_items,
            unique_locations=unique_locations,
            movement_types=movement_types,
            recent_movements=converted_recent_movements,
            date_range=date_range
        )