"""
Items API endpoints for the Home Inventory System.

Provides comprehensive CRUD operations and advanced functionality for managing inventory items.
"""

from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, and_, or_
from sqlalchemy.orm import selectinload
from decimal import Decimal
from datetime import datetime

from app.database.base import get_session
from app.models import Item, ItemType, ItemCondition, ItemStatus, Location, Category
from app.schemas import (
    ItemCreate, ItemUpdate, ItemResponse, ItemSummary, ItemSearch,
    ItemBulkUpdate, ItemMoveRequest, ItemStatusUpdate, ItemConditionUpdate,
    ItemValueUpdate, ItemStatistics, ItemTagResponse, ItemImportRequest,
    ItemImportResult, ItemExportRequest
)
from app.core.logging import get_logger

logger = get_logger("items_api")

router = APIRouter(prefix="/items", tags=["items"])


async def get_item_by_id(
    item_id: int, 
    session: AsyncSession = Depends(get_session),
    include_inactive: bool = False
) -> Item:
    """Get item by ID with error handling."""
    query = select(Item).where(Item.id == item_id)
    if not include_inactive:
        query = query.where(Item.is_active == True)
    
    result = await session.execute(query)
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail=f"Item with id {item_id} not found")
    
    return item


def build_item_search_query(search: ItemSearch, session: AsyncSession):
    """Build complex search query for items."""
    query = select(Item).options(
        selectinload(Item.location),
        selectinload(Item.category)
    )
    
    # Base filter for active items unless specified
    if not hasattr(search, 'include_inactive') or not search.include_inactive:
        query = query.where(Item.is_active == True)
    
    # Text search
    if search.search_text:
        search_term = f"%{search.search_text}%"
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
    if search.item_type:
        query = query.where(Item.item_type == search.item_type)
    if search.condition:
        query = query.where(Item.condition == search.condition)
    if search.status:
        query = query.where(Item.status == search.status)
    
    # Relationship filters
    if search.location_id:
        query = query.where(Item.location_id == search.location_id)
    if search.category_id:
        query = query.where(Item.category_id == search.category_id)
    
    # Brand filter
    if search.brand:
        query = query.where(Item.brand.ilike(f"%{search.brand}%"))
    
    # Value filters
    if search.min_value is not None:
        query = query.where(Item.current_value >= search.min_value)
    if search.max_value is not None:
        query = query.where(Item.current_value <= search.max_value)
    
    # Date filters
    if search.purchased_after:
        query = query.where(Item.purchase_date >= search.purchased_after)
    if search.purchased_before:
        query = query.where(Item.purchase_date <= search.purchased_before)
    if search.warranty_expiring_before:
        query = query.where(Item.warranty_expiry <= search.warranty_expiring_before)
    
    # Special filters
    if search.has_warranty is not None:
        if search.has_warranty:
            query = query.where(
                and_(
                    Item.warranty_expiry.is_not(None),
                    Item.warranty_expiry > func.now()
                )
            )
        else:
            query = query.where(
                or_(
                    Item.warranty_expiry.is_(None),
                    Item.warranty_expiry <= func.now()
                )
            )
    
    if search.is_valuable is not None:
        if search.is_valuable:
            query = query.where(
                or_(
                    Item.current_value >= 100,
                    Item.purchase_price >= 100
                )
            )
        else:
            query = query.where(
                and_(
                    or_(Item.current_value.is_(None), Item.current_value < 100),
                    or_(Item.purchase_price.is_(None), Item.purchase_price < 100)
                )
            )
    
    if search.has_serial_number is not None:
        if search.has_serial_number:
            query = query.where(Item.serial_number.is_not(None))
        else:
            query = query.where(Item.serial_number.is_(None))
    
    if search.has_barcode is not None:
        if search.has_barcode:
            query = query.where(Item.barcode.is_not(None))
        else:
            query = query.where(Item.barcode.is_(None))
    
    # Tag filter
    if search.tags:
        tag_terms = [tag.strip() for tag in search.tags.split(',')]
        tag_conditions = [Item.tags.ilike(f"%{tag}%") for tag in tag_terms]
        query = query.where(or_(*tag_conditions))
    
    # Sorting
    sort_field = getattr(Item, search.sort_by, Item.name)
    if search.sort_order == "desc":
        query = query.order_by(desc(sort_field))
    else:
        query = query.order_by(asc(sort_field))
    
    # Pagination
    if search.skip:
        query = query.offset(search.skip)
    if search.limit:
        query = query.limit(search.limit)
    
    return query


