"""
Weaviate service for semantic search and vector embeddings.

This service manages the connection to Weaviate vector database and provides
semantic search capabilities for inventory items using Weaviate v4 client.
"""

import logging
import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

import weaviate
from weaviate.exceptions import WeaviateConnectionError
import openai
from openai import AsyncOpenAI

from app.models.item import Item
from app.models.location import Location
from app.models.category import Category

logger = logging.getLogger(__name__)


class WeaviateConfig:
    """Configuration for Weaviate connection."""
    
    def __init__(self):
        self.host = os.getenv("WEAVIATE_HOST", "192.168.68.97")
        self.port = os.getenv("WEAVIATE_PORT", "8080")
        self.url = f"http://{self.host}:{self.port}"
        self.timeout = int(os.getenv("WEAVIATE_TIMEOUT", "30"))
        
        # OpenAI embedding configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY not set - embeddings will not work")
        
        self.embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self.embedding_dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
        
        # Search configuration
        self.default_limit = int(os.getenv("WEAVIATE_DEFAULT_LIMIT", "50"))
        self.default_certainty = float(os.getenv("WEAVIATE_DEFAULT_CERTAINTY", "0.7"))


class WeaviateSearchResult:
    """Result object for Weaviate searches."""
    
    def __init__(self, postgres_id: int, score: float, item_data: Dict[str, Any]):
        self.postgres_id = postgres_id
        self.score = score
        self.item_data = item_data
        
    def __repr__(self):
        return f"WeaviateSearchResult(id={self.postgres_id}, score={self.score:.3f})"


