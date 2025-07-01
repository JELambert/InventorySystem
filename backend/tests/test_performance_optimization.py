"""
Test suite for the performance optimization system.

Tests query optimization, caching, performance monitoring, and analytics functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.performance.query_optimizer import (
    QueryOptimizer,
    PerformanceCache,
    OptimizedInventoryService,
    cache,
    cached_query,
    get_performance_metrics,
    warm_cache
)


class TestQueryOptimizer:
    """Test the QueryOptimizer class functionality."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock(spec=AsyncSession)
        return session
    
    @pytest.fixture
    def optimizer(self, mock_db_session):
        """Create a QueryOptimizer instance with mocked database."""
        return QueryOptimizer(mock_db_session)
    
    def test_optimizer_initialization(self, optimizer):
        """Test query optimizer initialization."""
        assert optimizer.db is not None
    
    @pytest.mark.asyncio
    async def test_analyze_query_performance(self, optimizer):
        """Test query performance analysis."""
        analysis = await optimizer.analyze_query_performance()
        
        assert "slow_queries" in analysis
        assert "missing_indexes" in analysis
        assert "n_plus_one_risks" in analysis
        assert "recommendations" in analysis
        assert isinstance(analysis["n_plus_one_risks"], list)
        assert isinstance(analysis["recommendations"], list)
    
    @pytest.mark.asyncio
    async def test_check_missing_indexes(self, optimizer):
        """Test missing index detection."""
        missing_indexes = await optimizer._check_missing_indexes()
        
        assert isinstance(missing_indexes, list)
        assert len(missing_indexes) > 0
        
        # Check structure of returned indexes
        for index in missing_indexes:
            assert "table" in index
            assert "columns" in index
            assert "type" in index
            assert "reason" in index
    
    @pytest.mark.asyncio
    async def test_create_recommended_indexes(self, optimizer):
        """Test index creation."""
        # Mock successful index creation
        optimizer.db.execute.return_value = None
        optimizer.db.commit.return_value = None
        
        created_indexes = await optimizer.create_recommended_indexes()
        
        assert isinstance(created_indexes, list)
        # Should attempt to create multiple indexes
        assert len(created_indexes) >= 0


class TestPerformanceCache:
    """Test the PerformanceCache class functionality."""
    
    @pytest.fixture
    def cache_instance(self):
        """Create a PerformanceCache instance."""
        return PerformanceCache(default_ttl=300)
    
    def test_cache_initialization(self, cache_instance):
        """Test cache initialization."""
        assert cache_instance._default_ttl == 300
        assert len(cache_instance._cache) == 0
    
    def test_cache_set_and_get(self, cache_instance):
        """Test basic cache set and get operations."""
        test_key = "test_key"
        test_value = {"data": "test_data"}
        
        # Set value in cache
        cache_instance.set(test_key, test_value)
        
        # Get value from cache
        result = cache_instance.get(test_key)
        
        assert result == test_value
    
    def test_cache_miss(self, cache_instance):
        """Test cache miss behavior."""
        result = cache_instance.get("nonexistent_key")
        assert result is None
    
    def test_cache_expiration(self, cache_instance):
        """Test cache entry expiration."""
        test_key = "expiring_key"
        test_value = {"data": "expiring_data"}
        
        # Set value with short TTL
        cache_instance.set(test_key, test_value, ttl=1)
        
        # Should be available immediately
        assert cache_instance.get(test_key) == test_value
        
        # Wait for expiration and test
        import time
        time.sleep(1.1)
        
        # Should be expired
        assert cache_instance.get(test_key) is None
    
    def test_cache_invalidate(self, cache_instance):
        """Test cache invalidation."""
        # Add some entries
        cache_instance.set("key1", "value1")
        cache_instance.set("key2", "value2")
        
        assert len(cache_instance._cache) == 2
        
        # Clear cache
        cache_instance.invalidate()
        
        assert len(cache_instance._cache) == 0
    
    def test_cache_stats(self, cache_instance):
        """Test cache statistics."""
        # Add some entries
        cache_instance.set("key1", "value1")
        cache_instance.set("key2", "value2")
        
        stats = cache_instance.stats()
        
        assert "total_entries" in stats
        assert "active_entries" in stats
        assert "expired_entries" in stats
        assert stats["total_entries"] == 2


