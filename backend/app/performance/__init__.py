"""
Performance optimization module for the Home Inventory System.

Provides query optimization, caching, and performance monitoring utilities.
"""

from .query_optimizer import (
    PerformanceCache,
    QueryOptimizer,
    OptimizedInventoryService,
    cache,
    cached_query,
    invalidate_cache_on_changes,
    warm_cache,
    get_performance_metrics
)

__all__ = [
    "PerformanceCache",
    "QueryOptimizer", 
    "OptimizedInventoryService",
    "cache",
    "cached_query",
    "invalidate_cache_on_changes", 
    "warm_cache",
    "get_performance_metrics"
]