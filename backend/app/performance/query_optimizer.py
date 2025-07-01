"""
Query Performance Optimization Module for the Home Inventory System.

Provides query analysis, caching strategies, and performance optimizations
for high-frequency database operations.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, Index, select, func
from sqlalchemy.orm import selectinload, joinedload

from app.models.inventory import Inventory
from app.models.item import Item
from app.models.location import Location
from app.models.category import Category

logger = logging.getLogger(__name__)


class PerformanceCache:
    """Simple in-memory cache for frequent lookups."""
    
    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self._cache:
            value, expires_at = self._cache[key]
            if datetime.now() < expires_at:
                return value
            else:
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value with TTL."""
        ttl = ttl or self._default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl)
        self._cache[key] = (value, expires_at)
    
    def invalidate(self, pattern: str = None) -> None:
        """Invalidate cache entries matching pattern."""
        if pattern is None:
            self._cache.clear()
        else:
            keys_to_remove = [k for k in self._cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self._cache[key]
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = datetime.now()
        active_entries = sum(1 for _, expires_at in self._cache.values() if expires_at > now)
        return {
            "total_entries": len(self._cache),
            "active_entries": active_entries,
            "expired_entries": len(self._cache) - active_entries
        }


# Global cache instance
cache = PerformanceCache()


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments."""
    key_data = {
        "args": args,
        "kwargs": {k: v for k, v in kwargs.items() if k != "db"}  # Exclude db session
    }
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()


def cached_query(ttl: int = 300, invalidate_on: List[str] = None):
    """Decorator for caching query results."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_result = cache.get(key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Execute query and cache result
            result = await func(*args, **kwargs)
            cache.set(key, result, ttl)
            logger.debug(f"Cached result for {func.__name__}")
            return result
        
        return wrapper
    return decorator


class QueryOptimizer:
    """Database query optimization utilities."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def analyze_query_performance(self) -> Dict[str, Any]:
        """Analyze current query performance patterns."""
        analysis = {
            "slow_queries": [],
            "missing_indexes": [],
            "n_plus_one_risks": [],
            "recommendations": []
        }
        
        # Check for common N+1 query patterns
        analysis["n_plus_one_risks"] = [
            {
                "table": "inventory",
                "issue": "Loading inventory entries without preloading item/location",
                "fix": "Use selectinload(Inventory.item, Inventory.location)"
            },
            {
                "table": "items",
                "issue": "Loading items without category preloading",
                "fix": "Use selectinload(Item.category) for item queries"
            },
            {
                "table": "locations",
                "issue": "Loading location hierarchy without parent/children",
                "fix": "Use selectinload for location relationships"
            }
        ]
        
        # Recommend indexes for common queries
        analysis["missing_indexes"] = await self._check_missing_indexes()
        
        # Performance recommendations
        analysis["recommendations"] = [
            "Add composite index on inventory(item_id, location_id)",
            "Add index on inventory.updated_at for timeline queries",
            "Add index on items.item_type for category filtering",
            "Add index on locations.parent_id for hierarchy queries",
            "Implement connection pooling for high load",
            "Add query result caching for frequent lookups"
        ]
        
        return analysis
    
    async def _check_missing_indexes(self) -> List[Dict[str, str]]:
        """Check for commonly needed indexes."""
        # Note: This is simplified - in production you'd check actual index usage
        missing_indexes = [
            {
                "table": "inventory",
                "columns": ["item_id", "location_id"],
                "type": "composite",
                "reason": "Frequent lookups for item-location pairs"
            },
            {
                "table": "inventory", 
                "columns": ["updated_at"],
                "type": "single",
                "reason": "Sorting by update time in search queries"
            },
            {
                "table": "movement_history",
                "columns": ["item_id", "created_at"],
                "type": "composite", 
                "reason": "Movement history queries by item with time sorting"
            },
            {
                "table": "items",
                "columns": ["item_type"],
                "type": "single",
                "reason": "Filtering by item type"
            },
            {
                "table": "locations",
                "columns": ["parent_id"],
                "type": "single",
                "reason": "Location hierarchy traversal"
            }
        ]
        
        return missing_indexes
    
    async def create_recommended_indexes(self) -> List[str]:
        """Create recommended database indexes."""
        created_indexes = []
        
        try:
            # Composite index for inventory lookups
            await self.db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_inventory_item_location 
                ON inventory(item_id, location_id)
            """))
            created_indexes.append("idx_inventory_item_location")
            
            # Index for inventory update sorting
            await self.db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_inventory_updated_at 
                ON inventory(updated_at DESC)
            """))
            created_indexes.append("idx_inventory_updated_at")
            
            # Index for movement history queries
            await self.db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_movement_history_item_time 
                ON movement_history(item_id, created_at DESC)
            """))
            created_indexes.append("idx_movement_history_item_time")
            
            # Index for item type filtering
            await self.db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_items_type 
                ON items(item_type)
            """))
            created_indexes.append("idx_items_type")
            
            # Index for location hierarchy
            await self.db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_locations_parent 
                ON locations(parent_id)
            """))
            created_indexes.append("idx_locations_parent")
            
            await self.db.commit()
            logger.info(f"Created {len(created_indexes)} database indexes")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            await self.db.rollback()
            
        return created_indexes