def enhance_item_response(item: Item) -> Dict[str, Any]:
    """Enhance item data with computed fields."""
    item_dict = {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "item_type": item.item_type,
        "condition": item.condition,
        "status": item.status,
        "brand": item.brand,
        "model": item.model,
        "serial_number": item.serial_number,
        "barcode": item.barcode,
        "purchase_price": item.purchase_price,
        "current_value": item.current_value,
        "purchase_date": item.purchase_date,
        "warranty_expiry": item.warranty_expiry,
        "weight": item.weight,
        "dimensions": item.dimensions,
        "color": item.color,
        "location_id": item.location_id,
        "category_id": item.category_id,
        "is_active": item.is_active,
        "version": item.version,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "notes": item.notes,
        "tags": item.tags,
        
        # Computed fields
        "display_name": item.display_name,
        "full_location_path": item.full_location_path,
        "is_valuable": item.is_valuable,
        "age_days": item.age_days,
        "is_under_warranty": item.is_under_warranty,
        "tag_list": item.get_tag_list()
    }
    
    return item_dict


@router.post("/", response_model=ItemResponse, status_code=201)
async def create_item(
    item_data: ItemCreate,
    session: AsyncSession = Depends(get_session)
):
    """Create a new item."""
    
    # Validate that location exists
    location_query = select(Location).where(Location.id == item_data.location_id)
    location_result = await session.execute(location_query)
    location = location_result.scalar_one_or_none()
    
    if not location:
        raise HTTPException(status_code=400, detail=f"Location with id {item_data.location_id} not found")
    
    # Validate category if provided
    if item_data.category_id:
        category_query = select(Category).where(Category.id == item_data.category_id)
        category_result = await session.execute(category_query)
        category = category_result.scalar_one_or_none()
        
        if not category:
            raise HTTPException(status_code=400, detail=f"Category with id {item_data.category_id} not found")
    
    # Check for duplicate serial number
    if item_data.serial_number:
        duplicate_serial_query = select(Item).where(Item.serial_number == item_data.serial_number)
        duplicate_result = await session.execute(duplicate_serial_query)
        if duplicate_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Item with serial number '{item_data.serial_number}' already exists")
    
    # Check for duplicate barcode
    if item_data.barcode:
        duplicate_barcode_query = select(Item).where(Item.barcode == item_data.barcode)
        duplicate_result = await session.execute(duplicate_barcode_query)
        if duplicate_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Item with barcode '{item_data.barcode}' already exists")
    
    # Create item
    item = Item(**item_data.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    
    logger.info(f"Created item: {item.name} (ID: {item.id})")
    
    return enhance_item_response(item)


@router.get("/", response_model=List[ItemSummary])
async def list_items(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=1000, description="Number of items to return"),
    item_type: Optional[ItemType] = Query(None, description="Filter by item type"),
    status: Optional[ItemStatus] = Query(None, description="Filter by status"),
    location_id: Optional[int] = Query(None, description="Filter by location"),
    category_id: Optional[int] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search in item names and descriptions"),
    session: AsyncSession = Depends(get_session)
):
    """List items with optional filtering."""
    
    query = select(Item).where(Item.is_active == True)
    
    # Apply filters
    if item_type:
        query = query.where(Item.item_type == item_type)
    if status:
        query = query.where(Item.status == status)
    if location_id:
        query = query.where(Item.location_id == location_id)
    if category_id:
        query = query.where(Item.category_id == category_id)
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Item.name.ilike(search_term),
                Item.description.ilike(search_term),
                Item.brand.ilike(search_term),
                Item.model.ilike(search_term)
            )
        )
    
    # Apply pagination and sorting
    query = query.order_by(Item.name).offset(skip).limit(limit)
    
    result = await session.execute(query)
    items = result.scalars().all()
    
    return items


