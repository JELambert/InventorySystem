"""
Pydantic schemas for the Home Inventory System.

Exports all schemas for easy importing throughout the application.
"""

# Location schemas
from .location import (
    LocationBase,
    LocationCreate,
    LocationUpdate,
    LocationResponse,
    LocationSummary,
    LocationSearch,
    LocationStats,
    LocationHierarchy,
    LocationChildrenResponse
)

# Category schemas
from .category import (
    CategoryBase,
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategorySummary,
    CategorySearch,
    CategoryStats
)

# Item schemas
from .item import (
    ItemBase,
    ItemCreate,
    ItemCreateWithLocation,
    ItemUpdate,
    ItemResponse,
    ItemSummary,
    ItemSearch,
    ItemBulkUpdate,
    ItemMoveRequest,
    ItemStatusUpdate,
    ItemConditionUpdate,
    ItemValueUpdate,
    ItemStatistics,
    ItemTagResponse,
    ItemHistoryEntry,
    ItemImportRequest,
    ItemImportResult,
    ItemExportRequest,
    # Semantic search schemas
    SemanticSearchRequest,
    HybridSearchRequest,
    SemanticSearchResult,
    SemanticSearchResponse,
    SimilarItemsRequest,
    SimilarItemsResponse,
    WeaviateHealthResponse,
    EmbeddingBatchRequest,
    EmbeddingBatchResponse
)

# Inventory schemas
from .inventory import (
    InventoryBase,
    InventoryCreate,
    InventoryUpdate,
    InventoryResponse,
    InventoryWithDetails,
    InventorySearch,
    InventoryMove,
    InventorySummary,
    InventoryBulkOperation,
    ItemLocationHistory,
    LocationInventoryReport
)

__all__ = [
    # Location schemas
    "LocationBase",
    "LocationCreate", 
    "LocationUpdate",
    "LocationResponse",
    "LocationSummary",
    "LocationSearch",
    "LocationStats",
    "LocationHierarchy",
    "LocationChildrenResponse",
    
    # Category schemas
    "CategoryBase",
    "CategoryCreate",
    "CategoryUpdate", 
    "CategoryResponse",
    "CategorySummary",
    "CategorySearch",
    "CategoryStats",
    
    # Item schemas
    "ItemBase",
    "ItemCreate",
    "ItemUpdate",
    "ItemResponse",
    "ItemSummary", 
    "ItemSearch",
    "ItemBulkUpdate",
    "ItemMoveRequest",
    "ItemStatusUpdate",
    "ItemConditionUpdate",
    "ItemValueUpdate",
    "ItemStatistics",
    "ItemTagResponse",
    "ItemHistoryEntry",
    "ItemImportRequest",
    "ItemImportResult",
    "ItemExportRequest",
    # Semantic search schemas
    "SemanticSearchRequest",
    "HybridSearchRequest", 
    "SemanticSearchResult",
    "SemanticSearchResponse",
    "SimilarItemsRequest",
    "SimilarItemsResponse",
    "WeaviateHealthResponse",
    "EmbeddingBatchRequest",
    "EmbeddingBatchResponse",
    
    # Inventory schemas
    "InventoryBase",
    "InventoryCreate",
    "InventoryUpdate", 
    "InventoryResponse",
    "InventoryWithDetails",
    "InventorySearch",
    "InventoryMove",
    "InventorySummary",
    "InventoryBulkOperation",
    "ItemLocationHistory",
    "LocationInventoryReport"
]