class OptimizedInventoryService:
    """Performance-optimized inventory service methods."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    @cached_query(ttl=300, invalidate_on=["inventory_update"])
    async def get_locations_with_counts(self) -> List[Dict[str, Any]]:
        """Get locations with item counts - cached version."""
        result = await self.db.execute(
            select(
                Location.id,
                Location.name,
                Location.location_type,
                Location.parent_id,
                func.count(Inventory.id).label('item_count'),
                func.sum(Inventory.quantity).label('total_quantity')
            )
            .outerjoin(Inventory, Location.id == Inventory.location_id)
            .group_by(Location.id, Location.name, Location.location_type, Location.parent_id)
            .order_by(Location.name)
        )
        
        return [
            {
                "id": row.id,
                "name": row.name,
                "location_type": row.location_type,
                "parent_id": row.parent_id,
                "item_count": row.item_count or 0,
                "total_quantity": row.total_quantity or 0
            }
            for row in result.fetchall()
        ]
    
    @cached_query(ttl=600)  # Cache categories for 10 minutes
    async def get_categories_list(self) -> List[Dict[str, Any]]:
        """Get categories list - cached version."""
        result = await self.db.execute(
            select(Category.id, Category.name, Category.description)
            .order_by(Category.name)
        )
        
        return [
            {
                "id": row.id,
                "name": row.name,
                "description": row.description
            }
            for row in result.fetchall()
        ]
    
    async def get_inventory_with_preloading(
        self,
        limit: int = 100,
        offset: int = 0,
        item_id: Optional[int] = None,
        location_id: Optional[int] = None
    ) -> List[Inventory]:
        """Get inventory with optimized preloading to avoid N+1 queries."""
        query = (
            select(Inventory)
            .options(
                selectinload(Inventory.item).selectinload(Item.category),
                selectinload(Inventory.location)
            )
            .order_by(Inventory.updated_at.desc())
        )
        
        # Apply filters
        if item_id:
            query = query.where(Inventory.item_id == item_id)
        if location_id:
            query = query.where(Inventory.location_id == location_id)
        
        # Apply pagination
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_items_with_inventory_optimized(
        self,
        limit: int = 100,
        offset: int = 0,
        item_type: Optional[str] = None
    ) -> List[Item]:
        """Get items with inventory using optimized query."""
        query = (
            select(Item)
            .options(
                selectinload(Item.category),
                selectinload(Item.inventory_entries).selectinload(Inventory.location)
            )
            .order_by(Item.name)
        )
        
        # Apply filters
        if item_type:
            query = query.where(Item.item_type == item_type)
        
        # Apply pagination
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
            
        result = await self.db.execute(query)
        return result.scalars().all()


def invalidate_cache_on_changes(operation_type: str):
    """Decorator to invalidate cache on data changes."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # Invalidate relevant cache entries
            if operation_type in ["inventory_create", "inventory_update", "inventory_delete"]:
                cache.invalidate("get_locations_with_counts")
                cache.invalidate("get_inventory_with_preloading")
            
            if operation_type in ["item_create", "item_update"]:
                cache.invalidate("get_items_with_inventory_optimized")
            
            return result
        return wrapper
    return decorator


async def warm_cache(db: AsyncSession) -> Dict[str, Any]:
    """Warm up cache with frequently accessed data."""
    optimized_service = OptimizedInventoryService(db)
    
    try:
        # Pre-load frequently accessed data
        await optimized_service.get_locations_with_counts()
        await optimized_service.get_categories_list()
        await optimized_service.get_inventory_with_preloading(limit=50)
        
        return {
            "status": "success",
            "cached_queries": ["locations_with_counts", "categories_list", "recent_inventory"],
            "cache_stats": cache.stats()
        }
    except Exception as e:
        logger.error(f"Failed to warm cache: {e}")
        return {"status": "error", "message": str(e)}


async def get_performance_metrics(db: AsyncSession) -> Dict[str, Any]:
    """Get current performance metrics."""
    try:
        optimizer = QueryOptimizer(db)
        analysis = await optimizer.analyze_query_performance()
        
        return {
            "cache_stats": cache.stats(),
            "query_analysis": analysis,
            "optimization_status": {
                "caching_enabled": True,
                "indexes_recommended": len(analysis.get("missing_indexes", [])),
                "n_plus_one_risks": len(analysis.get("n_plus_one_risks", []))
            }
        }
    except Exception as e:
        # Return basic metrics even if full analysis fails
        return {
            "cache_stats": cache.stats(),
            "query_analysis": {
                "status": "error",
                "message": f"Analysis failed: {str(e)}",
                "missing_indexes": [],
                "n_plus_one_risks": []
            },
            "optimization_status": {
                "caching_enabled": True,
                "indexes_recommended": 0,
                "n_plus_one_risks": 0,
                "analysis_error": True
            }
        }