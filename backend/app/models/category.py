"""
Category model for the Home Inventory System.

Provides categorization capabilities for locations and items.
"""

from typing import Optional, List
from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Category(Base):
    """Category model for organizing locations and items."""
    
    __tablename__ = "categories"
    
    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Core fields
    name: Mapped[str] = mapped_column(
        String(255), 
        nullable=False, 
        unique=True,
        index=True,
        comment="Category name (must be unique)"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, 
        nullable=True,
        comment="Optional detailed description of the category"
    )
    color: Mapped[Optional[str]] = mapped_column(
        String(7),  # Hex color code format: #RRGGBB
        nullable=True,
        comment="Optional color for UI display (hex format)"
    )
    
    # Soft delete capability
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether this category is active (soft delete)"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Creation timestamp"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update timestamp"
    )
    
    # Relationships
    locations: Mapped[List["Location"]] = relationship(
        "Location", back_populates="category"
    )
    items: Mapped[List["Item"]] = relationship(
        "Item", back_populates="category"
    )
    
    def __str__(self) -> str:
        """String representation for debugging."""
        status = "active" if self.is_active else "inactive"
        return f"Category(id={self.id}, name='{self.name}', status={status})"
    
    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return (
            f"Category(id={self.id}, name='{self.name}', "
            f"description='{self.description}', color='{self.color}', "
            f"is_active={self.is_active}, created_at={self.created_at})"
        )
    
    # Validation methods
    def validate_color_format(self) -> bool:
        """Validate that color is in valid hex format."""
        if self.color is None:
            return True
        return (
            isinstance(self.color, str) and
            len(self.color) == 7 and
            self.color.startswith('#') and
            all(c in '0123456789ABCDEFabcdef' for c in self.color[1:])
        )
    
    def is_deletable(self) -> bool:
        """Check if category can be safely deleted (no dependencies)."""
        # This will be extended when we add relationships to locations/items
        return self.is_active
    
    def soft_delete(self) -> None:
        """Soft delete the category by marking as inactive."""
        self.is_active = False
        # Use timezone-aware UTC datetime
        from datetime import timezone
        self.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    
    def restore(self) -> None:
        """Restore a soft-deleted category."""
        self.is_active = True
        # Use timezone-aware UTC datetime
        from datetime import timezone
        self.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)