@router.post("/search", response_model=List[ItemResponse])
async def search_items(
    search: ItemSearch,
    session: AsyncSession = Depends(get_session)
):
    """Advanced item search with complex filtering."""
    
    query = build_item_search_query(search, session)
    result = await session.execute(query)
    items = result.scalars().all()
    
    return [enhance_item_response(item) for item in items]


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Get a specific item by ID."""
    
    item = await get_item_by_id(item_id, session)
    
    # Load relationships
    await session.refresh(item, ["location", "category"])
    
    return enhance_item_response(item)


@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: int,
    item_data: ItemUpdate,
    session: AsyncSession = Depends(get_session)
):
    """Update an existing item."""
    
    item = await get_item_by_id(item_id, session)
    
    # Validate location if being updated
    if item_data.location_id and item_data.location_id != item.location_id:
        location_query = select(Location).where(Location.id == item_data.location_id)
        location_result = await session.execute(location_query)
        location = location_result.scalar_one_or_none()
        
        if not location:
            raise HTTPException(status_code=400, detail=f"Location with id {item_data.location_id} not found")
    
    # Validate category if being updated
    if item_data.category_id and item_data.category_id != item.category_id:
        category_query = select(Category).where(Category.id == item_data.category_id)
        category_result = await session.execute(category_query)
        category = category_result.scalar_one_or_none()
        
        if not category:
            raise HTTPException(status_code=400, detail=f"Category with id {item_data.category_id} not found")
    
    # Check for duplicate serial number (exclude current item)
    if item_data.serial_number and item_data.serial_number != item.serial_number:
        duplicate_serial_query = select(Item).where(
            and_(Item.serial_number == item_data.serial_number, Item.id != item_id)
        )
        duplicate_result = await session.execute(duplicate_serial_query)
        if duplicate_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Item with serial number '{item_data.serial_number}' already exists")
    
    # Check for duplicate barcode (exclude current item)
    if item_data.barcode and item_data.barcode != item.barcode:
        duplicate_barcode_query = select(Item).where(
            and_(Item.barcode == item_data.barcode, Item.id != item_id)
        )
        duplicate_result = await session.execute(duplicate_barcode_query)
        if duplicate_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Item with barcode '{item_data.barcode}' already exists")
    
    # Update fields
    update_data = item_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    item.version += 1
    session.add(item)
    await session.commit()
    await session.refresh(item)
    
    logger.info(f"Updated item: {item.name} (ID: {item.id})")
    
    return enhance_item_response(item)


@router.delete("/{item_id}", status_code=204)
async def delete_item(
    item_id: int,
    permanent: bool = Query(False, description="Permanently delete (default is soft delete)"),
    session: AsyncSession = Depends(get_session)
):
    """Delete an item (soft delete by default)."""
    
    item = await get_item_by_id(item_id, session, include_inactive=True)
    
    if permanent:
        # Permanent delete
        await session.delete(item)
        logger.info(f"Permanently deleted item: {item.name} (ID: {item.id})")
    else:
        # Soft delete
        item.soft_delete("Deleted via API")
        session.add(item)
        logger.info(f"Soft deleted item: {item.name} (ID: {item.id})")
    
    await session.commit()


@router.post("/{item_id}/restore", response_model=ItemResponse)
async def restore_item(
    item_id: int,
    new_status: ItemStatus = ItemStatus.AVAILABLE,
    session: AsyncSession = Depends(get_session)
):
    """Restore a soft-deleted item."""
    
    item = await get_item_by_id(item_id, session, include_inactive=True)
    
    if item.is_active:
        raise HTTPException(status_code=400, detail="Item is not deleted")
    
    item.restore(new_status)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    
    logger.info(f"Restored item: {item.name} (ID: {item.id})")
    
    return enhance_item_response(item)


@router.post("/bulk-update", response_model=List[ItemResponse])
async def bulk_update_items(
    bulk_update: ItemBulkUpdate,
    session: AsyncSession = Depends(get_session)
):
    """Update multiple items at once."""
    
    # Get all items
    query = select(Item).where(
        and_(Item.id.in_(bulk_update.item_ids), Item.is_active == True)
    )
    result = await session.execute(query)
    items = result.scalars().all()
    
    if len(items) != len(bulk_update.item_ids):
        found_ids = [item.id for item in items]
        missing_ids = [id for id in bulk_update.item_ids if id not in found_ids]
        raise HTTPException(status_code=404, detail=f"Items not found: {missing_ids}")
    
    # Apply updates
    update_data = bulk_update.updates.model_dump(exclude_unset=True)
    updated_items = []
    
    for item in items:
        for field, value in update_data.items():
            setattr(item, field, value)
        item.version += 1
        session.add(item)
        updated_items.append(item)
    
    await session.commit()
    
    # Refresh items
    for item in updated_items:
        await session.refresh(item)
    
    logger.info(f"Bulk updated {len(updated_items)} items")
    
    return [enhance_item_response(item) for item in updated_items]


@router.post("/move", response_model=List[ItemResponse])
async def move_items(
    move_request: ItemMoveRequest,
    session: AsyncSession = Depends(get_session)
):
    """Move multiple items to a new location."""
    
    # Validate target location
    location_query = select(Location).where(Location.id == move_request.new_location_id)
    location_result = await session.execute(location_query)
    location = location_result.scalar_one_or_none()
    
    if not location:
        raise HTTPException(status_code=400, detail=f"Location with id {move_request.new_location_id} not found")
    
    # Get all items
    query = select(Item).where(
        and_(Item.id.in_(move_request.item_ids), Item.is_active == True)
    )
    result = await session.execute(query)
    items = result.scalars().all()
    
    if len(items) != len(move_request.item_ids):
        found_ids = [item.id for item in items]
        missing_ids = [id for id in move_request.item_ids if id not in found_ids]
        raise HTTPException(status_code=404, detail=f"Items not found: {missing_ids}")
    
    # Move items
    moved_items = []
    for item in items:
        item.move_to_location(move_request.new_location_id)
        if move_request.notes:
            note_text = f"Moved to {location.name}: {move_request.notes}"
            if item.notes:
                item.notes += f"\n{datetime.now().strftime('%Y-%m-%d')}: {note_text}"
            else:
                item.notes = f"{datetime.now().strftime('%Y-%m-%d')}: {note_text}"
        
        session.add(item)
        moved_items.append(item)
    
    await session.commit()
    
    # Refresh items
    for item in moved_items:
        await session.refresh(item)
    
    logger.info(f"Moved {len(moved_items)} items to location {location.name}")
    
    return [enhance_item_response(item) for item in moved_items]


@router.put("/{item_id}/status", response_model=ItemResponse)
async def update_item_status(
    item_id: int,
    status_update: ItemStatusUpdate,
    session: AsyncSession = Depends(get_session)
):
    """Update item status."""
    
    item = await get_item_by_id(item_id, session)
    
    item.update_status(status_update.new_status, status_update.notes)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    
    logger.info(f"Updated status for item {item.name} to {status_update.new_status.value}")
    
    return enhance_item_response(item)


@router.put("/{item_id}/condition", response_model=ItemResponse)
async def update_item_condition(
    item_id: int,
    condition_update: ItemConditionUpdate,
    session: AsyncSession = Depends(get_session)
):
    """Update item condition."""
    
    item = await get_item_by_id(item_id, session)
    
    item.update_condition(condition_update.new_condition, condition_update.notes)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    
    logger.info(f"Updated condition for item {item.name} to {condition_update.new_condition.value}")
    
    return enhance_item_response(item)


@router.put("/{item_id}/value", response_model=ItemResponse)
async def update_item_value(
    item_id: int,
    value_update: ItemValueUpdate,
    session: AsyncSession = Depends(get_session)
):
    """Update item current value."""
    
    item = await get_item_by_id(item_id, session)
    
    item.update_value(value_update.new_value, value_update.notes)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    
    logger.info(f"Updated value for item {item.name} to ${value_update.new_value}")
    
    return enhance_item_response(item)


@router.get("/{item_id}/tags", response_model=ItemTagResponse)
async def get_item_tags(
    item_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Get item tags."""
    
    item = await get_item_by_id(item_id, session)
    
    return ItemTagResponse(
        item_id=item.id,
        tags=item.get_tag_list()
    )


