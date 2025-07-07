"""
Location API endpoints for CRUD operations.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database.base import get_async_session
from app.models.location import Location, LocationType
from app.schemas.location import (
    LocationCreate,
    LocationUpdate,
    LocationResponse,
    LocationWithChildren,
    LocationTree,
    LocationSearchQuery,
    LocationValidationResponse,
)
from app.core.logging import get_logger

logger = get_logger("api.locations")
router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("/", response_model=List[LocationResponse])
async def get_locations(
    skip: int = Query(0, ge=0, description="Number of locations to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of locations to return"),
    location_type: Optional[LocationType] = Query(None, description="Filter by location type"),
    parent_id: Optional[int] = Query(None, description="Filter by parent location ID"),
    session: AsyncSession = Depends(get_async_session),
) -> List[LocationResponse]:
    """Get a list of locations with optional filtering."""
    
    logger.info(f"Fetching locations: skip={skip}, limit={limit}, type={location_type}, parent_id={parent_id}")
    
    # Build query with filters and eager loading
    query = (
        select(Location)
        .offset(skip)
        .limit(limit)
        .options(selectinload(Location.parent))
    )
    
    if location_type:
        query = query.where(Location.location_type == location_type)
    
    if parent_id is not None:
        query = query.where(Location.parent_id == parent_id)
    
    result = await session.execute(query)
    locations = result.scalars().all()
    
    logger.info(f"Found {len(locations)} locations")
    return [LocationResponse.model_validate(location) for location in locations]


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> LocationResponse:
    """Get a specific location by ID."""
    
    logger.info(f"Fetching location ID: {location_id}")
    
    result = await session.execute(
        select(Location)
        .where(Location.id == location_id)
        .options(selectinload(Location.parent))
    )
    location = result.scalar_one_or_none()
    
    if not location:
        logger.warning(f"Location not found: {location_id}")
        raise HTTPException(status_code=404, detail="Location not found")
    
    logger.info(f"Found location: {location.name}")
    return LocationResponse.model_validate(location)


@router.get("/{location_id}/children", response_model=List[LocationResponse])
async def get_location_children(
    location_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> List[LocationResponse]:
    """Get all direct children of a location."""
    
    logger.info(f"Fetching children for location ID: {location_id}")
    
    # Verify parent exists
    parent_result = await session.execute(
        select(Location).where(Location.id == location_id)
    )
    parent = parent_result.scalar_one_or_none()
    
    if not parent:
        logger.warning(f"Parent location not found: {location_id}")
        raise HTTPException(status_code=404, detail="Parent location not found")
    
    # Get children
    result = await session.execute(
        select(Location)
        .where(Location.parent_id == location_id)
        .options(selectinload(Location.parent))
    )
    children = result.scalars().all()
    
    logger.info(f"Found {len(children)} children for location: {parent.name}")
    return [LocationResponse.model_validate(child) for child in children]


@router.get("/{location_id}/tree", response_model=LocationTree)
async def get_location_tree(
    location_id: int,
    max_depth: int = Query(5, ge=1, le=10, description="Maximum depth to traverse"),
    session: AsyncSession = Depends(get_async_session),
) -> LocationTree:
    """Get a location and its descendants as a tree structure."""
    
    logger.info(f"Building tree for location ID: {location_id}, max_depth: {max_depth}")
    
    async def build_tree(location: Location, current_depth: int) -> LocationTree:
        """Recursively build location tree."""
        tree = LocationTree(
            location=LocationResponse.model_validate(location),
            children=[]
        )
        
        if current_depth < max_depth:
            # Get children with eager loading
            result = await session.execute(
                select(Location)
                .where(Location.parent_id == location.id)
                .options(selectinload(Location.children))
            )
            children = result.scalars().all()
            
            for child in children:
                child_tree = await build_tree(child, current_depth + 1)
                tree.children.append(child_tree)
        
        return tree
    
    # Get root location
    result = await session.execute(
        select(Location)
        .where(Location.id == location_id)
        .options(selectinload(Location.children))
    )
    location = result.scalar_one_or_none()
    
    if not location:
        logger.warning(f"Location not found: {location_id}")
        raise HTTPException(status_code=404, detail="Location not found")
    
    tree = await build_tree(location, 0)
    logger.info(f"Built tree for location: {location.name}")
    return tree


@router.post("/", response_model=LocationResponse, status_code=201)
async def create_location(
    location_data: LocationCreate,
    session: AsyncSession = Depends(get_async_session),
) -> LocationResponse:
    """Create a new location."""
    
    logger.info(f"Creating location: {location_data.name} ({location_data.location_type})")
    
    # Validate parent exists if specified
    if location_data.parent_id is not None:
        parent_result = await session.execute(
            select(Location).where(Location.id == location_data.parent_id)
        )
        parent = parent_result.scalar_one_or_none()
        
        if not parent:
            logger.warning(f"Parent location not found: {location_data.parent_id}")
            raise HTTPException(status_code=400, detail="Parent location not found")
    
    # Validate category exists if specified
    if location_data.category_id is not None:
        from app.models.category import Category
        category_result = await session.execute(
            select(Category).where(Category.id == location_data.category_id)
        )
        category = category_result.scalar_one_or_none()
        
        if not category:
            logger.warning(f"Category not found: {location_data.category_id}")
            raise HTTPException(status_code=400, detail="Category not found")
    
    # Create location
    location = Location(
        name=location_data.name,
        description=location_data.description,
        location_type=location_data.location_type,
        parent_id=location_data.parent_id,
        category_id=location_data.category_id,
    )
    
    session.add(location)
    await session.commit()
    await session.refresh(location)
    
    logger.info(f"Created location: {location.name} (ID: {location.id})")
    return LocationResponse.model_validate(location)


@router.put("/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: int,
    location_data: LocationUpdate,
    session: AsyncSession = Depends(get_async_session),
) -> LocationResponse:
    """Update an existing location."""
    
    logger.info(f"Updating location ID: {location_id}")
    
    # Get existing location
    result = await session.execute(
        select(Location).where(Location.id == location_id)
    )
    location = result.scalar_one_or_none()
    
    if not location:
        logger.warning(f"Location not found: {location_id}")
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Validate new parent if specified
    if location_data.parent_id is not None and location_data.parent_id != location.parent_id:
        # Check that new parent exists
        parent_result = await session.execute(
            select(Location).where(Location.id == location_data.parent_id)
        )
        parent = parent_result.scalar_one_or_none()
        
        if not parent:
            logger.warning(f"New parent location not found: {location_data.parent_id}")
            raise HTTPException(status_code=400, detail="New parent location not found")
        
        # Check for circular reference
        if location_data.parent_id == location_id:
            logger.warning(f"Cannot set location as its own parent: {location_id}")
            raise HTTPException(status_code=400, detail="Location cannot be its own parent")
    
    # Validate new category if specified
    if location_data.category_id is not None and location_data.category_id != location.category_id:
        from app.models.category import Category
        category_result = await session.execute(
            select(Category).where(Category.id == location_data.category_id)
        )
        category = category_result.scalar_one_or_none()
        
        if not category:
            logger.warning(f"New category not found: {location_data.category_id}")
            raise HTTPException(status_code=400, detail="New category not found")
    
    # Update fields
    update_data = location_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(location, field, value)
    
    await session.commit()
    await session.refresh(location)
    
    logger.info(f"Updated location: {location.name} (ID: {location.id})")
    return LocationResponse.model_validate(location)


@router.delete("/{location_id}", status_code=204)
async def delete_location(
    location_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> None:
    """Delete a location and all its descendants."""
    
    logger.info(f"Deleting location ID: {location_id}")
    
    # Get location
    result = await session.execute(
        select(Location).where(Location.id == location_id)
    )
    location = result.scalar_one_or_none()
    
    if not location:
        logger.warning(f"Location not found: {location_id}")
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Count descendants for logging
    descendants = location.get_all_descendants()
    descendant_count = len(descendants)
    
    # Delete location (cascade will handle descendants)
    await session.delete(location)
    await session.commit()
    
    logger.info(f"Deleted location: {location.name} and {descendant_count} descendants")


@router.post("/search", response_model=List[LocationResponse])
async def search_locations(
    search_query: LocationSearchQuery,
    session: AsyncSession = Depends(get_async_session),
) -> List[LocationResponse]:
    """Search locations with advanced filtering."""
    
    logger.info(f"Searching locations with query: {search_query}")
    
    # Build base query with eager loading
    query = select(Location).options(selectinload(Location.parent))
    
    # Apply filters
    if search_query.location_type:
        query = query.where(Location.location_type == search_query.location_type)
    
    if search_query.parent_id is not None:
        query = query.where(Location.parent_id == search_query.parent_id)
    
    # Execute query
    result = await session.execute(query)
    locations = result.scalars().all()
    
    # Apply pattern search in memory (for simplicity)
    if search_query.pattern:
        locations = Location.find_by_pattern(search_query.pattern, locations)
    
    # Apply depth filter if specified
    if search_query.max_depth is not None:
        locations = [loc for loc in locations if loc.depth <= search_query.max_depth]
    
    logger.info(f"Found {len(locations)} locations matching search criteria")
    return [LocationResponse.model_validate(location) for location in locations]


@router.post("/{location_id}/validate", response_model=LocationValidationResponse)
async def validate_location(
    location_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> LocationValidationResponse:
    """Validate a location's hierarchy and constraints."""
    
    logger.info(f"Validating location ID: {location_id}")
    
    # Get location
    result = await session.execute(
        select(Location)
        .where(Location.id == location_id)
        .options(selectinload(Location.parent))
    )
    location = result.scalar_one_or_none()
    
    if not location:
        logger.warning(f"Location not found: {location_id}")
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Run validation
    errors = []
    
    # Hierarchy validation
    if not location.validate_hierarchy():
        errors.append("Circular reference detected in hierarchy")
    
    # Type order validation
    if not location.validate_location_type_order():
        errors.append("Invalid location type nesting order")
    
    is_valid = len(errors) == 0
    
    logger.info(f"Validation result for {location.name}: {'valid' if is_valid else 'invalid'}")
    return LocationValidationResponse(is_valid=is_valid, errors=errors)


@router.get("/stats/summary")
async def get_location_stats(
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """Get summary statistics about locations."""
    
    logger.info("Generating location statistics")
    
    # Total count
    total_result = await session.execute(select(func.count(Location.id)))
    total_count = total_result.scalar()
    
    # Count by type
    type_stats = {}
    for location_type in LocationType:
        result = await session.execute(
            select(func.count(Location.id)).where(Location.location_type == location_type)
        )
        type_stats[location_type.value] = result.scalar()
    
    # Root locations count
    root_result = await session.execute(
        select(func.count(Location.id)).where(Location.parent_id.is_(None))
    )
    root_count = root_result.scalar()
    
    stats = {
        "total_locations": total_count,
        "by_type": type_stats,
        "root_locations": root_count,
    }
    
    logger.info(f"Generated stats: {stats}")
    return stats