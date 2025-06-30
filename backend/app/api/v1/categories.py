"""Category API routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from app.database.base import get_session
from app.models.category import Category
from app.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryListResponse,
    CategoryStats
)
from app.core.logging import get_logger

# Get logger
logger = get_logger("categories_api")

# Create router
router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=CategoryListResponse, summary="List categories")
async def list_categories(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    include_inactive: bool = Query(False, description="Include inactive categories"),
    search: Optional[str] = Query(None, description="Search by category name"),
    session: AsyncSession = Depends(get_session)
):
    """
    Retrieve a paginated list of categories.
    
    - **page**: Page number (1-based indexing)
    - **per_page**: Number of items per page (max 100)
    - **include_inactive**: Whether to include inactive categories
    - **search**: Optional search term to filter by category name
    """
    logger.info(f"Listing categories - page: {page}, per_page: {per_page}, search: {search}")
    
    try:
        # Build query
        query = select(Category)
        
        # Filter by active status
        if not include_inactive:
            query = query.where(Category.is_active == True)
        
        # Search filter
        if search:
            search_term = f"%{search.strip()}%"
            query = query.where(Category.name.ilike(search_term))
        
        # Order by name
        query = query.order_by(Category.name)
        
        # Count total records
        count_query = select(func.count()).select_from(query.subquery())
        total = await session.scalar(count_query)
        
        # Calculate pagination
        offset = (page - 1) * per_page
        pages = (total + per_page - 1) // per_page
        
        # Apply pagination
        query = query.offset(offset).limit(per_page)
        
        # Execute query
        result = await session.execute(query)
        categories = result.scalars().all()
        
        logger.info(f"Found {len(categories)} categories (total: {total})")
        
        return CategoryListResponse(
            categories=categories,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )
        
    except Exception as e:
        logger.error(f"Failed to list categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve categories")


@router.get("/stats", response_model=CategoryStats, summary="Get category statistics")
async def get_category_stats(
    session: AsyncSession = Depends(get_session)
):
    """Get category statistics and analytics."""
    logger.info("Getting category statistics")
    
    try:
        # Total active categories
        total_categories = await session.scalar(
            select(func.count(Category.id)).where(Category.is_active == True)
        )
        
        # Inactive categories
        inactive_categories = await session.scalar(
            select(func.count(Category.id)).where(Category.is_active == False)
        )
        
        # Most used color
        most_used_color_result = await session.execute(
            select(Category.color, func.count(Category.color).label('count'))
            .where(Category.is_active == True)
            .where(Category.color.isnot(None))
            .group_by(Category.color)
            .order_by(desc('count'))
            .limit(1)
        )
        most_used_color_row = most_used_color_result.first()
        most_used_color = most_used_color_row[0] if most_used_color_row else None
        
        logger.info(f"Category stats - total: {total_categories}, inactive: {inactive_categories}")
        
        return CategoryStats(
            total_categories=total_categories or 0,
            inactive_categories=inactive_categories or 0,
            most_used_color=most_used_color
        )
        
    except Exception as e:
        logger.error(f"Failed to get category statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve category statistics")


@router.get("/{category_id}", response_model=CategoryResponse, summary="Get category by ID")
async def get_category(
    category_id: int,
    session: AsyncSession = Depends(get_session)
):
    """
    Retrieve a specific category by ID.
    
    - **category_id**: The ID of the category to retrieve
    """
    logger.info(f"Getting category with ID: {category_id}")
    
    try:
        # Query category
        query = select(Category).where(Category.id == category_id)
        result = await session.execute(query)
        category = result.scalar_one_or_none()
        
        if not category:
            logger.warning(f"Category {category_id} not found")
            raise HTTPException(status_code=404, detail="Category not found")
        
        logger.info(f"Retrieved category: {category.name}")
        return category
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get category {category_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve category")


@router.post("/", response_model=CategoryResponse, status_code=201, summary="Create category")
async def create_category(
    category_data: CategoryCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new category.
    
    - **name**: Category name (required, max 100 chars)
    - **description**: Optional description (max 500 chars)
    - **color**: Optional color in hex format (#RRGGBB)
    - **icon**: Optional icon name (max 50 chars)
    """
    logger.info(f"Creating category: {category_data.name}")
    
    try:
        # Check if category name already exists
        existing_query = select(Category).where(
            Category.name == category_data.name,
            Category.is_active == True
        )
        existing_result = await session.execute(existing_query)
        existing_category = existing_result.scalar_one_or_none()
        
        if existing_category:
            logger.warning(f"Category name '{category_data.name}' already exists")
            raise HTTPException(
                status_code=400,
                detail=f"Category with name '{category_data.name}' already exists"
            )
        
        # Create new category
        category = Category(
            name=category_data.name,
            description=category_data.description,
            color=category_data.color
        )
        
        session.add(category)
        await session.commit()
        await session.refresh(category)
        
        logger.info(f"Created category: {category.name} (ID: {category.id})")
        return category
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create category: {e}")
        await session.rollback()
        raise HTTPException(status_code=500, detail="Failed to create category")


