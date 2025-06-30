"""
Pydantic schemas for Location model API operations.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from app.models.location import LocationType


class LocationBase(BaseModel):
    """Base schema for Location with common fields."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Location name")
    description: Optional[str] = Field(None, description="Optional location description")
    location_type: LocationType = Field(..., description="Type of location")
    parent_id: Optional[int] = Field(None, description="Parent location ID")
    category_id: Optional[int] = Field(None, description="Category ID")


class LocationCreate(LocationBase):
    """Schema for creating a new location."""
    pass


class LocationUpdate(BaseModel):
    """Schema for updating an existing location."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Location name")
    description: Optional[str] = Field(None, description="Optional location description")
    location_type: Optional[LocationType] = Field(None, description="Type of location")
    parent_id: Optional[int] = Field(None, description="Parent location ID")
    category_id: Optional[int] = Field(None, description="Category ID")


class LocationResponse(LocationBase):
    """Schema for Location API responses."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Unique location ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    full_path: str = Field(..., description="Full hierarchical path")
    depth: int = Field(..., description="Hierarchy depth level")


class LocationWithChildren(LocationResponse):
    """Schema for Location with children information."""
    
    children: List["LocationResponse"] = Field(default_factory=list, description="Child locations")
    descendant_count: int = Field(..., description="Total number of descendants")


class LocationTree(BaseModel):
    """Schema for hierarchical location tree structure."""
    
    location: LocationResponse = Field(..., description="Current location")
    children: List["LocationTree"] = Field(default_factory=list, description="Child location trees")


class LocationSearchQuery(BaseModel):
    """Schema for location search parameters."""
    
    pattern: Optional[str] = Field(None, description="Search pattern for name/description")
    location_type: Optional[LocationType] = Field(None, description="Filter by location type")
    parent_id: Optional[int] = Field(None, description="Filter by parent location")
    max_depth: Optional[int] = Field(None, ge=0, le=10, description="Maximum depth to search")


class LocationValidationResponse(BaseModel):
    """Schema for location validation results."""
    
    is_valid: bool = Field(..., description="Whether the location is valid")
    errors: List[str] = Field(default_factory=list, description="Validation error messages")


# Update forward references
LocationWithChildren.model_rebuild()
LocationTree.model_rebuild()