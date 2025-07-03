"""
Tests for the Weaviate service.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import sys

# Mock weaviate module before importing service
sys.modules['weaviate'] = MagicMock()
sys.modules['weaviate.exceptions'] = MagicMock()
sys.modules['sentence_transformers'] = MagicMock()

from app.services.weaviate_service import (
    WeaviateService, WeaviateConfig, WeaviateSearchResult
)
from app.models.item import Item, ItemType
from app.models.location import Location, LocationType
from app.models.category import Category


@pytest.fixture
def weaviate_config():
    """Create a test Weaviate configuration."""
    config = WeaviateConfig()
    config.host = "test-host"
    config.port = "8080"
    config.url = "http://test-host:8080"
    config.timeout = 30
    config.embedding_model = "test-model"
    config.default_limit = 10
    config.default_certainty = 0.7
    return config


@pytest.fixture
def mock_weaviate_client():
    """Create a mock Weaviate client."""
    client = Mock()
    
    # Mock collections
    collections = Mock()
    item_collection = Mock()
    
    # Mock collection methods
    collections.exists.return_value = True
    collections.get.return_value = item_collection
    collections.create = Mock()
    
    client.collections = collections
    client.is_ready.return_value = True
    client.close = Mock()
    
    return client


@pytest.fixture
def mock_embedding_model():
    """Create a mock sentence transformer model."""
    model = Mock()
    model.encode.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
    return model


@pytest.fixture
def sample_item():
    """Create a sample item for testing."""
    return Item(
        id=1,
        name="Test Item",
        description="A test item description",
        item_type=ItemType.ELECTRONICS,
        brand="TestBrand",
        model="TestModel",
        tags="tag1,tag2,tag3",
        notes="Test notes",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


class TestWeaviateService:
    """Test cases for WeaviateService."""
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, weaviate_config, mock_weaviate_client, mock_embedding_model):
        """Test successful service initialization."""
        service = WeaviateService(weaviate_config)
        
        with patch('weaviate.connect_to_custom', return_value=mock_weaviate_client):
            with patch('sentence_transformers.SentenceTransformer', return_value=mock_embedding_model):
                result = await service.initialize()
                
                assert result is True
                assert service._client is not None
                assert service._embedding_model is not None
                mock_weaviate_client.collections.create.assert_not_called()  # Schema already exists
    
    @pytest.mark.asyncio
    async def test_initialize_creates_schema(self, weaviate_config, mock_weaviate_client, mock_embedding_model):
        """Test that initialization creates schema if missing."""
        service = WeaviateService(weaviate_config)
        
        # Simulate schema not existing
        mock_weaviate_client.collections.exists.return_value = False
        
        with patch('weaviate.connect_to_custom', return_value=mock_weaviate_client):
            with patch('sentence_transformers.SentenceTransformer', return_value=mock_embedding_model):
                result = await service.initialize()
                
                assert result is True
                mock_weaviate_client.collections.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_failure(self, weaviate_config):
        """Test initialization failure handling."""
        service = WeaviateService(weaviate_config)
        
        with patch('weaviate.connect_to_custom', side_effect=Exception("Connection failed")):
            result = await service.initialize()
            
            assert result is False
            assert service._client is None
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, weaviate_config, mock_weaviate_client):
        """Test successful health check."""
        service = WeaviateService(weaviate_config)
        service._client = mock_weaviate_client
        
        result = await service.health_check()
        
        assert result is True
        mock_weaviate_client.is_ready.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_no_client(self, weaviate_config):
        """Test health check when client is not initialized."""
        service = WeaviateService(weaviate_config)
        service._client = None
        
        result = await service.health_check()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_health_check_client_not_ready(self, weaviate_config, mock_weaviate_client):
        """Test health check when client is not ready."""
        service = WeaviateService(weaviate_config)
        service._client = mock_weaviate_client
        mock_weaviate_client.is_ready.return_value = False
        
        result = await service.health_check()
        
        assert result is False
    
    def test_build_combined_text(self, weaviate_config, sample_item):
        """Test building combined text for vectorization."""
        service = WeaviateService(weaviate_config)
        
        combined_text = service._build_combined_text(
            sample_item,
            category_name="Electronics",
            location_names=["Room 1", "Shelf A"]
        )
        
        assert "Test Item" in combined_text
        assert "A test item description" in combined_text
        assert "Brand: TestBrand" in combined_text
        assert "Model: TestModel" in combined_text
        assert "Type: ELECTRONICS" in combined_text
        assert "Category: Electronics" in combined_text
        assert "Locations: Room 1, Shelf A" in combined_text
        assert "Tags: tag1,tag2,tag3" in combined_text
        assert "Notes: Test notes" in combined_text
    
    @pytest.mark.asyncio
    async def test_create_item_embedding_success(
        self, weaviate_config, mock_weaviate_client, mock_embedding_model, sample_item
    ):
        """Test successful item embedding creation."""
        service = WeaviateService(weaviate_config)
        service._client = mock_weaviate_client
        service._embedding_model = mock_embedding_model
        
        # Mock collection methods
        collection = Mock()
        collection.data.insert = Mock()
        mock_weaviate_client.collections.get.return_value = collection
        
        # Mock health check
        with patch.object(service, 'health_check', return_value=True):
            result = await service.create_item_embedding(
                sample_item,
                category_name="Electronics",
                location_names=["Room 1"]
            )
            
            assert result is True
            mock_embedding_model.encode.assert_called_once()
            collection.data.insert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_item_embedding_health_check_fail(
        self, weaviate_config, sample_item
    ):
        """Test embedding creation when health check fails."""
        service = WeaviateService(weaviate_config)
        
        with patch.object(service, 'health_check', return_value=False):
            result = await service.create_item_embedding(sample_item)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_semantic_search_success(
        self, weaviate_config, mock_weaviate_client, mock_embedding_model
    ):
        """Test successful semantic search."""
        service = WeaviateService(weaviate_config)
        service._client = mock_weaviate_client
        service._embedding_model = mock_embedding_model
        
        # Mock search response
        mock_response = Mock()
        mock_obj = Mock()
        mock_obj.properties = {
            "postgres_id": 1,
            "name": "Test Item",
            "description": "Test description",
            "item_type": "ELECTRONICS",
            "category_name": "Electronics",
            "location_names": ["Room 1"],
            "brand": "TestBrand",
            "model": "TestModel"
        }
        mock_obj.metadata.certainty = 0.85
        mock_response.objects = [mock_obj]
        
        collection = Mock()
        collection.query.near_vector.return_value = mock_response
        mock_weaviate_client.collections.get.return_value = collection
        
        # Mock health check
        with patch.object(service, 'health_check', return_value=True):
            results = await service.semantic_search("test query", limit=5, certainty=0.7)
            
            assert len(results) == 1
            assert isinstance(results[0], WeaviateSearchResult)
            assert results[0].postgres_id == 1
            assert results[0].score == 0.85
            mock_embedding_model.encode.assert_called_once_with("test query")
    
    @pytest.mark.asyncio
    async def test_semantic_search_no_results(
        self, weaviate_config, mock_weaviate_client, mock_embedding_model
    ):
        """Test semantic search with no results."""
        service = WeaviateService(weaviate_config)
        service._client = mock_weaviate_client
        service._embedding_model = mock_embedding_model
        
        # Mock empty response
        mock_response = Mock()
        mock_response.objects = []
        
        collection = Mock()
        collection.query.near_vector.return_value = mock_response
        mock_weaviate_client.collections.get.return_value = collection
        
        with patch.object(service, 'health_check', return_value=True):
            results = await service.semantic_search("test query")
            
            assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_semantic_search_filters_by_certainty(
        self, weaviate_config, mock_weaviate_client, mock_embedding_model
    ):
        """Test that semantic search filters results by certainty score."""
        service = WeaviateService(weaviate_config)
        service._client = mock_weaviate_client
        service._embedding_model = mock_embedding_model
        
        # Mock response with mixed certainty scores
        mock_response = Mock()
        
        mock_obj1 = Mock()
        mock_obj1.properties = {"postgres_id": 1}
        mock_obj1.metadata.certainty = 0.85  # Above threshold
        
        mock_obj2 = Mock()
        mock_obj2.properties = {"postgres_id": 2}
        mock_obj2.metadata.certainty = 0.65  # Below threshold
        
        mock_response.objects = [mock_obj1, mock_obj2]
        
        collection = Mock()
        collection.query.near_vector.return_value = mock_response
        mock_weaviate_client.collections.get.return_value = collection
        
        with patch.object(service, 'health_check', return_value=True):
            results = await service.semantic_search("test query", certainty=0.7)
            
            assert len(results) == 1
            assert results[0].postgres_id == 1
    
    @pytest.mark.asyncio
    async def test_get_similar_items_success(
        self, weaviate_config, mock_weaviate_client, mock_embedding_model
    ):
        """Test successful similar items retrieval."""
        service = WeaviateService(weaviate_config)
        service._client = mock_weaviate_client
        service._embedding_model = mock_embedding_model
        
        # Mock target item fetch
        target_obj = Mock()
        target_obj.vector = [0.1, 0.2, 0.3]
        target_response = Mock()
        target_response.objects = [target_obj]
        
        # Mock similar items response
        similar_obj = Mock()
        similar_obj.properties = {
            "postgres_id": 2,
            "name": "Similar Item"
        }
        similar_obj.metadata.certainty = 0.9
        similar_response = Mock()
        similar_response.objects = [similar_obj]
        
        collection = Mock()
        collection.query.fetch_objects.return_value = target_response
        collection.query.near_vector.return_value = similar_response
        mock_weaviate_client.collections.get.return_value = collection
        
        with patch.object(service, 'health_check', return_value=True):
            results = await service.get_similar_items(1, limit=5)
            
            assert len(results) == 1
            assert results[0].postgres_id == 2
    
    @pytest.mark.asyncio
    async def test_delete_item_embedding_success(
        self, weaviate_config, mock_weaviate_client
    ):
        """Test successful item embedding deletion."""
        service = WeaviateService(weaviate_config)
        service._client = mock_weaviate_client
        
        # Mock finding and deleting item
        mock_obj = Mock()
        mock_obj.uuid = "test-uuid"
        mock_response = Mock()
        mock_response.objects = [mock_obj]
        
        collection = Mock()
        collection.query.fetch_objects.return_value = mock_response
        collection.data.delete_by_id = Mock()
        mock_weaviate_client.collections.get.return_value = collection
        
        with patch.object(service, 'health_check', return_value=True):
            result = await service.delete_item_embedding(1)
            
            assert result is True
            collection.data.delete_by_id.assert_called_once_with("test-uuid")
    
    @pytest.mark.asyncio
    async def test_batch_create_embeddings(
        self, weaviate_config, sample_item
    ):
        """Test batch embedding creation."""
        service = WeaviateService(weaviate_config)
        
        items_data = [
            (sample_item, "Electronics", ["Room 1"]),
            (sample_item, "Electronics", ["Room 2"])
        ]
        
        # Mock health check and create_item_embedding
        with patch.object(service, 'health_check', return_value=True):
            with patch.object(service, 'create_item_embedding', return_value=True):
                stats = await service.batch_create_embeddings(items_data)
                
                assert stats["success"] == 2
                assert stats["failed"] == 0
                assert stats["skipped"] == 0
    
    @pytest.mark.asyncio
    async def test_get_stats_success(
        self, weaviate_config, mock_weaviate_client, mock_embedding_model
    ):
        """Test successful stats retrieval."""
        service = WeaviateService(weaviate_config)
        service._client = mock_weaviate_client
        service._embedding_model = mock_embedding_model
        service.config = weaviate_config
        
        # Mock aggregate response
        aggregate_result = Mock()
        aggregate_result.total_count = 42
        
        collection = Mock()
        collection.aggregate.over_all.return_value = aggregate_result
        mock_weaviate_client.collections.get.return_value = collection
        
        with patch.object(service, 'health_check', return_value=True):
            stats = await service.get_stats()
            
            assert stats["status"] == "healthy"
            assert stats["item_count"] == 42
            assert stats["embedding_model"] == "test-model"
            assert stats["weaviate_url"] == "http://test-host:8080"
    
    @pytest.mark.asyncio
    async def test_close_service(self, weaviate_config, mock_weaviate_client):
        """Test service cleanup."""
        service = WeaviateService(weaviate_config)
        service._client = mock_weaviate_client
        
        await service.close()
        
        mock_weaviate_client.close.assert_called_once()