class WeaviateService:
    """Service for managing Weaviate vector database operations."""
    
    def __init__(self, config: Optional[WeaviateConfig] = None):
        self.config = config or WeaviateConfig()
        self._client: Optional[weaviate.WeaviateClient] = None
        self._openai_client: Optional[AsyncOpenAI] = None
        self._executor = ThreadPoolExecutor(max_workers=4)
        
        logger.info(f"Initializing Weaviate service with URL: {self.config.url}")
        logger.info(f"Using OpenAI embedding model: {self.config.embedding_model}")
    
    async def initialize(self) -> bool:
        """Initialize Weaviate connection and OpenAI client."""
        try:
            # Initialize Weaviate client
            await self._connect()
            
            # Initialize OpenAI client
            self._initialize_openai_client()
            
            # Ensure schema exists
            await self._ensure_schema()
            
            logger.info("Weaviate service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate service: {e}")
            return False
    
    async def _connect(self) -> None:
        """Establish connection to Weaviate."""
        def _create_client():
            # Weaviate v4 requires both HTTP and gRPC configuration
            grpc_port = int(self.config.port) + 1 if self.config.port != "8080" else 50051
            
            return weaviate.connect_to_custom(
                http_host=self.config.host,
                http_port=self.config.port,
                http_secure=False,
                grpc_host=self.config.host,
                grpc_port=grpc_port,
                grpc_secure=False
            )
        
        loop = asyncio.get_event_loop()
        self._client = await loop.run_in_executor(self._executor, _create_client)
        
        # Test connection
        await self.health_check()
    
    def _initialize_openai_client(self) -> None:
        """Initialize OpenAI client for embeddings."""
        if not self.config.openai_api_key:
            raise ValueError("OpenAI API key is required for embeddings")
        
        self._openai_client = AsyncOpenAI(api_key=self.config.openai_api_key)
        logger.info(f"Initialized OpenAI client with model: {self.config.embedding_model}")
    
    async def _create_embedding(self, text: str) -> List[float]:
        """Create embedding using OpenAI API."""
        if not self._openai_client:
            raise ValueError("OpenAI client not initialized")
        
        try:
            response = await self._openai_client.embeddings.create(
                model=self.config.embedding_model,
                input=text.strip(),
                dimensions=self.config.embedding_dimensions
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to create OpenAI embedding: {e}")
            raise
    
    async def health_check(self) -> bool:
        """Check if Weaviate is healthy and accessible."""
        try:
            def _check_health():
                if not self._client:
                    return False
                return self._client.is_ready()
            
            loop = asyncio.get_event_loop()
            is_ready = await loop.run_in_executor(self._executor, _check_health)
            
            if is_ready:
                logger.debug("Weaviate health check passed")
                return True
            else:
                logger.warning("Weaviate is not ready")
                return False
                
        except Exception as e:
            logger.error(f"Weaviate health check failed: {e}")
            return False
    
    async def _ensure_schema(self) -> None:
        """Ensure the Item schema exists in Weaviate."""
        def _create_schema():
            if not self._client:
                raise WeaviateConnectionError("Client not initialized")
            
            # Check if collection already exists
            if self._client.collections.exists("Item"):
                logger.info("Item collection already exists in Weaviate")
                return
            
            # Create Item collection without vectorizer (we handle embeddings manually)
            # Using OpenAI text-embedding-3-small dimensions (1536)
            self._client.collections.create(
                name="Item",
                description="Inventory items with semantic search capabilities using OpenAI embeddings",
                vectorizer_config=weaviate.classes.config.Configure.Vectorizer.none(),
                vector_index_config=weaviate.classes.config.Configure.VectorIndex.hnsw(
                    distance_metric=weaviate.classes.config.VectorDistances.COSINE
                ),
                properties=[
                    weaviate.classes.config.Property(
                        name="postgres_id",
                        data_type=weaviate.classes.config.DataType.INT,
                        description="PostgreSQL item ID for reference"
                    ),
                    weaviate.classes.config.Property(
                        name="name",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Item name"
                    ),
                    weaviate.classes.config.Property(
                        name="description", 
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Item description"
                    ),
                    weaviate.classes.config.Property(
                        name="combined_text",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Combined searchable text for vectorization"
                    ),
                    weaviate.classes.config.Property(
                        name="item_type",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Item type/category"
                    ),
                    weaviate.classes.config.Property(
                        name="category_name",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Category name"
                    ),
                    weaviate.classes.config.Property(
                        name="location_names",
                        data_type=weaviate.classes.config.DataType.TEXT_ARRAY,
                        description="Array of location names where item is stored"
                    ),
                    weaviate.classes.config.Property(
                        name="tags",
                        data_type=weaviate.classes.config.DataType.TEXT_ARRAY,
                        description="Item tags for enhanced search"
                    ),
                    weaviate.classes.config.Property(
                        name="brand",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Item brand"
                    ),
                    weaviate.classes.config.Property(
                        name="model",
                        data_type=weaviate.classes.config.DataType.TEXT,
                        description="Item model"
                    ),
                    weaviate.classes.config.Property(
                        name="created_at",
                        data_type=weaviate.classes.config.DataType.DATE,
                        description="Creation timestamp"
                    ),
                    weaviate.classes.config.Property(
                        name="updated_at",
                        data_type=weaviate.classes.config.DataType.DATE,
                        description="Last update timestamp"
                    )
                ]
            )
            
            logger.info("Created Item collection in Weaviate")
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, _create_schema)
    
    def _build_combined_text(self, item: Item, category_name: str = "", location_names: List[str] = None) -> str:
        """Build combined text for vectorization."""
        parts = []
        
        # Core item information
        if item.name:
            parts.append(item.name)
        if item.description:
            parts.append(item.description)
        if item.brand:
            parts.append(f"Brand: {item.brand}")
        if item.model:
            parts.append(f"Model: {item.model}")
        
        # Type and category
        if item.item_type:
            parts.append(f"Type: {item.item_type.value}")
        if category_name:
            parts.append(f"Category: {category_name}")
        
        # Locations
        if location_names:
            parts.append(f"Locations: {', '.join(location_names)}")
        
        # Tags and notes
        if item.tags:
            parts.append(f"Tags: {item.tags}")
        if item.notes:
            parts.append(f"Notes: {item.notes}")
        
        return " | ".join(parts)
    
    async def create_item_embedding(
        self, 
        item: Item, 
        category_name: str = "", 
        location_names: List[str] = None
    ) -> bool:
        """Create or update an item embedding in Weaviate."""
        try:
            if not await self.health_check():
                logger.warning("Weaviate not available, skipping embedding creation")
                return False
            
            # Build combined text for embedding
            combined_text = self._build_combined_text(item, category_name, location_names or [])
            
            # Prepare item data
            item_data = {
                "postgres_id": item.id,
                "name": item.name or "",
                "description": item.description or "",
                "combined_text": combined_text,
                "item_type": item.item_type.value if item.item_type else "",
                "category_name": category_name,
                "location_names": location_names or [],
                "tags": item.tags.split(",") if item.tags else [],
                "brand": item.brand or "",
                "model": item.model or "",
                "created_at": item.created_at or datetime.now(),
                "updated_at": item.updated_at or datetime.now()
            }
            
            # Generate embedding using OpenAI API
            embedding = await self._create_embedding(combined_text)
            
            def _insert_embedding():
                if not self._client:
                    raise WeaviateConnectionError("Client not initialized")
                
                collection = self._client.collections.get("Item")
                
                # Create new embedding (simpler approach - no deduplication for now)
                collection.data.insert(properties=item_data, vector=embedding)
                logger.debug(f"Created Weaviate embedding for item {item.id}")
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self._executor, _insert_embedding)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create embedding for item {item.id}: {e}")
            return False
    
    async def semantic_search(
        self, 
        query: str, 
        limit: int = None,
        certainty: float = None
    ) -> List[WeaviateSearchResult]:
        """Perform semantic search for items."""
        try:
            if not await self.health_check():
                logger.warning("Weaviate not available for semantic search")
                return []
            
            limit = limit or self.config.default_limit
            certainty = certainty or self.config.default_certainty
            
            # Generate query embedding using OpenAI API
            query_embedding = await self._create_embedding(query)
            
            def _search():
                if not self._client:
                    raise WeaviateConnectionError("Client not initialized")
                
                collection = self._client.collections.get("Item")
                
                response = collection.query.near_vector(
                    near_vector=query_embedding,
                    limit=limit,
                    return_metadata=weaviate.classes.query.MetadataQuery(certainty=True),
                    return_properties=[
                        "postgres_id", "name", "description", "item_type",
                        "category_name", "location_names", "brand", "model"
                    ]
                )
                
                search_results = []
                for obj in response.objects:
                    if obj.metadata.certainty >= certainty:
                        search_results.append(WeaviateSearchResult(
                            postgres_id=obj.properties["postgres_id"],
                            score=obj.metadata.certainty,
                            item_data=obj.properties
                        ))
                
                return search_results
            
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(self._executor, _search)
            
            logger.info(f"Semantic search for '{query}' returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed for query '{query}': {e}")
            return []
    
    async def get_similar_items(
        self, 
        item_id: int, 
        limit: int = 5
    ) -> List[WeaviateSearchResult]:
        """Find items similar to the given item."""
        try:
            if not await self.health_check():
                return []
            
            def _find_similar():
                if not self._client:
                    raise WeaviateConnectionError("Client not initialized")
                
                collection = self._client.collections.get("Item")
                
                # First get the target item
                target_objects = collection.query.fetch_objects(
                    where=weaviate.classes.query.Filter.by_property("postgres_id").equal(item_id),
                    limit=1,
                    include_vector=True
                )
                
                if not target_objects.objects:
                    return []
                
                target_vector = target_objects.objects[0].vector
                
                # Find similar items using the vector
                response = collection.query.near_vector(
                    near_vector=target_vector,
                    limit=limit + 1,  # +1 to exclude the original item
                    return_metadata=weaviate.classes.query.MetadataQuery(certainty=True),
                    return_properties=[
                        "postgres_id", "name", "description", "item_type",
                        "category_name", "location_names", "brand", "model"
                    ],
                    where=weaviate.classes.query.Filter.by_property("postgres_id").not_equal(item_id)
                )
                
                return [
                    WeaviateSearchResult(
                        postgres_id=obj.properties["postgres_id"],
                        score=obj.metadata.certainty,
                        item_data=obj.properties
                    )
                    for obj in response.objects
                ]
            
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(self._executor, _find_similar)
            
            logger.info(f"Found {len(results)} similar items for item {item_id}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to find similar items for {item_id}: {e}")
            return []
    
    async def delete_item_embedding(self, item_id: int) -> bool:
        """Delete an item's embedding from Weaviate."""
        try:
            if not await self.health_check():
                return False
            
            def _delete():
                if not self._client:
                    raise WeaviateConnectionError("Client not initialized")
                
                collection = self._client.collections.get("Item")
                
                # Find and delete the item
                objects = collection.query.fetch_objects(
                    where=weaviate.classes.query.Filter.by_property("postgres_id").equal(item_id),
                    limit=1
                )
                
                if objects.objects:
                    collection.data.delete_by_id(objects.objects[0].uuid)
                    logger.debug(f"Deleted Weaviate embedding for item {item_id}")
                    return True
                
                return False
            
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self._executor, _delete)
            
        except Exception as e:
            logger.error(f"Failed to delete embedding for item {item_id}: {e}")
            return False
    
    async def batch_create_embeddings(
        self, 
        items_data: List[Tuple[Item, str, List[str]]]
    ) -> Dict[str, int]:
        """Batch create embeddings for multiple items."""
        stats = {"success": 0, "failed": 0, "skipped": 0}
        
        if not await self.health_check():
            logger.warning("Weaviate not available for batch embedding creation")
            stats["skipped"] = len(items_data)
            return stats
        
        logger.info(f"Starting batch embedding creation for {len(items_data)} items")
        
        for item, category_name, location_names in items_data:
            try:
                success = await self.create_item_embedding(item, category_name, location_names)
                if success:
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
            except Exception as e:
                logger.error(f"Failed to create embedding for item {item.id}: {e}")
                stats["failed"] += 1
        
        logger.info(f"Batch embedding completed: {stats}")
        return stats
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Weaviate statistics."""
        try:
            if not await self.health_check():
                return {"status": "unavailable"}
            
            def _get_stats():
                if not self._client:
                    return {"status": "not_initialized"}
                
                # Get item count
                collection = self._client.collections.get("Item")
                count_result = collection.aggregate.over_all(total_count=True)
                item_count = count_result.total_count or 0
                
                return {
                    "status": "healthy",
                    "item_count": item_count,
                    "embedding_model": self.config.embedding_model,
                    "embedding_dimensions": self.config.embedding_dimensions,
                    "weaviate_url": self.config.url,
                    "embedding_provider": "openai"
                }
            
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self._executor, _get_stats)
            
        except Exception as e:
            logger.error(f"Failed to get Weaviate stats: {e}")
            return {"status": "error", "error": str(e)}
    
    async def close(self) -> None:
        """Close Weaviate connection and cleanup resources."""
        try:
            if self._client:
                def _close_client():
                    self._client.close()
                
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(self._executor, _close_client)
            
            # Close OpenAI client if it exists
            if self._openai_client:
                await self._openai_client.close()
            
            self._executor.shutdown(wait=True)
            logger.info("Weaviate service closed")
        except Exception as e:
            logger.error(f"Error closing Weaviate service: {e}")


# Global instance
_weaviate_service: Optional[WeaviateService] = None


async def get_weaviate_service() -> WeaviateService:
    """Get or create the global Weaviate service instance."""
    global _weaviate_service
    
    if _weaviate_service is None:
        _weaviate_service = WeaviateService()
        await _weaviate_service.initialize()
    
    return _weaviate_service


async def close_weaviate_service() -> None:
    """Close the global Weaviate service."""
    global _weaviate_service
    
    if _weaviate_service:
        await _weaviate_service.close()
        _weaviate_service = None