@router.put("/{category_id}", response_model=CategoryResponse, summary="Update category")
async def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    session: AsyncSession = Depends(get_session)
):
    """
    Update an existing category.
    
    - **category_id**: The ID of the category to update
    - **name**: New category name (optional)
    - **description**: New description (optional)
    - **color**: New color in hex format (optional)
    - **icon**: New icon name (optional)
    """
    logger.info(f"Updating category {category_id}")
    
    try:
        # Get existing category
        query = select(Category).where(Category.id == category_id)
        result = await session.execute(query)
        category = result.scalar_one_or_none()
        
        if not category:
            logger.warning(f"Category {category_id} not found")
            raise HTTPException(status_code=404, detail="Category not found")
        
        if not category.is_active:
            logger.warning(f"Cannot update inactive category {category_id}")
            raise HTTPException(status_code=400, detail="Cannot update inactive category")
        
        # Check for name conflicts (if name is being changed)
        if category_data.name and category_data.name != category.name:
            existing_query = select(Category).where(
                Category.name == category_data.name,
                Category.is_active == True,
                Category.id != category_id
            )
            existing_result = await session.execute(existing_query)
            existing_category = existing_result.scalar_one_or_none()
            
            if existing_category:
                logger.warning(f"Category name '{category_data.name}' already exists")
                raise HTTPException(
                    status_code=400,
                    detail=f"Category with name '{category_data.name}' already exists"
                )
        
        # Update fields
        update_data = category_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(category, field, value)
        
        await session.commit()
        await session.refresh(category)
        
        logger.info(f"Updated category: {category.name} (ID: {category.id})")
        return category
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update category {category_id}: {e}")
        await session.rollback()
        raise HTTPException(status_code=500, detail="Failed to update category")


@router.delete("/{category_id}", status_code=204, summary="Delete category")
async def delete_category(
    category_id: int,
    permanent: bool = Query(False, description="Permanently delete (cannot be undone)"),
    session: AsyncSession = Depends(get_session)
):
    """
    Delete a category (soft delete by default).
    
    - **category_id**: The ID of the category to delete
    - **permanent**: If true, permanently delete the category (cannot be undone)
    """
    logger.info(f"Deleting category {category_id} (permanent: {permanent})")
    
    try:
        # Get category
        query = select(Category).where(Category.id == category_id)
        result = await session.execute(query)
        category = result.scalar_one_or_none()
        
        if not category:
            logger.warning(f"Category {category_id} not found")
            raise HTTPException(status_code=404, detail="Category not found")
        
        if permanent:
            # Permanent deletion
            await session.delete(category)
            logger.info(f"Permanently deleted category: {category.name} (ID: {category.id})")
        else:
            # Soft deletion
            if not category.is_active:
                logger.warning(f"Category {category_id} is already inactive")
                raise HTTPException(status_code=400, detail="Category is already inactive")
            
            category.soft_delete()
            logger.info(f"Soft deleted category: {category.name} (ID: {category.id})")
        
        await session.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete category {category_id}: {e}")
        await session.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete category")


@router.post("/{category_id}/restore", response_model=CategoryResponse, summary="Restore inactive category")
async def restore_category(
    category_id: int,
    session: AsyncSession = Depends(get_session)
):
    """
    Restore an inactive category.
    
    - **category_id**: The ID of the category to restore
    """
    logger.info(f"Restoring category {category_id}")
    
    try:
        # Get category
        query = select(Category).where(Category.id == category_id)
        result = await session.execute(query)
        category = result.scalar_one_or_none()
        
        if not category:
            logger.warning(f"Category {category_id} not found")
            raise HTTPException(status_code=404, detail="Category not found")
        
        if category.is_active:
            logger.warning(f"Category {category_id} is not inactive")
            raise HTTPException(status_code=400, detail="Category is not inactive")
        
        # Check for name conflicts
        existing_query = select(Category).where(
            Category.name == category.name,
            Category.is_active == True
        )
        existing_result = await session.execute(existing_query)
        existing_category = existing_result.scalar_one_or_none()
        
        if existing_category:
            logger.warning(f"Cannot restore: Category name '{category.name}' already exists")
            raise HTTPException(
                status_code=400,
                detail=f"Cannot restore: Category with name '{category.name}' already exists"
            )
        
        # Restore category
        category.restore()
        await session.commit()
        await session.refresh(category)
        
        logger.info(f"Restored category: {category.name} (ID: {category.id})")
        return category
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restore category {category_id}: {e}")
        await session.rollback()
        raise HTTPException(status_code=500, detail="Failed to restore category")