@router.post("/{item_id}/tags/{tag}", response_model=ItemTagResponse)
async def add_item_tag(
    item_id: int,
    tag: str,
    session: AsyncSession = Depends(get_session)
):
    """Add a tag to an item."""
    
    item = await get_item_by_id(item_id, session)
    
    item.add_tag(tag)
    session.add(item)
    await session.commit()
    
    logger.info(f"Added tag '{tag}' to item {item.name}")
    
    return ItemTagResponse(
        item_id=item.id,
        tags=item.get_tag_list()
    )


@router.delete("/{item_id}/tags/{tag}", response_model=ItemTagResponse)
async def remove_item_tag(
    item_id: int,
    tag: str,
    session: AsyncSession = Depends(get_session)
):
    """Remove a tag from an item."""
    
    item = await get_item_by_id(item_id, session)
    
    item.remove_tag(tag)
    session.add(item)
    await session.commit()
    
    logger.info(f"Removed tag '{tag}' from item {item.name}")
    
    return ItemTagResponse(
        item_id=item.id,
        tags=item.get_tag_list()
    )


@router.get("/statistics/overview", response_model=ItemStatistics)
async def get_item_statistics(
    session: AsyncSession = Depends(get_session)
):
    """Get comprehensive item statistics."""
    
    # Basic counts
    total_query = select(func.count(Item.id))
    total_result = await session.execute(total_query)
    total_items = total_result.scalar()
    
    active_query = select(func.count(Item.id)).where(Item.is_active == True)
    active_result = await session.execute(active_query)
    active_items = active_result.scalar()
    
    # Value statistics
    value_query = select(
        func.sum(Item.current_value),
        func.avg(Item.current_value)
    ).where(
        and_(Item.is_active == True, Item.current_value.is_not(None))
    )
    value_result = await session.execute(value_query)
    total_value, avg_value = value_result.first()
    
    # Count by type
    type_query = select(Item.item_type, func.count(Item.id)).where(
        Item.is_active == True
    ).group_by(Item.item_type)
    type_result = await session.execute(type_query)
    by_type = {row[0].value: row[1] for row in type_result}
    
    # Count by condition
    condition_query = select(Item.condition, func.count(Item.id)).where(
        Item.is_active == True
    ).group_by(Item.condition)
    condition_result = await session.execute(condition_query)
    by_condition = {row[0].value: row[1] for row in condition_result}
    
    # Count by status
    status_query = select(Item.status, func.count(Item.id)).where(
        Item.is_active == True
    ).group_by(Item.status)
    status_result = await session.execute(status_query)
    by_status = {row[0].value: row[1] for row in status_result}
    
    # Special counts
    warranty_query = select(func.count(Item.id)).where(
        and_(
            Item.is_active == True,
            Item.warranty_expiry.is_not(None),
            Item.warranty_expiry > func.now()
        )
    )
    warranty_result = await session.execute(warranty_query)
    items_under_warranty = warranty_result.scalar()
    
    valuable_query = select(func.count(Item.id)).where(
        and_(
            Item.is_active == True,
            or_(
                Item.current_value >= 100,
                Item.purchase_price >= 100
            )
        )
    )
    valuable_result = await session.execute(valuable_query)
    valuable_items = valuable_result.scalar()
    
    serial_query = select(func.count(Item.id)).where(
        and_(Item.is_active == True, Item.serial_number.is_not(None))
    )
    serial_result = await session.execute(serial_query)
    items_with_serial = serial_result.scalar()
    
    barcode_query = select(func.count(Item.id)).where(
        and_(Item.is_active == True, Item.barcode.is_not(None))
    )
    barcode_result = await session.execute(barcode_query)
    items_with_barcode = barcode_result.scalar()
    
    return ItemStatistics(
        total_items=total_items,
        active_items=active_items,
        total_value=total_value,
        average_value=avg_value,
        by_type=by_type,
        by_condition=by_condition,
        by_status=by_status,
        items_under_warranty=items_under_warranty,
        valuable_items=valuable_items,
        items_with_serial=items_with_serial,
        items_with_barcode=items_with_barcode
    )