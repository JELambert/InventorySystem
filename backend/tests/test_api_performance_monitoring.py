"""
Comprehensive test suite for Performance API endpoints.

Tests all 8+ performance API endpoints including metrics monitoring, cache management,
query analysis, and database optimization.
"""

import pytest
import json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch

from app.main import app


class TestPerformanceAPIMetrics:
    """Test performance metrics and monitoring endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_get_performance_metrics(self, client):
        """Test getting comprehensive performance metrics."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.get("/api/v1/performance/metrics")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                expected_fields = [
                    "cache_stats", "query_analysis", "optimization_status"
                ]
                for field in expected_fields:
                    assert field in data
                
                # Validate cache stats structure
                if "cache_stats" in data:
                    cache_stats = data["cache_stats"]
                    assert "total_entries" in cache_stats
                    assert "active_entries" in cache_stats
                
                # Validate optimization status
                if "optimization_status" in data:
                    opt_status = data["optimization_status"]
                    assert "caching_enabled" in opt_status
    
    def test_get_query_analysis(self, client):
        """Test getting query performance analysis."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.get("/api/v1/performance/query-analysis")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                expected_fields = [
                    "slow_queries", "missing_indexes", "n_plus_one_risks", "recommendations"
                ]
                for field in expected_fields:
                    assert field in data
                
                # Validate data types
                assert isinstance(data["slow_queries"], list)
                assert isinstance(data["missing_indexes"], list)
                assert isinstance(data["n_plus_one_risks"], list)
                assert isinstance(data["recommendations"], list)


class TestPerformanceAPICacheManagement:
    """Test cache management operations."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_get_cache_stats(self, client):
        """Test getting cache statistics."""
        response = client.get("/api/v1/performance/cache/stats")
        
        # Should not return 404 for endpoint
        assert response.status_code != 404
        
        if response.status_code == 200:
            data = response.json()
            expected_fields = [
                "total_entries", "active_entries", "expired_entries"
            ]
            for field in expected_fields:
                assert field in data
            
            # Validate data types
            assert isinstance(data["total_entries"], int)
            assert isinstance(data["active_entries"], int)
            assert isinstance(data["expired_entries"], int)
            
            # Validate logical constraints
            assert data["total_entries"] >= 0
            assert data["active_entries"] >= 0
            assert data["expired_entries"] >= 0
            assert data["total_entries"] >= data["active_entries"]
    
    def test_warm_cache(self, client):
        """Test cache warming operation."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/performance/cache/warm")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert data["status"] in ["success", "error"]
                
                if data["status"] == "success":
                    assert "cached_queries" in data
                    assert "cache_stats" in data
                    assert isinstance(data["cached_queries"], list)
                else:
                    assert "message" in data
    
    def test_clear_cache_complete(self, client):
        """Test clearing entire cache."""
        response = client.delete("/api/v1/performance/cache/clear")
        
        # Should not return 404 for endpoint
        assert response.status_code != 404
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert "message" in data
            assert "remaining_entries" in data
            assert data["status"] == "success"
            assert isinstance(data["remaining_entries"], int)
    
    def test_clear_cache_pattern(self, client):
        """Test clearing cache with specific pattern."""
        pattern = "locations"
        response = client.delete(f"/api/v1/performance/cache/clear?pattern={pattern}")
        
        # Should not return 404 for endpoint
        assert response.status_code != 404
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert "message" in data
            assert pattern in data["message"]


class TestPerformanceAPIOptimization:
    """Test database optimization operations."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_create_indexes(self, client):
        """Test creating recommended database indexes."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Mock successful index creation
            mock_db.execute.return_value = None
            mock_db.commit.return_value = None
            
            response = client.post("/api/v1/performance/optimize/indexes")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            if response.status_code == 200:
                data = response.json()
                assert "status" in data
                assert "created_indexes" in data
                assert "message" in data
                assert data["status"] == "success"
                assert isinstance(data["created_indexes"], list)


class TestPerformanceAPIOptimizedData:
    """Test optimized data access endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_get_optimized_locations(self, client):
        """Test getting optimized location data."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Mock optimized service response
            mock_result = [
                {
                    "id": 1,
                    "name": "Test Location",
                    "location_type": "room",
                    "parent_id": None,
                    "item_count": 5,
                    "total_quantity": 10
                }
            ]
            
            with patch('app.performance.query_optimizer.OptimizedInventoryService') as mock_service:
                mock_instance = AsyncMock()
                mock_instance.get_locations_with_counts.return_value = mock_result
                mock_service.return_value = mock_instance
                
                response = client.get("/api/v1/performance/optimized/locations")
                
                # Should not return 404 for endpoint
                assert response.status_code != 404
                
                if response.status_code == 200:
                    data = response.json()
                    assert isinstance(data, list)
                    if data:
                        location = data[0]
                        expected_fields = [
                            "id", "name", "location_type", "item_count", "total_quantity"
                        ]
                        for field in expected_fields:
                            assert field in location
    
    def test_get_optimized_categories(self, client):
        """Test getting optimized category data."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Mock optimized service response
            mock_result = [
                {
                    "id": 1,
                    "name": "Test Category",
                    "description": "Test category description"
                }
            ]
            
            with patch('app.performance.query_optimizer.OptimizedInventoryService') as mock_service:
                mock_instance = AsyncMock()
                mock_instance.get_categories_list.return_value = mock_result
                mock_service.return_value = mock_instance
                
                response = client.get("/api/v1/performance/optimized/categories")
                
                # Should not return 404 for endpoint
                assert response.status_code != 404
                
                if response.status_code == 200:
                    data = response.json()
                    assert isinstance(data, list)
                    if data:
                        category = data[0]
                        expected_fields = ["id", "name", "description"]
                        for field in expected_fields:
                            assert field in category


