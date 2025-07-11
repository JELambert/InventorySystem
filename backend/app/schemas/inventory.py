"""
Pydantic schemas for Inventory model operations.

Handles serialization and validation for inventory-related API operations.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

from .item import ItemSummary
from .location import LocationSummary


class InventoryBase(BaseModel):
    """Base schema for inventory operations."""
    
    item_id: int = Field(..., description="ID of the item", gt=0)
    location_id: int = Field(..., description="ID of the location", gt=0)
    quantity: int = Field(default=1, description="Quantity of items at this location", ge=1)


class InventoryCreate(InventoryBase):
    """Schema for creating new inventory entries."""
    pass


class InventoryUpdate(BaseModel):
    """Schema for updating inventory entries."""
    
    quantity: Optional[int] = Field(None, description="New quantity (if changing)", ge=1)
    location_id: Optional[int] = Field(None, description="New location ID (if moving)", gt=0)


class InventoryResponse(InventoryBase):
    """Schema for inventory responses."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Inventory entry ID")
    updated_at: datetime = Field(..., description="Last update timestamp")
    total_value: Optional[float] = Field(None, description="Total value of items at this location")


class InventoryWithDetails(InventoryResponse):
    """Schema for inventory responses with item and location details."""
    
    item: Optional[ItemSummary] = Field(None, description="Item details")
    location: Optional[LocationSummary] = Field(None, description="Location details")


class InventorySearch(BaseModel):
    """Schema for inventory search parameters."""
    
    item_id: Optional[int] = Field(None, description="Filter by item ID", gt=0)
    location_id: Optional[int] = Field(None, description="Filter by location ID", gt=0)
    min_quantity: Optional[int] = Field(None, description="Minimum quantity filter", ge=1)
    max_quantity: Optional[int] = Field(None, description="Maximum quantity filter", ge=1)
    min_value: Optional[float] = Field(None, description="Minimum total value filter", ge=0)
    max_value: Optional[float] = Field(None, description="Maximum total value filter", ge=0)


class InventoryMove(BaseModel):
    """Schema for moving items between locations."""
    
    from_location_id: int = Field(..., description="Source location ID", gt=0)
    to_location_id: int = Field(..., description="Destination location ID", gt=0)
    quantity: int = Field(..., description="Quantity to move", ge=1)
    reason: Optional[str] = Field(None, max_length=255, description="Optional reason for the move")
    
    def validate_different_locations(self) -> bool:
        """Validate that source and destination are different."""
        return self.from_location_id != self.to_location_id


class InventorySummary(BaseModel):
    """Schema for inventory summary information."""
    
    total_items: int = Field(..., description="Total number of unique items")
    total_quantity: int = Field(..., description="Total quantity across all items")
    total_locations: int = Field(..., description="Number of locations with items")
    total_value: Optional[float] = Field(None, description="Total estimated value")
    by_location: List[dict] = Field(default_factory=list, description="Summary by location")
    by_item_type: List[dict] = Field(default_factory=list, description="Summary by item type")


class InventoryBulkOperation(BaseModel):
    """Schema for bulk inventory operations."""
    
    operations: List[InventoryCreate] = Field(..., description="List of inventory operations")
    
    def validate_operations(self) -> List[str]:
        """Validate all operations in the bulk request."""
        errors = []
        
        if not self.operations:
            errors.append("At least one operation is required")
        
        if len(self.operations) > 100:
            errors.append("Maximum 100 operations allowed per bulk request")
        
        # Check for duplicate item-location combinations
        seen_combinations = set()
        for i, op in enumerate(self.operations):
            combination = (op.item_id, op.location_id)
            if combination in seen_combinations:
                errors.append(f"Operation {i+1}: Duplicate item-location combination")
            seen_combinations.add(combination)
        
        return errors


class ItemLocationHistory(BaseModel):
    """Schema for tracking item movement history."""
    
    item_id: int = Field(..., description="Item ID")
    locations: List[dict] = Field(..., description="Location history with timestamps")
    current_locations: List[InventoryWithDetails] = Field(..., description="Current locations and quantities")


class LocationInventoryReport(BaseModel):
    """Schema for location-based inventory reports."""
    
    location_id: int = Field(..., description="Location ID")
    location_name: str = Field(..., description="Location name")
    location_path: str = Field(..., description="Full location path")
    total_items: int = Field(..., description="Number of unique items")
    total_quantity: int = Field(..., description="Total quantity of all items")
    total_value: Optional[float] = Field(None, description="Total estimated value")
    items: List[InventoryWithDetails] = Field(..., description="Items in this location")
    utilization: Optional[float] = Field(None, description="Location utilization percentage")