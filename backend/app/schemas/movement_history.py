"""
Pydantic schemas for Item Movement History operations.

Handles serialization and validation for movement history tracking.
"""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict

from .item import ItemSummary
from .location import LocationSummary


class MovementHistoryBase(BaseModel):
    """Base schema for movement history operations."""
    
    item_id: int = Field(..., description="ID of the item that was moved", gt=0)
    from_location_id: Optional[int] = Field(None, description="Source location ID (null for new items)", gt=0)
    to_location_id: Optional[int] = Field(None, description="Destination location ID (null for removals)", gt=0)
    quantity_moved: int = Field(..., description="Quantity that was moved", ge=1)
    quantity_before: Optional[int] = Field(None, description="Quantity before the operation", ge=0)
    quantity_after: Optional[int] = Field(None, description="Quantity after the operation", ge=0)
    movement_type: str = Field(..., description="Type of movement", max_length=50)
    reason: Optional[str] = Field(None, description="Reason for the movement", max_length=255)
    notes: Optional[str] = Field(None, description="Additional notes about the movement")
    estimated_value: Optional[Decimal] = Field(None, description="Estimated value of moved items", ge=0, decimal_places=2)
    user_id: Optional[str] = Field(None, description="User who performed the operation", max_length=255)
    system_notes: Optional[str] = Field(None, description="System-generated notes")


class MovementHistoryCreate(MovementHistoryBase):
    """Schema for creating new movement history entries."""
    pass


class MovementHistoryResponse(MovementHistoryBase):
    """Schema for movement history responses."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Movement history entry ID")
    created_at: datetime = Field(..., description="When the movement occurred")
    movement_description: str = Field(..., description="Human-readable description of the movement")


class MovementHistoryWithDetails(MovementHistoryResponse):
    """Schema for movement history responses with item and location details."""
    
    item: Optional[ItemSummary] = Field(None, description="Item details")
    from_location: Optional[LocationSummary] = Field(None, description="Source location details")
    to_location: Optional[LocationSummary] = Field(None, description="Destination location details")


class MovementHistorySearch(BaseModel):
    """Schema for movement history search parameters."""
    
    item_id: Optional[int] = Field(None, description="Filter by item ID", gt=0)
    location_id: Optional[int] = Field(None, description="Filter by either source or destination location ID", gt=0)
    from_location_id: Optional[int] = Field(None, description="Filter by source location ID", gt=0)
    to_location_id: Optional[int] = Field(None, description="Filter by destination location ID", gt=0)
    movement_type: Optional[str] = Field(None, description="Filter by movement type", max_length=50)
    user_id: Optional[str] = Field(None, description="Filter by user who performed the operation", max_length=255)
    start_date: Optional[datetime] = Field(None, description="Filter movements after this date")
    end_date: Optional[datetime] = Field(None, description="Filter movements before this date")
    min_quantity: Optional[int] = Field(None, description="Minimum quantity moved", ge=1)
    max_quantity: Optional[int] = Field(None, description="Maximum quantity moved", ge=1)


class MovementHistorySummary(BaseModel):
    """Schema for movement history summary information."""
    
    total_movements: int = Field(..., description="Total number of movements")
    total_items_moved: int = Field(..., description="Total quantity of items moved")
    unique_items: int = Field(..., description="Number of unique items involved")
    unique_locations: int = Field(..., description="Number of unique locations involved")
    movement_types: List[dict] = Field(default_factory=list, description="Summary by movement type")
    recent_movements: List[MovementHistoryWithDetails] = Field(default_factory=list, description="Recent movements")
    date_range: dict = Field(default_factory=dict, description="Date range of movements")


class BulkMovementCreate(BaseModel):
    """Schema for creating multiple movement history entries."""
    
    movements: List[MovementHistoryCreate] = Field(..., description="List of movement history entries to create")
    
    def validate_movements(self) -> List[str]:
        """Validate all movements in the bulk request."""
        errors = []
        
        if not self.movements:
            errors.append("At least one movement is required")
        
        if len(self.movements) > 100:
            errors.append("Maximum 100 movements allowed per bulk request")
        
        return errors


class MovementTypeStats(BaseModel):
    """Schema for movement type statistics."""
    
    movement_type: str = Field(..., description="Type of movement")
    count: int = Field(..., description="Number of movements of this type")
    total_quantity: int = Field(..., description="Total quantity moved for this type")
    percentage: float = Field(..., description="Percentage of total movements")


class ItemMovementTimeline(BaseModel):
    """Schema for item movement timeline."""
    
    item_id: int = Field(..., description="Item ID")
    item_name: str = Field(..., description="Item name")
    movements: List[MovementHistoryWithDetails] = Field(default_factory=list, description="Chronological list of movements")
    current_locations: List[dict] = Field(default_factory=list, description="Current location information")
    total_movements: int = Field(..., description="Total number of movements for this item")