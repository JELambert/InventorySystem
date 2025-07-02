"""
Pydantic schemas for Item model API operations.

Provides comprehensive schemas for Item CRUD operations including
validation, serialization, and API documentation.
"""

from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, validator, field_validator
from enum import Enum

from app.models.item import ItemType, ItemCondition, ItemStatus


class ItemBase(BaseModel):
    """Base schema for Item with common fields."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Item name or title")
    description: Optional[str] = Field(None, description="Detailed description of the item")
    item_type: ItemType = Field(..., description="Primary classification of the item")
    condition: ItemCondition = Field(ItemCondition.GOOD, description="Physical condition of the item")
    status: ItemStatus = Field(ItemStatus.AVAILABLE, description="Current status/availability of the item")
    
    # Identification and tracking
    brand: Optional[str] = Field(None, max_length=100, description="Brand or manufacturer")
    model: Optional[str] = Field(None, max_length=100, description="Model number or name")
    serial_number: Optional[str] = Field(None, max_length=100, description="Serial number (if applicable)")
    barcode: Optional[str] = Field(None, max_length=50, description="Barcode or UPC (if applicable)")
    
    # Value tracking
    purchase_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Original purchase price")
    current_value: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Current estimated value")
    
    # Temporal information
    purchase_date: Optional[datetime] = Field(None, description="Date of purchase")
    warranty_expiry: Optional[datetime] = Field(None, description="Warranty expiration date")
    
    # Physical properties
    weight: Optional[Decimal] = Field(None, ge=0, decimal_places=3, description="Weight in kilograms")
    dimensions: Optional[str] = Field(None, max_length=100, description="Dimensions (e.g., '10x20x5 cm')")
    color: Optional[str] = Field(None, max_length=50, description="Primary color")
    
    # Relationships
    category_id: Optional[int] = Field(None, description="Optional category for organization")
    
    # Additional metadata
    notes: Optional[str] = Field(None, description="Additional notes or observations")
    tags: Optional[str] = Field(None, max_length=500, description="Comma-separated tags for flexible categorization")

    @field_validator('serial_number')
    @classmethod
    def validate_serial_number(cls, v):
        if v is not None and len(v.strip()) < 3:
            raise ValueError('Serial number must be at least 3 characters long')
        return v
    
    @field_validator('barcode')
    @classmethod
    def validate_barcode(cls, v):
        if v is not None:
            if not v.isdigit():
                raise ValueError('Barcode must contain only digits')
            if len(v) not in [8, 12, 13, 14]:
                raise ValueError('Barcode must be 8, 12, 13, or 14 digits long')
        return v
    
    @field_validator('warranty_expiry')
    @classmethod
    def validate_warranty_expiry(cls, v, info):
        if v is not None and 'purchase_date' in info.data:
            purchase_date = info.data['purchase_date']
            if purchase_date and v < purchase_date:
                raise ValueError('Warranty expiry must be after purchase date')
        return v


class ItemCreate(ItemBase):
    """Schema for creating a new item."""
    pass


class ItemCreateWithLocation(ItemBase):
    """Schema for creating a new item with location assignment."""
    location_id: int = Field(..., description="Location where item will be stored")
    quantity: int = Field(1, ge=1, description="Quantity of items to add to location")


class ItemUpdate(BaseModel):
    """Schema for updating an existing item."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Item name or title")
    description: Optional[str] = Field(None, description="Detailed description of the item")
    item_type: Optional[ItemType] = Field(None, description="Primary classification of the item")
    condition: Optional[ItemCondition] = Field(None, description="Physical condition of the item")
    status: Optional[ItemStatus] = Field(None, description="Current status/availability of the item")
    
    # Identification and tracking
    brand: Optional[str] = Field(None, max_length=100, description="Brand or manufacturer")
    model: Optional[str] = Field(None, max_length=100, description="Model number or name")
    serial_number: Optional[str] = Field(None, max_length=100, description="Serial number (if applicable)")
    barcode: Optional[str] = Field(None, max_length=50, description="Barcode or UPC (if applicable)")
    
    # Value tracking
    purchase_price: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Original purchase price")
    current_value: Optional[Decimal] = Field(None, ge=0, decimal_places=2, description="Current estimated value")
    
    # Temporal information
    purchase_date: Optional[datetime] = Field(None, description="Date of purchase")
    warranty_expiry: Optional[datetime] = Field(None, description="Warranty expiration date")
    
    # Physical properties
    weight: Optional[Decimal] = Field(None, ge=0, decimal_places=3, description="Weight in kilograms")
    dimensions: Optional[str] = Field(None, max_length=100, description="Dimensions (e.g., '10x20x5 cm')")
    color: Optional[str] = Field(None, max_length=50, description="Primary color")
    
    # Relationships
    location_id: Optional[int] = Field(None, description="Location where item is stored")
    category_id: Optional[int] = Field(None, description="Optional category for organization")
    
    # Additional metadata
    notes: Optional[str] = Field(None, description="Additional notes or observations")
    tags: Optional[str] = Field(None, max_length=500, description="Comma-separated tags for flexible categorization")

    @field_validator('serial_number')
    @classmethod
    def validate_serial_number(cls, v):
        if v is not None and len(v.strip()) < 3:
            raise ValueError('Serial number must be at least 3 characters long')
        return v
    
    @field_validator('barcode')
    @classmethod
    def validate_barcode(cls, v):
        if v is not None:
            if not v.isdigit():
                raise ValueError('Barcode must contain only digits')
            if len(v) not in [8, 12, 13, 14]:
                raise ValueError('Barcode must be 8, 12, 13, or 14 digits long')
        return v


