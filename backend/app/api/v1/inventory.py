"""
Inventory API endpoints for the Home Inventory System.

Handles inventory management operations including item-location relationships,
quantity tracking, and movement between locations.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import get_session
from app.services.inventory_service import InventoryService
from app.schemas.inventory import (
    InventoryCreate, InventoryUpdate, InventoryResponse, InventoryWithDetails,
    InventorySearch, InventoryMove, InventorySummary, InventoryBulkOperation,
    ItemLocationHistory, LocationInventoryReport
)

router = APIRouter()


def get_inventory_service(db: AsyncSession = Depends(get_session)) -> InventoryService:
    """Dependency to get inventory service."""
    return InventoryService(db)


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
            item=entry.item,
            location=entry.location
        )
        for entry in inventory_entries
    ]


@router.post("/", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
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
    service: InventoryService = Depends(get_inventory_service)
):
    """
    Move items between locations.
    
    - **from_location_id**: Source location ID
    - **to_location_id**: Destination location ID  
    - **quantity**: Quantity to move
    
    If moving all items from a location, the source inventory entry will be deleted.
    If the destination already has the item, quantities will be combined.
    """
    try:
        inventory_entry = await service.move_item(item_id, move_data)
        return InventoryResponse.model_validate(inventory_entry)
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
            item=entry.item,
            location=entry.location
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
            item=entry.item,
            location=entry.location
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