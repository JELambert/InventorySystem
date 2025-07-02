#!/usr/bin/env python3
"""
Migration script to sync existing items to Weaviate for semantic search.

This script performs a one-time migration of all existing items from PostgreSQL
to Weaviate vector database to enable semantic search capabilities.
"""

import asyncio
import logging
import sys
from typing import Optional
from datetime import datetime

from app.services.item_service import ItemService
from app.database.base import async_session
from app.core.logging import LoggingConfig

# Setup logging
LoggingConfig.setup_logging()
logger = logging.getLogger("weaviate_migration")


async def migrate_items_to_weaviate(
    batch_size: int = 50,
    dry_run: bool = False,
    item_ids: Optional[list] = None
) -> dict:
    """
    Migrate existing items to Weaviate.
    
    Args:
        batch_size: Number of items to process in each batch
        dry_run: If True, only report what would be done without making changes
        item_ids: Specific item IDs to migrate (None for all items)
        
    Returns:
        Migration statistics
    """
    stats = {
        "total_items": 0,
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "start_time": datetime.now(),
        "end_time": None
    }
    
    logger.info(f"Starting Weaviate migration (dry_run={dry_run})")
    
    try:
        async with async_session() as session:
            item_service = ItemService(session)
            
            if dry_run:
                logger.info("DRY RUN: No actual changes will be made")
            
            # Perform bulk sync
            logger.info(f"Syncing items to Weaviate (batch_size={batch_size})")
            sync_stats = await item_service.bulk_sync_to_weaviate(
                item_ids=item_ids,
                force_update=True
            )
            
            stats.update(sync_stats)
            stats["total_items"] = sum([sync_stats.get("success", 0), 
                                      sync_stats.get("failed", 0), 
                                      sync_stats.get("skipped", 0)])
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        stats["failed"] = stats.get("total_items", 0)
    
    finally:
        stats["end_time"] = datetime.now()
        duration = stats["end_time"] - stats["start_time"]
        
        logger.info("Migration completed!")
        logger.info(f"Duration: {duration}")
        logger.info(f"Total items: {stats['total_items']}")
        logger.info(f"Successful: {stats['success']}")
        logger.info(f"Failed: {stats['failed']}")
        logger.info(f"Skipped: {stats['skipped']}")
        
        if stats["total_items"] > 0:
            success_rate = (stats["success"] / stats["total_items"]) * 100
            logger.info(f"Success rate: {success_rate:.1f}%")
    
    return stats


async def check_weaviate_health() -> bool:
    """Check if Weaviate is available and healthy."""
    try:
        from app.services.weaviate_service import get_weaviate_service
        
        logger.info("Checking Weaviate connection...")
        weaviate_service = await get_weaviate_service()
        is_healthy = await weaviate_service.health_check()
        
        if is_healthy:
            stats = await weaviate_service.get_stats()
            logger.info(f"Weaviate is healthy: {stats}")
        else:
            logger.warning("Weaviate is not healthy")
            
        return is_healthy
        
    except Exception as e:
        logger.error(f"Weaviate health check failed: {e}")
        return False


def main():
    """Main migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate existing items to Weaviate for semantic search"
    )
    parser.add_argument(
        "--batch-size", 
        type=int, 
        default=50,
        help="Number of items to process in each batch (default: 50)"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Perform a dry run without making actual changes"
    )
    parser.add_argument(
        "--item-ids", 
        nargs="+", 
        type=int,
        help="Specific item IDs to migrate (space-separated)"
    )
    parser.add_argument(
        "--check-health", 
        action="store_true",
        help="Only check Weaviate health and exit"
    )
    
    args = parser.parse_args()
    
    async def run_migration():
        # Check Weaviate health first
        if not await check_weaviate_health():
            logger.error("Weaviate is not available. Please ensure Weaviate is running.")
            if not args.dry_run:
                return False
            else:
                logger.info("Continuing with dry run despite Weaviate unavailability")
        
        if args.check_health:
            return True
        
        # Run migration
        stats = await migrate_items_to_weaviate(
            batch_size=args.batch_size,
            dry_run=args.dry_run,
            item_ids=args.item_ids
        )
        
        # Return success status
        return stats["failed"] == 0
    
    # Run the migration
    try:
        success = asyncio.run(run_migration())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()