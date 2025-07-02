"""
API v1 router configuration.
"""

from fastapi import APIRouter
from app.api.v1 import locations, categories, items, inventory, performance, search

# Create main v1 router
router = APIRouter(prefix="/v1")

# Include all endpoint routers
router.include_router(locations.router)
router.include_router(categories.router)
router.include_router(items.router)
router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
router.include_router(performance.router, prefix="/performance", tags=["performance"])
router.include_router(search.router, tags=["search"])