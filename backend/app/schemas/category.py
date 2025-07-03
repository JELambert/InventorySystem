"""Category Pydantic schemas for API requests and responses."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict
import re


class CategoryBase(BaseModel):
    """Base category schema with common fields."""
    
    name: str = Field(..., min_length=1, max_length=100, description="Category name")
    description: Optional[str] = Field(None, max_length=500, description="Category description")
    color: Optional[str] = Field(None, description="Category color in hex format (#RRGGBB)")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate category name."""
        if not v or not v.strip():
            raise ValueError('Category name cannot be empty')
        return v.strip()
    
    @field_validator('color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate color is in proper hex format."""
        if v is None:
            return v
        
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError('Color must be in hex format (#RRGGBB)')
        return v.upper()
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean description."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class CategoryCreate(CategoryBase):
    """Schema for creating a new category."""
    pass


class CategoryUpdate(BaseModel):
    """Schema for updating an existing category."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Category name")
    description: Optional[str] = Field(None, max_length=500, description="Category description")
    color: Optional[str] = Field(None, description="Category color in hex format (#RRGGBB)")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate category name."""
        if v is not None and (not v or not v.strip()):
            raise ValueError('Category name cannot be empty')
        if v is not None:
            v = v.strip()
        return v
    
    @field_validator('color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        """Validate color is in proper hex format."""
        if v is None:
            return v
        
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError('Color must be in hex format (#RRGGBB)')
        return v.upper()
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean description."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v


class CategoryResponse(CategoryBase):
    """Schema for category API responses."""
    
    id: int = Field(..., description="Category ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_active: bool = Field(..., description="Active status flag")
    
    model_config = ConfigDict(from_attributes=True)


class CategoryListResponse(BaseModel):
    """Schema for paginated category list responses."""
    
    categories: list[CategoryResponse] = Field(..., description="List of categories")
    total: int = Field(..., description="Total number of categories")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")
    
    model_config = ConfigDict(from_attributes=True)


class CategoryStats(BaseModel):
    """Schema for category statistics."""
    
    total_categories: int = Field(..., description="Total number of active categories")
    inactive_categories: int = Field(..., description="Number of inactive categories")
    most_used_color: Optional[str] = Field(None, description="Most commonly used color")
    
    model_config = ConfigDict(from_attributes=True)


class CategorySummary(BaseModel):
    """Summary schema for category information."""
    
    id: int = Field(..., description="Category ID")
    name: str = Field(..., description="Category name")
    color: Optional[str] = Field(None, description="Category color")
    is_active: bool = Field(..., description="Active status")
    item_count: int = Field(0, description="Number of items in this category")
    location_count: int = Field(0, description="Number of locations using this category")
    
    model_config = ConfigDict(from_attributes=True)


class CategorySearch(BaseModel):
    """Schema for category search parameters."""
    
    name: Optional[str] = Field(None, description="Search by name pattern")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    has_color: Optional[bool] = Field(None, description="Filter by whether category has color")
    skip: int = Field(0, ge=0, description="Number of items to skip")
    limit: int = Field(100, ge=1, le=1000, description="Number of items to return")