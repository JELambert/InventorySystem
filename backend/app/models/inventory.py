"""
Inventory model for tracking item quantities at specific locations.

This implements the many-to-many relationship between Items and Locations
with quantity tracking, as specified in Architecture.md.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Column, Integer, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from app.database.base import Base

if TYPE_CHECKING:
    from .item import Item
    from .location import Location


class Inventory(Base):
    """
    Inventory model representing item quantities at specific locations.
    
    This table implements the many-to-many relationship between Items and Locations
    with additional quantity tracking, as designed in Architecture.md.
    """
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    location_id: Mapped[int] = mapped_column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    item: Mapped["Item"] = relationship("Item", back_populates="inventory_entries")
    location: Mapped["Location"] = relationship("Location", back_populates="inventory_entries")

    # Indexes for efficient queries
    __table_args__ = (
        Index('ix_inventory_item_location', 'item_id', 'location_id', unique=True),
        Index('ix_inventory_item_id', 'item_id'),
        Index('ix_inventory_location_id', 'location_id'),
        Index('ix_inventory_updated_at', 'updated_at'),
    )

    def __repr__(self) -> str:
        return f"<Inventory(id={self.id}, item_id={self.item_id}, location_id={self.location_id}, quantity={self.quantity})>"

    @property
    def total_value(self) -> Optional[float]:
        """Calculate total value of items at this location."""
        if self.item and self.item.current_value:
            return float(self.item.current_value) * self.quantity
        return None

    def to_dict(self) -> dict:
        """Convert inventory entry to dictionary."""
        return {
            "id": self.id,
            "item_id": self.item_id,
            "location_id": self.location_id,
            "quantity": self.quantity,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "total_value": self.total_value,
        }