class ItemResponse(ItemBase):
    """Schema for item responses including computed fields."""
    
    id: int = Field(..., description="Item ID")
    is_active: bool = Field(..., description="Whether this item is active (soft delete)")
    version: int = Field(..., description="Version number for optimistic locking")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    # Computed fields
    display_name: Optional[str] = Field(None, description="Display-friendly name for the item")
    full_location_path: Optional[str] = Field(None, description="Full path to this item's location")
    is_valuable: Optional[bool] = Field(None, description="Whether item has significant value (over $100)")
    age_days: Optional[int] = Field(None, description="Age of the item in days since purchase")
    is_under_warranty: Optional[bool] = Field(None, description="Whether item is still under warranty")
    tag_list: Optional[List[str]] = Field(None, description="Tags as a list")

    model_config = ConfigDict(from_attributes=True)


class ItemSummary(BaseModel):
    """Lightweight schema for item lists and summaries."""
    
    id: int = Field(..., description="Item ID")
    name: str = Field(..., description="Item name or title")
    item_type: ItemType = Field(..., description="Primary classification of the item")
    condition: ItemCondition = Field(..., description="Physical condition of the item")
    status: ItemStatus = Field(..., description="Current status/availability of the item")
    brand: Optional[str] = Field(None, description="Brand or manufacturer")
    model: Optional[str] = Field(None, description="Model number or name")
    current_value: Optional[Decimal] = Field(None, description="Current estimated value")
    category_id: Optional[int] = Field(None, description="Optional category for organization")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class ItemSearch(BaseModel):
    """Schema for item search parameters."""
    
    # Text search
    search_text: Optional[str] = Field(None, description="Search in item names, descriptions, and notes")
    
    # Filters
    item_type: Optional[ItemType] = Field(None, description="Filter by item type")
    condition: Optional[ItemCondition] = Field(None, description="Filter by condition")
    status: Optional[ItemStatus] = Field(None, description="Filter by status")
    location_id: Optional[int] = Field(None, description="Filter by location")
    category_id: Optional[int] = Field(None, description="Filter by category")
    brand: Optional[str] = Field(None, description="Filter by brand")
    
    # Value filters
    min_value: Optional[Decimal] = Field(None, ge=0, description="Minimum current value")
    max_value: Optional[Decimal] = Field(None, ge=0, description="Maximum current value")
    
    # Date filters
    purchased_after: Optional[datetime] = Field(None, description="Items purchased after this date")
    purchased_before: Optional[datetime] = Field(None, description="Items purchased before this date")
    warranty_expiring_before: Optional[datetime] = Field(None, description="Items with warranty expiring before this date")
    
    # Special filters
    has_warranty: Optional[bool] = Field(None, description="Filter items with active warranty")
    is_valuable: Optional[bool] = Field(None, description="Filter valuable items (over $100)")
    has_serial_number: Optional[bool] = Field(None, description="Filter items with serial numbers")
    has_barcode: Optional[bool] = Field(None, description="Filter items with barcodes")
    tags: Optional[str] = Field(None, description="Filter by tags (comma-separated)")
    
    # Sorting
    sort_by: Optional[str] = Field("name", description="Sort field (name, created_at, current_value, etc.)")
    sort_order: Optional[str] = Field("asc", pattern="^(asc|desc)$", description="Sort order")
    
    # Pagination
    skip: Optional[int] = Field(0, ge=0, description="Number of items to skip")
    limit: Optional[int] = Field(50, ge=1, le=1000, description="Maximum number of items to return")