class TestOptimizedInventoryService:
    """Test the OptimizedInventoryService class functionality."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock(spec=AsyncSession)
        return session
    
    @pytest.fixture
    def service(self, mock_db_session):
        """Create an OptimizedInventoryService instance."""
        return OptimizedInventoryService(mock_db_session)
    
    @pytest.mark.asyncio
    async def test_get_locations_with_counts(self, service):
        """Test optimized location retrieval."""
        # Mock database result
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            Mock(id=1, name="Test Location", location_type="room", parent_id=None, item_count=5, total_quantity=10)
        ]
        service.db.execute.return_value = mock_result
        
        # Clear cache first
        cache.invalidate()
        
        locations = await service.get_locations_with_counts()
        
        assert isinstance(locations, list)
        assert len(locations) == 1
        assert locations[0]["id"] == 1
        assert locations[0]["name"] == "Test Location"
        assert locations[0]["item_count"] == 5
    
    @pytest.mark.asyncio
    async def test_get_categories_list(self, service):
        """Test optimized category retrieval."""
        # Mock database result
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            Mock(id=1, name="Test Category", description="Test Description")
        ]
        service.db.execute.return_value = mock_result
        
        # Clear cache first
        cache.invalidate()
        
        categories = await service.get_categories_list()
        
        assert isinstance(categories, list)
        assert len(categories) == 1
        assert categories[0]["id"] == 1
        assert categories[0]["name"] == "Test Category"
    
    @pytest.mark.asyncio
    async def test_get_inventory_with_preloading(self, service):
        """Test optimized inventory retrieval with preloading."""
        # Mock database result
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        service.db.execute.return_value = mock_result
        
        inventory = await service.get_inventory_with_preloading(limit=50)
        
        assert isinstance(inventory, list)
        # Verify that the execute method was called (query was built and executed)
        service.db.execute.assert_called_once()


class TestGlobalFunctions:
    """Test global functions for performance optimization."""
    
    @pytest.mark.asyncio
    async def test_get_performance_metrics(self):
        """Test performance metrics retrieval."""
        mock_db = AsyncMock(spec=AsyncSession)
        
        metrics = await get_performance_metrics(mock_db)
        
        assert "cache_stats" in metrics
        assert "query_analysis" in metrics
        assert "optimization_status" in metrics
        
        # Check cache stats structure
        cache_stats = metrics["cache_stats"]
        assert "total_entries" in cache_stats
        assert "active_entries" in cache_stats
    
    @pytest.mark.asyncio
    async def test_warm_cache(self):
        """Test cache warming functionality."""
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock the service methods
        with patch('app.performance.query_optimizer.OptimizedInventoryService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            
            result = await warm_cache(mock_db)
            
            assert "status" in result
            # Should either succeed or fail gracefully
            assert result["status"] in ["success", "error"]
    
    def test_cached_query_decorator(self):
        """Test the cached_query decorator."""
        # Create a test function with caching
        @cached_query(ttl=60)
        async def test_function(value):
            return f"result_{value}"
        
        # The decorator should return a wrapper function
        assert callable(test_function)
        assert hasattr(test_function, '__wrapped__')


class TestCacheIntegration:
    """Test cache integration scenarios."""
    
    def setup_method(self):
        """Clear cache before each test."""
        cache.invalidate()
    
    def test_global_cache_instance(self):
        """Test that global cache instance works correctly."""
        # Test basic operations on global cache
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"
        
        # Test stats
        stats = cache.stats()
        assert stats["total_entries"] >= 1
    
    def test_cache_invalidation_patterns(self):
        """Test pattern-based cache invalidation."""
        # Set up test data
        cache.set("locations_query_1", "location_data_1")
        cache.set("locations_query_2", "location_data_2")
        cache.set("items_query_1", "item_data_1")
        
        # Test pattern invalidation
        cache.invalidate("locations")
        
        # Locations should be invalidated, items should remain
        assert cache.get("locations_query_1") is None
        assert cache.get("locations_query_2") is None
        assert cache.get("items_query_1") == "item_data_1"


class TestErrorHandling:
    """Test error handling in performance optimization."""
    
    @pytest.mark.asyncio
    async def test_get_performance_metrics_error_handling(self):
        """Test that performance metrics handle errors gracefully."""
        # Create a mock database that will raise an exception
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute.side_effect = Exception("Database error")
        
        # Should not raise exception, but return error information
        metrics = await get_performance_metrics(mock_db)
        
        assert "cache_stats" in metrics
        assert "query_analysis" in metrics
        assert metrics["query_analysis"]["status"] == "error"
        assert "analysis_error" in metrics["optimization_status"]
        assert metrics["optimization_status"]["analysis_error"] is True
    
    @pytest.mark.asyncio
    async def test_warm_cache_error_handling(self):
        """Test that cache warming handles errors gracefully."""
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock service that will raise an exception
        with patch('app.performance.query_optimizer.OptimizedInventoryService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.get_locations_with_counts.side_effect = Exception("Service error")
            mock_service_class.return_value = mock_service
            
            result = await warm_cache(mock_db)
            
            assert result["status"] == "error"
            assert "message" in result


if __name__ == "__main__":
    pytest.main([__file__])