"""
Inventory API endpoints for the Home Inventory System.

Handles inventory management operations including item-location relationships,
quantity tracking, and movement between locations.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import get_session
from app.services.inventory_service import InventoryService
from app.services.movement_validator import MovementValidator, ValidationError
from app.performance import cache, invalidate_cache_on_changes, OptimizedInventoryService
from app.schemas.inventory import (
    InventoryCreate, InventoryUpdate, InventoryResponse, InventoryWithDetails,
    InventorySearch, InventoryMove, InventorySummary, InventoryBulkOperation,
    ItemLocationHistory, LocationInventoryReport
)
from app.schemas.item import ItemSummary
from app.schemas.location import LocationSummary
from app.schemas.movement_history import (
    MovementHistorySearch, MovementHistoryWithDetails, MovementHistorySummary,
    ItemMovementTimeline, MovementHistoryCreate
)
from app.services.movement_service import MovementService

router = APIRouter()


def get_inventory_service(db: AsyncSession = Depends(get_session)) -> InventoryService:
    """Dependency to get inventory service."""
    return InventoryService(db)


def get_movement_service(db: AsyncSession = Depends(get_session)) -> MovementService:
    """Dependency to get movement service."""
    return MovementService(db)


def get_movement_validator(db: AsyncSession = Depends(get_session)) -> MovementValidator:
    """Dependency to get movement validator."""
    return MovementValidator(db)


def get_optimized_service(db: AsyncSession = Depends(get_session)) -> OptimizedInventoryService:
    """Dependency to get optimized inventory service."""
    return OptimizedInventoryService(db)


# Specific paths first, then parameterized paths

@router.get("/summary", response_model=InventorySummary)
async def get_inventory_summary(
    service: InventoryService = Depends(get_inventory_service)
):
    """Get overall inventory summary statistics."""
    return await service.get_inventory_summary()


@router.post("/bulk", response_model=List[InventoryResponse], status_code=status.HTTP_201_CREATED)
async def bulk_create_inventory(
    bulk_data: InventoryBulkOperation,
    service: InventoryService = Depends(get_inventory_service)
):
    """
    Create multiple inventory entries in a single transaction.
    
    Maximum 100 operations per request.
    All operations must succeed or none will be applied.
    """
    try:
        inventory_entries = await service.bulk_create_inventory(bulk_data)
        return [InventoryResponse.model_validate(entry) for entry in inventory_entries]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=List[InventoryWithDetails])
async def search_inventory(
    item_id: Optional[int] = Query(None, description="Filter by item ID"),
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    min_quantity: Optional[int] = Query(None, description="Minimum quantity filter"),
    max_quantity: Optional[int] = Query(None, description="Maximum quantity filter"),
    min_value: Optional[float] = Query(None, description="Minimum total value filter"),
    max_value: Optional[float] = Query(None, description="Maximum total value filter"),
    service: InventoryService = Depends(get_inventory_service)
):
    """
    Search inventory entries based on various criteria.
    
    All parameters are optional - omit to get all inventory entries.
    """
    search_params = InventorySearch(
        item_id=item_id,
        location_id=location_id,
        min_quantity=min_quantity,
        max_quantity=max_quantity,
        min_value=min_value,
        max_value=max_value
    )
    
    inventory_entries = await service.search_inventory(search_params)
    
    return [
        InventoryWithDetails(
            id=entry.id,
            item_id=entry.item_id,
            location_id=entry.location_id,
            quantity=entry.quantity,
            updated_at=entry.updated_at,
            total_value=entry.total_value,
            item=ItemSummary.model_validate(entry.item) if entry.item else None,
            location=LocationSummary(
                id=entry.location.id,
                name=entry.location.name,
                location_type=entry.location.location_type,
                child_count=0,  # We can set this to 0 for now
                item_count=0   # We can set this to 0 for now
            ) if entry.location else None
        )
        for entry in inventory_entries
    ]


@router.get("/optimized", response_model=List[InventoryWithDetails])
async def get_optimized_inventory(
    limit: int = Query(100, description="Number of items to return"),
    offset: int = Query(0, description="Number of items to skip"),
    item_id: Optional[int] = Query(None, description="Filter by item ID"),
    location_id: Optional[int] = Query(None, description="Filter by location ID"),
    optimized_service: OptimizedInventoryService = Depends(get_optimized_service)
):
    """
    Get inventory entries using optimized queries with caching and preloading.
    
    This endpoint is faster for large datasets as it uses optimized database queries
    and caching to reduce response times.
    """
    inventory_entries = await optimized_service.get_inventory_with_preloading(
        limit=limit,
        offset=offset,
        item_id=item_id,
        location_id=location_id
    )
    
    return [
        InventoryWithDetails(
            id=entry.id,
            item_id=entry.item_id,
            location_id=entry.location_id,
            quantity=entry.quantity,
            updated_at=entry.updated_at,
            total_value=entry.total_value,
            item=ItemSummary.model_validate(entry.item) if entry.item else None,
            location=LocationSummary(
                id=entry.location.id,
                name=entry.location.name,
                location_type=entry.location.location_type,
                child_count=0,
                item_count=0
            ) if entry.location else None
        )
        for entry in inventory_entries
    ]


@router.post("/", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
@invalidate_cache_on_changes("inventory_create")
async def create_inventory_entry(
    inventory_data: InventoryCreate,
    service: InventoryService = Depends(get_inventory_service)
):
    """
    Create a new inventory entry for an item at a location.
    
    - **item_id**: ID of the item to add to inventory
    - **location_id**: ID of the location where item is stored
    - **quantity**: Quantity of items at this location (default: 1)
    """
    try:
        inventory_entry = await service.create_inventory_entry(inventory_data)
        return InventoryResponse.model_validate(inventory_entry)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/move/{item_id}", response_model=InventoryResponse)
async def move_item(
    item_id: int,
    move_data: InventoryMove,
    service: InventoryService = Depends(get_inventory_service),
    validator: MovementValidator = Depends(get_movement_validator),
    movement_service: MovementService = Depends(get_movement_service)
):
    """
    Move items between locations with comprehensive validation.
    
    - **from_location_id**: Source location ID
    - **to_location_id**: Destination location ID  
    - **quantity**: Quantity to move
    
    Includes business rule validation and automatic movement history tracking.
    If moving all items from a location, the source inventory entry will be deleted.
    If the destination already has the item, quantities will be combined.
    """
    try:
        # Create movement data for validation
        movement_data = MovementHistoryCreate(
            item_id=item_id,
            from_location_id=move_data.from_location_id,
            to_location_id=move_data.to_location_id,
            quantity_moved=move_data.quantity,
            movement_type="move",
            reason=move_data.reason,
            user_id=getattr(move_data, 'user_id', None)
        )
        
        # Validate the movement
        validation_result = await validator.validate_movement_create(movement_data)
        
        if not validation_result.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Movement validation failed",
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings,
                    "business_rules_checked": validation_result.business_rules_applied
                }
            )
        
        # If there are warnings but validation passed, log them
        if validation_result.warnings:
            # In a real system, you might want to log these warnings
            pass
        
        # Perform the move
        inventory_entry = await service.move_item(item_id, move_data)
        
        return InventoryResponse.model_validate(inventory_entry)
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": e.message,
                "error_code": e.error_code,
                "details": e.details
            }
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/items/{item_id}/locations", response_model=List[InventoryWithDetails])
async def get_item_locations(
    item_id: int,
    service: InventoryService = Depends(get_inventory_service)
):
    """Get all locations where an item is stored."""
    inventory_entries = await service.get_item_locations(item_id)
    
    return [
        InventoryWithDetails(
            id=entry.id,
            item_id=entry.item_id,
            location_id=entry.location_id,
            quantity=entry.quantity,
            updated_at=entry.updated_at,
            total_value=entry.total_value,
            item=ItemSummary.model_validate(entry.item) if entry.item else None,
            location=LocationSummary(
                id=entry.location.id,
                name=entry.location.name,
                location_type=entry.location.location_type,
                child_count=0,  # We can set this to 0 for now
                item_count=0   # We can set this to 0 for now
            ) if entry.location else None
        )
        for entry in inventory_entries
    ]


@router.get("/locations/{location_id}/items", response_model=List[InventoryWithDetails])
async def get_location_items(
    location_id: int,
    service: InventoryService = Depends(get_inventory_service)
):
    """Get all items stored in a location."""
    inventory_entries = await service.get_location_items(location_id)
    
    return [
        InventoryWithDetails(
            id=entry.id,
            item_id=entry.item_id,
            location_id=entry.location_id,
            quantity=entry.quantity,
            updated_at=entry.updated_at,
            total_value=entry.total_value,
            item=ItemSummary.model_validate(entry.item) if entry.item else None,
            location=LocationSummary(
                id=entry.location.id,
                name=entry.location.name,
                location_type=entry.location.location_type,
                child_count=0,  # We can set this to 0 for now
                item_count=0   # We can set this to 0 for now
            ) if entry.location else None
        )
        for entry in inventory_entries
    ]


@router.get("/locations/{location_id}/report", response_model=LocationInventoryReport)
async def get_location_inventory_report(
    location_id: int,
    service: InventoryService = Depends(get_inventory_service)
):
    """Generate comprehensive inventory report for a location."""
    report = await service.get_location_inventory_report(location_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location with ID {location_id} not found"
        )
    
    return report


# Movement History Endpoints

@router.get("/history", response_model=List[MovementHistoryWithDetails])
async def get_movement_history(
    item_id: Optional[int] = Query(None, description="Filter by item ID"),
    location_id: Optional[int] = Query(None, description="Filter by either source or destination location ID"),
    from_location_id: Optional[int] = Query(None, description="Filter by source location ID"),
    to_location_id: Optional[int] = Query(None, description="Filter by destination location ID"),
    movement_type: Optional[str] = Query(None, description="Filter by movement type"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    start_date: Optional[datetime] = Query(None, description="Filter movements after this date"),
    end_date: Optional[datetime] = Query(None, description="Filter movements before this date"),
    min_quantity: Optional[int] = Query(None, description="Minimum quantity moved"),
    max_quantity: Optional[int] = Query(None, description="Maximum quantity moved"),
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(100, description="Maximum number of records to return"),
    service: MovementService = Depends(get_movement_service)
):
    """
    Get movement history with filtering and pagination.
    
    Returns chronological list of item movements including location changes,
    quantity adjustments, and audit trail information.
    """
    search_params = MovementHistorySearch(
        item_id=item_id,
        location_id=location_id,
        from_location_id=from_location_id,
        to_location_id=to_location_id,
        movement_type=movement_type,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        min_quantity=min_quantity,
        max_quantity=max_quantity
    )
    
    movements = await service.get_movement_history(search_params, skip, limit)
    
    return [
        MovementHistoryWithDetails(
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
            item=ItemSummary.model_validate(movement.item) if movement.item else None,
            from_location=LocationSummary(
                id=movement.from_location.id,
                name=movement.from_location.name,
                location_type=movement.from_location.location_type,
                child_count=0,
                item_count=0
            ) if movement.from_location else None,
            to_location=LocationSummary(
                id=movement.to_location.id,
                name=movement.to_location.name,
                location_type=movement.to_location.location_type,
                child_count=0,
                item_count=0
            ) if movement.to_location else None
        )
        for movement in movements
    ]


@router.get("/history/summary", response_model=MovementHistorySummary)
async def get_movement_history_summary(
    start_date: Optional[datetime] = Query(None, description="Filter movements after this date"),
    end_date: Optional[datetime] = Query(None, description="Filter movements before this date"),
    service: MovementService = Depends(get_movement_service)
):
    """
    Get movement history summary statistics.
    
    Provides overview of movement activity including totals, trends,
    and recent activity.
    """
    return await service.get_movement_summary(start_date, end_date)


@router.get("/items/{item_id}/timeline", response_model=ItemMovementTimeline)
async def get_item_movement_timeline(
    item_id: int,
    service: MovementService = Depends(get_movement_service)
):
    """
    Get complete movement timeline for a specific item.
    
    Returns chronological history of all movements for an item
    including current location status.
    """
    try:
        return await service.get_item_movement_timeline(item_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/{inventory_id}", response_model=InventoryWithDetails)
async def get_inventory_entry(
    inventory_id: int,
    service: InventoryService = Depends(get_inventory_service)
):
    """Get inventory entry by ID with item and location details."""
    inventory_entry = await service.get_inventory_entry(inventory_id)
    if not inventory_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory entry with ID {inventory_id} not found"
        )
    
    return InventoryWithDetails(
        id=inventory_entry.id,
        item_id=inventory_entry.item_id,
        location_id=inventory_entry.location_id,
        quantity=inventory_entry.quantity,
        updated_at=inventory_entry.updated_at,
        total_value=inventory_entry.total_value,
        item=inventory_entry.item,
        location=inventory_entry.location
    )


@router.put("/{inventory_id}", response_model=InventoryResponse)
async def update_inventory_entry(
    inventory_id: int,
    update_data: InventoryUpdate,
    service: InventoryService = Depends(get_inventory_service)
):
    """
    Update an inventory entry.
    
    Can update quantity or move item to a different location.
    """
    try:
        inventory_entry = await service.update_inventory_entry(inventory_id, update_data)
        if not inventory_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory entry with ID {inventory_id} not found"
            )
        
        return InventoryResponse.model_validate(inventory_entry)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{inventory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inventory_entry(
    inventory_id: int,
    service: InventoryService = Depends(get_inventory_service)
):
    """Delete an inventory entry."""
    success = await service.delete_inventory_entry(inventory_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory entry with ID {inventory_id} not found"
        )


# Advanced Quantity Operations

@router.post("/items/{item_id}/split", response_model=None)
async def split_item_quantity(
    item_id: int,
    split_data: dict,  # {source_location_id, dest_location_id, quantity_to_move, reason?}
    user_id: Optional[str] = Query(None, description="User performing the operation"),
    service: InventoryService = Depends(get_inventory_service),
    validator: MovementValidator = Depends(get_movement_validator)
):
    """
    Split item quantity between two locations with validation.
    
    Moves specified quantity from source location to destination location,
    maintaining accurate quantity tracking at both locations.
    Includes comprehensive business rule validation.
    """
    try:
        # Validate split operation
        movement_data = MovementHistoryCreate(
            item_id=item_id,
            from_location_id=split_data["source_location_id"],
            to_location_id=split_data["dest_location_id"],
            quantity_moved=split_data["quantity_to_move"],
            movement_type="split",
            reason=split_data.get("reason"),
            user_id=user_id
        )
        
        validation_result = await validator.validate_movement_create(movement_data)
        if not validation_result.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Split operation validation failed",
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings
                }
            )
        
        source_entry, dest_entry = await service.split_item_quantity(
            item_id=item_id,
            source_location_id=split_data["source_location_id"],
            dest_location_id=split_data["dest_location_id"],
            quantity_to_move=split_data["quantity_to_move"],
            user_id=user_id,
            reason=split_data.get("reason")
        )
        
        return [
            {
                "id": source_entry.id,
                "item_id": source_entry.item_id,
                "location_id": source_entry.location_id,
                "quantity": source_entry.quantity,
                "updated_at": source_entry.updated_at.isoformat() if source_entry.updated_at else None
            },
            {
                "id": dest_entry.id,
                "item_id": dest_entry.item_id,
                "location_id": dest_entry.location_id,
                "quantity": dest_entry.quantity,
                "updated_at": dest_entry.updated_at.isoformat() if dest_entry.updated_at else None
            }
        ]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/items/{item_id}/merge", response_model=None)
async def merge_item_quantities(
    item_id: int,
    merge_data: dict,  # {location_ids: List[int], target_location_id: int, reason?}
    user_id: Optional[str] = Query(None, description="User performing the operation"),
    service: InventoryService = Depends(get_inventory_service)
):
    """
    Merge item quantities from multiple locations into one target location.
    
    Consolidates all quantities from source locations into the target location,
    removing the source entries and creating/updating the target entry.
    """
    try:
        target_entry = await service.merge_item_quantities(
            item_id=item_id,
            location_ids=merge_data["location_ids"],
            target_location_id=merge_data["target_location_id"],
            user_id=user_id,
            reason=merge_data.get("reason")
        )
        
        return {
            "id": target_entry.id,
            "item_id": target_entry.item_id,
            "location_id": target_entry.location_id,
            "quantity": target_entry.quantity,
            "updated_at": target_entry.updated_at.isoformat() if target_entry.updated_at else None
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/items/{item_id}/locations/{location_id}/quantity", response_model=None)
async def adjust_item_quantity(
    item_id: int,
    location_id: int,
    adjustment_data: dict,  # {new_quantity: int, reason?}
    user_id: Optional[str] = Query(None, description="User performing the operation"),
    service: InventoryService = Depends(get_inventory_service)
):
    """
    Adjust item quantity at a specific location.
    
    Sets the quantity to the specified value. Use 0 to remove the item
    from the location entirely.
    """
    try:
        result_entry = await service.adjust_item_quantity(
            item_id=item_id,
            location_id=location_id,
            new_quantity=adjustment_data["new_quantity"],
            user_id=user_id,
            reason=adjustment_data.get("reason")
        )
        
        if result_entry:
            # Create a simple response without relying on SQLAlchemy properties
            return {
                "id": result_entry.id,
                "item_id": result_entry.item_id,
                "location_id": result_entry.location_id,
                "quantity": result_entry.quantity,
                "updated_at": result_entry.updated_at.isoformat() if result_entry.updated_at else None
            }
        else:
            # Entry was removed (quantity set to 0)
            return {"message": "Item removed from location", "item_id": item_id, "location_id": location_id}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Movement Validation Endpoints

@router.post("/validate/movement", response_model=None)
async def validate_movement_operation(
    movement_data: MovementHistoryCreate,
    enforce_strict: bool = Query(True, description="Enforce strict business rule validation"),
    validator: MovementValidator = Depends(get_movement_validator)
):
    """
    Validate a movement operation without executing it.
    
    Returns validation result with errors, warnings, and business rules applied.
    Useful for pre-validation in UI before attempting actual movement.
    """
    try:
        validation_result = await validator.validate_movement_create(
            movement_data, 
            enforce_strict_validation=enforce_strict
        )
        
        return {
            "is_valid": validation_result.is_valid,
            "errors": validation_result.errors,
            "warnings": validation_result.warnings,
            "business_rules_applied": validation_result.business_rules_applied,
            "validation_metadata": validation_result.validation_metadata
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation system error: {str(e)}"
        )


@router.post("/validate/bulk-movement", response_model=None)
async def validate_bulk_movement_operation(
    movements: List[MovementHistoryCreate],
    enforce_atomic: bool = Query(True, description="All movements must pass validation"),
    validator: MovementValidator = Depends(get_movement_validator)
):
    """
    Validate multiple movement operations as a batch.
    
    Returns overall validation result plus individual results for each movement.
    Includes cross-movement conflict detection.
    """
    try:
        overall_result, individual_results = await validator.validate_bulk_movement(
            movements, 
            enforce_atomic_validation=enforce_atomic
        )
        
        return {
            "overall_result": {
                "is_valid": overall_result.is_valid,
                "errors": overall_result.errors,
                "warnings": overall_result.warnings,
                "business_rules_applied": overall_result.business_rules_applied
            },
            "individual_results": [
                {
                    "movement_index": i,
                    "is_valid": result.is_valid,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "business_rules_applied": result.business_rules_applied
                }
                for i, result in enumerate(individual_results)
            ],
            "total_movements": len(movements),
            "valid_movements": sum(1 for r in individual_results if r.is_valid),
            "failed_movements": sum(1 for r in individual_results if not r.is_valid)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk validation system error: {str(e)}"
        )


@router.get("/validation/report", response_model=None)
async def get_validation_report(
    item_id: Optional[int] = Query(None, description="Filter report by specific item"),
    validator: MovementValidator = Depends(get_movement_validator)
):
    """
    Get comprehensive validation system report.
    
    Includes business rules configuration, validation statistics,
    recent failures, and system health metrics.
    """
    try:
        report = await validator.get_validation_report(item_id)
        return report
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate validation report: {str(e)}"
        )


@router.post("/validation/rules/override", response_model=None)
async def apply_business_rule_overrides(
    overrides: dict,  # {rule_name: {enabled: bool, ...other_config}}
    validator: MovementValidator = Depends(get_movement_validator)
):
    """
    Apply temporary business rule overrides.
    
    Allows runtime modification of business rules for special cases.
    Overrides are not persistent and will reset on service restart.
    """
    try:
        await validator.apply_business_rule_overrides(overrides)
        
        return {
            "message": "Business rule overrides applied successfully",
            "overrides_applied": overrides,
            "active_rules": validator.business_rules
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply business rule overrides: {str(e)}"
        )