class ItemBulkUpdate(BaseModel):
    """Schema for bulk item updates."""
    
    item_ids: List[int] = Field(..., min_length=1, description="List of item IDs to update")
    updates: ItemUpdate = Field(..., description="Updates to apply to all items")


class ItemMoveRequest(BaseModel):
    """Schema for moving items to a new location."""
    
    item_ids: List[int] = Field(..., min_length=1, description="List of item IDs to move")
    new_location_id: int = Field(..., description="Target location ID")
    notes: Optional[str] = Field(None, description="Optional notes for the move operation")


class ItemStatusUpdate(BaseModel):
    """Schema for updating item status."""
    
    new_status: ItemStatus = Field(..., description="New status for the item")
    notes: Optional[str] = Field(None, description="Optional notes for the status change")


class ItemConditionUpdate(BaseModel):
    """Schema for updating item condition."""
    
    new_condition: ItemCondition = Field(..., description="New condition for the item")
    notes: Optional[str] = Field(None, description="Optional notes for the condition change")


class ItemValueUpdate(BaseModel):
    """Schema for updating item value."""
    
    new_value: Decimal = Field(..., ge=0, decimal_places=2, description="New current value for the item")
    notes: Optional[str] = Field(None, description="Optional notes for the value change")


class ItemStatistics(BaseModel):
    """Schema for item statistics."""
    
    total_items: int = Field(..., description="Total number of items")
    active_items: int = Field(..., description="Number of active items")
    total_value: Optional[float] = Field(None, description="Total estimated value of all items")
    average_value: Optional[float] = Field(None, description="Average value per item")
    
    # Counts by enumeration
    by_type: dict = Field(default_factory=dict, description="Count of items by type")
    by_condition: dict = Field(default_factory=dict, description="Count of items by condition")
    by_status: dict = Field(default_factory=dict, description="Count of items by status")
    
    # Location and category statistics
    by_location: dict = Field(default_factory=dict, description="Count of items by location")
    by_category: dict = Field(default_factory=dict, description="Count of items by category")
    
    # Warranty and value insights
    items_under_warranty: int = Field(0, description="Number of items still under warranty")
    valuable_items: int = Field(0, description="Number of valuable items (over $100)")
    items_with_serial: int = Field(0, description="Number of items with serial numbers")
    items_with_barcode: int = Field(0, description="Number of items with barcodes")


class ItemTagResponse(BaseModel):
    """Schema for tag operations responses."""
    
    item_id: int = Field(..., description="Item ID")
    tags: List[str] = Field(..., description="Current tags for the item")


class ItemHistoryEntry(BaseModel):
    """Schema for item history/audit trail."""
    
    timestamp: datetime = Field(..., description="When the change occurred")
    change_type: str = Field(..., description="Type of change (move, status, condition, value, etc.)")
    old_value: Optional[str] = Field(None, description="Previous value")
    new_value: Optional[str] = Field(None, description="New value")
    notes: Optional[str] = Field(None, description="Notes associated with the change")
    version: int = Field(..., description="Item version after this change")


class ItemImportRequest(BaseModel):
    """Schema for bulk item import."""
    
    items: List[ItemCreate] = Field(..., min_length=1, description="List of items to import")
    validate_only: bool = Field(False, description="Only validate without importing")
    skip_duplicates: bool = Field(True, description="Skip items with duplicate serial numbers or barcodes")