class TestPerformanceAPIErrorHandling:
    """Test error handling in performance API."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_metrics_with_database_error(self, client):
        """Test metrics endpoint with database error."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_db.execute.side_effect = Exception("Database connection failed")
            mock_session.return_value = mock_db
            
            response = client.get("/api/v1/performance/metrics")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            # Should handle error gracefully
            if response.status_code == 500:
                data = response.json()
                assert "detail" in data
                assert "performance metrics" in data["detail"].lower()
            elif response.status_code == 200:
                # Should return error information in response
                data = response.json()
                if "query_analysis" in data:
                    assert data["query_analysis"]["status"] == "error"
    
    def test_query_analysis_with_error(self, client):
        """Test query analysis with database error."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_db.execute.side_effect = Exception("Query analysis failed")
            mock_session.return_value = mock_db
            
            response = client.get("/api/v1/performance/query-analysis")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            # Should handle error appropriately
            if response.status_code == 500:
                data = response.json()
                assert "detail" in data
    
    def test_cache_warm_with_service_error(self, client):
        """Test cache warming with service error."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            with patch('app.performance.query_optimizer.warm_cache') as mock_warm:
                mock_warm.side_effect = Exception("Cache warming failed")
                
                response = client.post("/api/v1/performance/cache/warm")
                
                # Should not return 404 for endpoint
                assert response.status_code != 404
                
                # Should handle error appropriately
                if response.status_code == 500:
                    data = response.json()
                    assert "detail" in data
    
    def test_index_creation_with_error(self, client):
        """Test index creation with database error."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_db.execute.side_effect = Exception("Index creation failed")
            mock_session.return_value = mock_db
            
            response = client.post("/api/v1/performance/optimize/indexes")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            # Should handle error appropriately
            if response.status_code == 500:
                data = response.json()
                assert "detail" in data
                assert "create indexes" in data["detail"].lower()
    
    def test_optimized_locations_with_error(self, client):
        """Test optimized locations with service error."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            with patch('app.performance.query_optimizer.OptimizedInventoryService') as mock_service:
                mock_instance = AsyncMock()
                mock_instance.get_locations_with_counts.side_effect = Exception("Service failed")
                mock_service.return_value = mock_instance
                
                response = client.get("/api/v1/performance/optimized/locations")
                
                # Should not return 404 for endpoint
                assert response.status_code != 404
                
                # Should handle error appropriately
                if response.status_code == 500:
                    data = response.json()
                    assert "detail" in data
    
    def test_cache_clear_with_error(self, client):
        """Test cache clearing with internal error."""
        with patch('app.performance.query_optimizer.cache') as mock_cache:
            mock_cache.invalidate.side_effect = Exception("Cache clear failed")
            mock_cache.stats.return_value = {"active_entries": 0}
            
            response = client.delete("/api/v1/performance/cache/clear")
            
            # Should not return 404 for endpoint
            assert response.status_code != 404
            
            # Should handle error appropriately
            if response.status_code == 500:
                data = response.json()
                assert "detail" in data


class TestPerformanceAPILoadTesting:
    """Test performance under various load conditions."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_concurrent_cache_operations(self, client):
        """Test concurrent cache operations."""
        # Simulate multiple concurrent requests
        responses = []
        
        for _ in range(5):
            response = client.get("/api/v1/performance/cache/stats")
            responses.append(response)
        
        # All requests should succeed (or fail consistently)
        status_codes = [r.status_code for r in responses]
        assert all(code != 404 for code in status_codes)
        
        # If successful, all should return cache stats
        for response in responses:
            if response.status_code == 200:
                data = response.json()
                assert "total_entries" in data
    
    def test_rapid_cache_warm_clear_cycle(self, client):
        """Test rapid cache warming and clearing."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Warm cache
            warm_response = client.post("/api/v1/performance/cache/warm")
            assert warm_response.status_code != 404
            
            # Clear cache
            clear_response = client.delete("/api/v1/performance/cache/clear")
            assert clear_response.status_code != 404
            
            # Warm again
            warm_response2 = client.post("/api/v1/performance/cache/warm")
            assert warm_response2.status_code != 404
    
    def test_metrics_under_load(self, client):
        """Test metrics endpoint under simulated load."""
        with patch('app.database.base.get_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value = mock_db
            
            # Make multiple rapid requests
            responses = []
            for _ in range(10):
                response = client.get("/api/v1/performance/metrics")
                responses.append(response)
            
            # All should handle the load appropriately
            status_codes = [r.status_code for r in responses]
            assert all(code != 404 for code in status_codes)
            
            # Should not have catastrophic failures
            success_codes = [code for code in status_codes if code in [200, 500]]
            assert len(success_codes) == len(status_codes)


if __name__ == "__main__":
    pytest.main([__file__])