"""
Performance monitoring and optimization API endpoints.

Provides endpoints for query analysis, cache management, and performance metrics.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import get_session
from app.performance import (
    QueryOptimizer,
    OptimizedInventoryService,
    cache,
    warm_cache,
    get_performance_metrics
)

router = APIRouter()


@router.get("/metrics", response_model=Dict[str, Any])
async def get_performance_metrics_endpoint(
    db: AsyncSession = Depends(get_session)
):
    """Get current performance metrics and analysis."""
    try:
        metrics = await get_performance_metrics(db)
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance metrics: {str(e)}"
        )


@router.get("/cache/stats", response_model=Dict[str, Any])
async def get_cache_stats():
    """Get cache statistics."""
    return cache.stats()


@router.post("/cache/warm", response_model=Dict[str, Any])
async def warm_cache_endpoint(
    db: AsyncSession = Depends(get_session)
):
    """Warm up cache with frequently accessed data."""
    try:
        result = await warm_cache(db)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to warm cache: {str(e)}"
        )


@router.delete("/cache/clear")
async def clear_cache(pattern: str = None):
    """Clear cache entries. Optionally specify pattern to clear specific entries."""
    try:
        cache.invalidate(pattern)
        return {
            "status": "success",
            "message": f"Cache cleared{'for pattern: ' + pattern if pattern else ' completely'}",
            "remaining_entries": cache.stats()["active_entries"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )


@router.get("/query-analysis", response_model=Dict[str, Any])
async def analyze_queries(
    db: AsyncSession = Depends(get_session)
):
    """Analyze query performance and get optimization recommendations."""
    try:
        optimizer = QueryOptimizer(db)
        analysis = await optimizer.analyze_query_performance()
        return analysis
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze queries: {str(e)}"
        )


@router.post("/optimize/indexes", response_model=Dict[str, Any])
async def create_indexes(
    db: AsyncSession = Depends(get_session)
):
    """Create recommended database indexes for performance optimization."""
    try:
        optimizer = QueryOptimizer(db)
        created_indexes = await optimizer.create_recommended_indexes()
        return {
            "status": "success",
            "created_indexes": created_indexes,
            "message": f"Successfully created {len(created_indexes)} database indexes"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create indexes: {str(e)}"
        )


@router.get("/optimized/locations", response_model=List[Dict[str, Any]])
async def get_optimized_locations(
    db: AsyncSession = Depends(get_session)
):
    """Get locations with counts using optimized cached query."""
    try:
        service = OptimizedInventoryService(db)
        locations = await service.get_locations_with_counts()
        return locations
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get optimized locations: {str(e)}"
        )


@router.get("/optimized/categories", response_model=List[Dict[str, Any]])
async def get_optimized_categories(
    db: AsyncSession = Depends(get_session)
):
    """Get categories using optimized cached query."""
    try:
        service = OptimizedInventoryService(db)
        categories = await service.get_categories_list()
        return categories
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get optimized categories: {str(e)}"
        )