class ItemImportResult(BaseModel):
    """Schema for item import results."""
    
    success: bool = Field(..., description="Whether the import was successful")
    created_items: List[ItemResponse] = Field(default_factory=list, description="Successfully created items")
    errors: List[str] = Field(default_factory=list, description="Import errors")
    skipped_items: List[str] = Field(default_factory=list, description="Skipped items (duplicates, errors)")
    total_processed: int = Field(0, description="Total number of items processed")


class ItemExportRequest(BaseModel):
    """Schema for item export requests."""
    
    format: str = Field("csv", pattern="^(csv|json)$", description="Export format")
    filters: Optional[ItemSearch] = Field(None, description="Optional filters to apply")
    include_inactive: bool = Field(False, description="Include inactive (soft-deleted) items")
    include_computed_fields: bool = Field(True, description="Include computed fields in export")


# Semantic Search Schemas

class SemanticSearchRequest(BaseModel):
    """Schema for semantic search requests."""
    
    query: str = Field(..., min_length=1, max_length=500, description="Natural language search query")
    limit: int = Field(50, ge=1, le=100, description="Maximum number of results to return")
    certainty: float = Field(0.7, ge=0.1, le=1.0, description="Minimum certainty threshold for results")
    include_scores: bool = Field(True, description="Include similarity scores in response")


class HybridSearchRequest(BaseModel):
    """Schema for hybrid semantic + traditional search requests."""
    
    query: str = Field(..., min_length=1, max_length=500, description="Natural language search query")
    filters: Optional[ItemSearch] = Field(None, description="Traditional filters to apply")
    limit: int = Field(50, ge=1, le=100, description="Maximum number of results to return")
    certainty: float = Field(0.7, ge=0.1, le=1.0, description="Minimum certainty threshold for semantic results")
    semantic_weight: float = Field(0.7, ge=0.0, le=1.0, description="Weight for semantic vs traditional search")


class SemanticSearchResult(BaseModel):
    """Schema for individual semantic search result."""
    
    item: ItemResponse = Field(..., description="Item details")
    score: float = Field(..., description="Semantic similarity score")
    match_type: str = Field(..., description="Type of match (semantic, traditional, hybrid)")


class SemanticSearchResponse(BaseModel):
    """Schema for semantic search response."""
    
    query: str = Field(..., description="Original search query")
    results: List[SemanticSearchResult] = Field(default_factory=list, description="Search results")
    total_results: int = Field(0, description="Total number of results found")
    search_time_ms: float = Field(0.0, description="Search execution time in milliseconds")
    semantic_enabled: bool = Field(True, description="Whether semantic search was used")
    fallback_used: bool = Field(False, description="Whether fallback to traditional search was used")


class SimilarItemsRequest(BaseModel):
    """Schema for finding similar items."""
    
    item_id: int = Field(..., ge=1, description="ID of the item to find similarities for")
    limit: int = Field(5, ge=1, le=20, description="Maximum number of similar items to return")


class SimilarItemsResponse(BaseModel):
    """Schema for similar items response."""
    
    source_item: ItemResponse = Field(..., description="The source item")
    similar_items: List[SemanticSearchResult] = Field(default_factory=list, description="Similar items")
    total_found: int = Field(0, description="Total number of similar items found")


class WeaviateHealthResponse(BaseModel):
    """Schema for Weaviate health check response."""
    
    status: str = Field(..., description="Weaviate service status")
    item_count: int = Field(0, description="Number of items in vector database")
    embedding_model: str = Field("", description="Current embedding model")
    weaviate_url: str = Field("", description="Weaviate instance URL")
    last_sync: Optional[datetime] = Field(None, description="Last successful sync timestamp")


class EmbeddingBatchRequest(BaseModel):
    """Schema for batch embedding creation."""
    
    item_ids: List[int] = Field(..., min_length=1, description="List of item IDs to create embeddings for")
    force_update: bool = Field(False, description="Force update existing embeddings")


class EmbeddingBatchResponse(BaseModel):
    """Schema for batch embedding response."""
    
    success_count: int = Field(0, description="Number of embeddings created successfully")
    failed_count: int = Field(0, description="Number of embeddings that failed")
    skipped_count: int = Field(0, description="Number of embeddings skipped")
    total_processed: int = Field(0, description="Total number of items processed")
    errors: List[str] = Field(default_factory=list, description="Error messages for failed embeddings")