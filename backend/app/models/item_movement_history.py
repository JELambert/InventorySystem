"""
Item Movement History model for tracking audit trail of item movements.

This model provides comprehensive auditing for all item movement operations
including relocations, quantity changes, and inventory adjustments.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from decimal import Decimal

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Numeric
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from app.database.base import Base

if TYPE_CHECKING:
    from .item import Item
    from .location import Location


class ItemMovementHistory(Base):
    """
    Item Movement History model for audit trail tracking.
    
    Records all movements and changes to item inventory including:
    - Location changes (moves between locations)
    - Quantity adjustments (increases/decreases)
    - New inventory entries (initial assignments)
    - Inventory removals (item removal from locations)
    """
    __tablename__ = "item_movement_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Core references
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Movement details
    from_location_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    to_location_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("locations.id", ondelete="SET NULL"), nullable=True)
    
    # Quantity tracking
    quantity_moved: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_before: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quantity_after: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Movement type and context
    movement_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # 'move', 'adjust', 'create', 'remove'
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Value tracking (optional)
    estimated_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    
    # Audit information
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False,
        index=True
    )
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # For future user tracking
    system_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # For system-generated notes
    
    # Relationships
    item: Mapped["Item"] = relationship("Item", back_populates="movement_history")
    from_location: Mapped[Optional["Location"]] = relationship("Location", foreign_keys=[from_location_id])
    to_location: Mapped[Optional["Location"]] = relationship("Location", foreign_keys=[to_location_id])

    def __repr__(self) -> str:
        return f"<ItemMovementHistory(id={self.id}, item_id={self.item_id}, type={self.movement_type}, quantity={self.quantity_moved})>"

    @property
    def movement_description(self) -> str:
        """Generate a human-readable description of the movement."""
        if self.movement_type == "create":
            location_name = self.to_location.name if self.to_location else "Unknown Location"
            return f"Added {self.quantity_moved} item(s) to {location_name}"
        elif self.movement_type == "move":
            from_name = self.from_location.name if self.from_location else "Unknown Location"
            to_name = self.to_location.name if self.to_location else "Unknown Location"
            return f"Moved {self.quantity_moved} item(s) from {from_name} to {to_name}"
        elif self.movement_type == "adjust":
            location_name = self.to_location.name if self.to_location else "Unknown Location"
            if self.quantity_before and self.quantity_after:
                change = self.quantity_after - self.quantity_before
                if change > 0:
                    return f"Increased quantity by {change} at {location_name} (now {self.quantity_after})"
                else:
                    return f"Decreased quantity by {abs(change)} at {location_name} (now {self.quantity_after})"
            return f"Adjusted quantity to {self.quantity_moved} at {location_name}"
        elif self.movement_type == "remove":
            location_name = self.from_location.name if self.from_location else "Unknown Location"
            return f"Removed {self.quantity_moved} item(s) from {location_name}"
        else:
            return f"Unknown movement type: {self.movement_type}"

    def to_dict(self) -> dict:
        """Convert movement history to dictionary for API responses."""
        return {
            "id": self.id,
            "item_id": self.item_id,
            "from_location_id": self.from_location_id,
            "to_location_id": self.to_location_id,
            "quantity_moved": self.quantity_moved,
            "quantity_before": self.quantity_before,
            "quantity_after": self.quantity_after,
            "movement_type": self.movement_type,
            "reason": self.reason,
            "notes": self.notes,
            "estimated_value": float(self.estimated_value) if self.estimated_value else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "user_id": self.user_id,
            "system_notes": self.system_notes,
            "movement_description": self.movement_description,
            "from_location": {
                "id": self.from_location.id,
                "name": self.from_location.name,
                "location_type": self.from_location.location_type.value
            } if self.from_location else None,
            "to_location": {
                "id": self.to_location.id,
                "name": self.to_location.name,
                "location_type": self.to_location.location_type.value
            } if self.to_location else None,
            "item": {
                "id": self.item.id,
                "name": self.item.name,
                "item_type": self.item.item_type.value
            } if self.item else None
        }