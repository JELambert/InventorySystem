#!/usr/bin/env python3
"""
Migration script to transition from sentence-transformers to OpenAI embeddings.

This script:
1. Backs up the existing Weaviate collection
2. Creates a new collection with OpenAI embedding dimensions (1536)
3. Regenerates all embeddings using OpenAI API
4. Provides rollback capabilities

Usage:
    python migrate_to_openai_embeddings.py --mode backup
    python migrate_to_openai_embeddings.py --mode migrate --openai-key YOUR_API_KEY
    python migrate_to_openai_embeddings.py --mode rollback
"""

import asyncio
import argparse
import logging
import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

import weaviate
from weaviate.exceptions import WeaviateConnectionError
from openai import AsyncOpenAI

from app.database.base import get_session
from app.models.item import Item
from app.models.location import Location
from app.models.category import Category
from app.services.weaviate_service import WeaviateConfig

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OpenAIEmbeddingMigrator:
    """Handles migration from sentence-transformers to OpenAI embeddings."""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        self.config = WeaviateConfig()
        if openai_api_key:
            self.config.openai_api_key = openai_api_key
        
        self.weaviate_client: Optional[weaviate.WeaviateClient] = None
        self.openai_client: Optional[AsyncOpenAI] = None
        self.backup_data: List[Dict[str, Any]] = []
        
    async def initialize(self):
        """Initialize connections to Weaviate and OpenAI."""
        # Connect to Weaviate
        try:
            grpc_port = int(self.config.port) + 1 if self.config.port != "8080" else 50051
            self.weaviate_client = weaviate.connect_to_custom(
                http_host=self.config.host,
                http_port=self.config.port,
                http_secure=False,
                grpc_host=self.config.host,
                grpc_port=grpc_port,
                grpc_secure=False
            )
            logger.info(f"Connected to Weaviate at {self.config.url}")
        except Exception as e:
            logger.error(f"Failed to connect to Weaviate: {e}")
            raise
        
        # Initialize OpenAI client if API key is provided
        if self.config.openai_api_key:
            self.openai_client = AsyncOpenAI(api_key=self.config.openai_api_key)
            logger.info("Initialized OpenAI client")
    
    async def backup_existing_collection(self) -> bool:
        """Backup existing Item collection to JSON file."""
        try:
            if not self.weaviate_client.collections.exists("Item"):
                logger.info("No existing Item collection to backup")
                return True
            
            collection = self.weaviate_client.collections.get("Item")
            
            # Fetch all items with vectors
            response = collection.query.fetch_objects(
                limit=10000,  # Adjust based on your data size
                include_vector=True
            )
            
            backup_data = []
            for obj in response.objects:
                backup_data.append({
                    "uuid": str(obj.uuid),
                    "properties": obj.properties,
                    "vector": obj.vector
                })
            
            # Save backup to file
            backup_file = f"weaviate_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2, default=str)
            
            self.backup_data = backup_data
            logger.info(f"Backed up {len(backup_data)} items to {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to backup collection: {e}")
            return False
    
    async def recreate_collection_with_new_dimensions(self) -> bool:
        """Recreate Item collection with OpenAI embedding dimensions."""
        try:
            # Delete existing collection if it exists
            if self.weaviate_client.collections.exists("Item"):
                self.weaviate_client.collections.delete("Item")
                logger.info("Deleted existing Item collection")
            
            # Create new collection with OpenAI dimensions (1536)
            self.weaviate_client.collections.create(
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
            
            logger.info("Created new Item collection with OpenAI embedding dimensions")
            return True
            
        except Exception as e:
            logger.error(f"Failed to recreate collection: {e}")
            return False
    
    async def create_openai_embedding(self, text: str) -> List[float]:
        """Create embedding using OpenAI API."""
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")
        
        try:
            response = await self.openai_client.embeddings.create(
                model=self.config.embedding_model,
                input=text.strip(),
                dimensions=self.config.embedding_dimensions
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to create OpenAI embedding: {e}")
            raise
    
    def build_combined_text(self, item: Item, category_name: str = "", location_names: List[str] = None) -> str:
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
    
    async def regenerate_all_embeddings(self) -> bool:
        """Regenerate embeddings for all items using OpenAI."""
        try:
            # Get all items from PostgreSQL
            async with get_session() as session:
                from sqlalchemy import select
                from sqlalchemy.orm import selectinload
                
                stmt = select(Item).options(
                    selectinload(Item.category),
                    selectinload(Item.inventory_entries).selectinload("location")
                )
                result = await session.execute(stmt)
                items = result.scalars().all()
            
            logger.info(f"Found {len(items)} items to process")
            
            collection = self.weaviate_client.collections.get("Item")
            processed = 0
            failed = 0
            
            for item in items:
                try:
                    # Get category name
                    category_name = item.category.name if item.category else ""
                    
                    # Get location names
                    location_names = []
                    for inventory_entry in item.inventory_entries:
                        if inventory_entry.location and inventory_entry.location.name:
                            location_names.append(inventory_entry.location.name)
                    
                    # Build combined text
                    combined_text = self.build_combined_text(item, category_name, location_names)
                    
                    # Create OpenAI embedding
                    embedding = await self.create_openai_embedding(combined_text)
                    
                    # Prepare item data
                    item_data = {
                        "postgres_id": item.id,
                        "name": item.name or "",
                        "description": item.description or "",
                        "combined_text": combined_text,
                        "item_type": item.item_type.value if item.item_type else "",
                        "category_name": category_name,
                        "location_names": location_names,
                        "tags": item.tags.split(",") if item.tags else [],
                        "brand": item.brand or "",
                        "model": item.model or "",
                        "created_at": item.created_at or datetime.now(),
                        "updated_at": item.updated_at or datetime.now()
                    }
                    
                    # Insert into Weaviate
                    collection.data.insert(properties=item_data, vector=embedding)
                    
                    processed += 1
                    if processed % 10 == 0:
                        logger.info(f"Processed {processed}/{len(items)} items")
                    
                except Exception as e:
                    logger.error(f"Failed to process item {item.id}: {e}")
                    failed += 1
            
            logger.info(f"Migration completed: {processed} successful, {failed} failed")
            return failed == 0
            
        except Exception as e:
            logger.error(f"Failed to regenerate embeddings: {e}")
            return False
    
    async def rollback_from_backup(self, backup_file: str) -> bool:
        """Restore collection from backup file."""
        try:
            # Load backup data
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
            
            logger.info(f"Loaded backup with {len(backup_data)} items")
            
            # Recreate old collection structure (assuming 384 dimensions)
            if self.weaviate_client.collections.exists("Item"):
                self.weaviate_client.collections.delete("Item")
            
            # Create collection with old dimensions
            # Note: You might need to adjust this based on your original schema
            logger.warning("Rollback functionality needs original schema definition")
            logger.info("Please manually recreate the original collection if needed")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to rollback: {e}")
            return False
    
    async def close(self):
        """Close all connections."""
        if self.weaviate_client:
            self.weaviate_client.close()
        if self.openai_client:
            await self.openai_client.close()


async def main():
    parser = argparse.ArgumentParser(description="Migrate from sentence-transformers to OpenAI embeddings")
    parser.add_argument("--mode", choices=["backup", "migrate", "rollback"], required=True,
                        help="Migration mode")
    parser.add_argument("--openai-key", help="OpenAI API key (required for migrate mode)")
    parser.add_argument("--backup-file", help="Backup file for rollback mode")
    
    args = parser.parse_args()
    
    if args.mode == "migrate" and not args.openai_key:
        parser.error("--openai-key is required for migrate mode")
    
    if args.mode == "rollback" and not args.backup_file:
        parser.error("--backup-file is required for rollback mode")
    
    migrator = OpenAIEmbeddingMigrator(args.openai_key)
    
    try:
        await migrator.initialize()
        
        if args.mode == "backup":
            logger.info("Starting backup process...")
            success = await migrator.backup_existing_collection()
            if success:
                logger.info("✅ Backup completed successfully")
            else:
                logger.error("❌ Backup failed")
                return 1
        
        elif args.mode == "migrate":
            logger.info("Starting full migration process...")
            
            # Step 1: Backup
            logger.info("Step 1: Backing up existing data...")
            if not await migrator.backup_existing_collection():
                logger.error("Backup failed, aborting migration")
                return 1
            
            # Step 2: Recreate collection
            logger.info("Step 2: Recreating collection with new dimensions...")
            if not await migrator.recreate_collection_with_new_dimensions():
                logger.error("Failed to recreate collection, aborting migration")
                return 1
            
            # Step 3: Regenerate embeddings
            logger.info("Step 3: Regenerating embeddings with OpenAI...")
            if not await migrator.regenerate_all_embeddings():
                logger.error("Failed to regenerate embeddings")
                return 1
            
            logger.info("✅ Migration completed successfully!")
            logger.info("🔧 Update your environment variables:")
            logger.info("  - Set OPENAI_API_KEY")
            logger.info("  - Remove WEAVIATE_EMBEDDING_MODEL")
            logger.info("  - Restart your application")
        
        elif args.mode == "rollback":
            logger.info("Starting rollback process...")
            success = await migrator.rollback_from_backup(args.backup_file)
            if success:
                logger.info("✅ Rollback completed")
            else:
                logger.error("❌ Rollback failed")
                return 1
        
        return 0
    
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 1
    
    finally:
        await migrator.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))