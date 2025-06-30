"""
Item model for the Home Inventory System.

Represents physical items stored in locations, with categorization support.
"""

from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .inventory import Inventory
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Text, Boolean, DateTime, Integer, Numeric, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum

from app.database.base import Base


class ItemType(enum.Enum):
    """Enumeration of item types for classification."""
    
    ELECTRONICS = "electronics"
    FURNITURE = "furniture"
    CLOTHING = "clothing"
    BOOKS = "books"
    DOCUMENTS = "documents"
    TOOLS = "tools"
    KITCHEN = "kitchen"
    DECOR = "decor"
    COLLECTIBLES = "collectibles"
    HOBBY = "hobby"
    OFFICE = "office"
    PERSONAL = "personal"
    SEASONAL = "seasonal"
    STORAGE = "storage"
    OTHER = "other"


class ItemCondition(enum.Enum):
    """Enumeration of item condition states."""
    
    EXCELLENT = "excellent"
    VERY_GOOD = "very_good"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    FOR_REPAIR = "for_repair"
    NOT_WORKING = "not_working"


class ItemStatus(enum.Enum):
    """Enumeration of item status states."""
    
    AVAILABLE = "available"
    IN_USE = "in_use"
    RESERVED = "reserved"
    LOANED = "loaned"
    MISSING = "missing"
    DISPOSED = "disposed"
    SOLD = "sold"


class Item(Base):
    """
    Item model representing physical inventory items.
    
    Each item belongs to a location and can optionally be categorized.
    Supports rich metadata including value tracking, condition, and status.
    """
    
    __tablename__ = "items"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Core identification fields
    name: Mapped[str] = mapped_column(
        String(255), 
        nullable=False, 
        index=True,
        comment="Item name or title"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, 
        nullable=True,
        comment="Detailed description of the item"
    )
    
    # Item classification
    item_type: Mapped[ItemType] = mapped_column(
        Enum(ItemType), 
        nullable=False, 
        index=True,
        comment="Primary classification of the item"
    )
    condition: Mapped[ItemCondition] = mapped_column(
        Enum(ItemCondition), 
        nullable=False,
        default=ItemCondition.GOOD,
        comment="Physical condition of the item"
    )
    status: Mapped[ItemStatus] = mapped_column(
        Enum(ItemStatus), 
        nullable=False,
        default=ItemStatus.AVAILABLE,
        index=True,
        comment="Current status/availability of the item"
    )
    
    # Identification and tracking
    brand: Mapped[Optional[str]] = mapped_column(
        String(100), 
        nullable=True,
        index=True,
        comment="Brand or manufacturer"
    )
    model: Mapped[Optional[str]] = mapped_column(
        String(100), 
        nullable=True,
        comment="Model number or name"
    )
    serial_number: Mapped[Optional[str]] = mapped_column(
        String(100), 
        nullable=True,
        unique=True,
        index=True,
        comment="Serial number (if applicable)"
    )
    barcode: Mapped[Optional[str]] = mapped_column(
        String(50), 
        nullable=True,
        unique=True,
        index=True,
        comment="Barcode or UPC (if applicable)"
    )
    
    # Value tracking
    purchase_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), 
        nullable=True,
        comment="Original purchase price"
    )
    current_value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2), 
        nullable=True,
        comment="Current estimated value"
    )
    
    # Temporal information
    purchase_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Date of purchase"
    )
    warranty_expiry: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), 
        nullable=True,
        comment="Warranty expiration date"
    )
    
    # Physical properties
    weight: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 3), 
        nullable=True,
        comment="Weight in kilograms"
    )
    dimensions: Mapped[Optional[str]] = mapped_column(
        String(100), 
        nullable=True,
        comment="Dimensions (e.g., '10x20x5 cm')"
    )
    color: Mapped[Optional[str]] = mapped_column(
        String(50), 
        nullable=True,
        comment="Primary color"
    )
    
    # Note: location relationship now handled through inventory table
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, 
        ForeignKey("categories.id"), 
        nullable=True, 
        index=True,
        comment="Optional category for organization"
    )
    
    # Soft delete and versioning
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether this item is active (soft delete)"
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="Version number for optimistic locking"
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
    
    # Additional metadata
    notes: Mapped[Optional[str]] = mapped_column(
        Text, 
        nullable=True,
        comment="Additional notes or observations"
    )
    tags: Mapped[Optional[str]] = mapped_column(
        String(500), 
        nullable=True,
        comment="Comma-separated tags for flexible categorization"
    )
    
    # Relationships
    category: Mapped[Optional["Category"]] = relationship(
        "Category", back_populates="items"
    )
    inventory_entries: Mapped[List["Inventory"]] = relationship(
        "Inventory", back_populates="item", cascade="all, delete-orphan"
    )
    
    def __init__(self, **kwargs):
        """Initialize Item with default values."""
        super().__init__(**kwargs)
        # Ensure version is initialized for objects created outside database
        if self.version is None:
            self.version = 1
    
    def __str__(self) -> str:
        """String representation for debugging."""
        return f"Item(id={self.id}, name='{self.name}', type={self.item_type.value})"
    
    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return (
            f"Item(id={self.id}, name='{self.name}', "
            f"type={self.item_type.value}, condition={self.condition.value}, "
            f"status={self.status.value})"
        )
    
    # Property methods
    @property
    def primary_location(self) -> Optional["Location"]:
        """Get the primary location for this item (first inventory entry)."""
        from .location import Location
        if self.inventory_entries:
            return self.inventory_entries[0].location
        return None
    
    @property
    def full_location_path(self) -> str:
        """Get the full path to this item's primary location."""
        primary_loc = self.primary_location
        if primary_loc:
            return f"{primary_loc.full_path}/{self.name}"
        return self.name
    
    @property
    def display_name(self) -> str:
        """Get a display-friendly name for the item."""
        if self.brand and self.model:
            return f"{self.brand} {self.model} - {self.name}"
        elif self.brand:
            return f"{self.brand} - {self.name}"
        return self.name
    
    @property
    def is_valuable(self) -> bool:
        """Check if item has significant value (over $100)."""
        if self.current_value:
            return self.current_value >= 100
        elif self.purchase_price:
            return self.purchase_price >= 100
        return False
    
    @property
    def age_days(self) -> Optional[int]:
        """Get the age of the item in days since purchase."""
        if self.purchase_date:
            return (datetime.now().replace(tzinfo=None) - 
                   self.purchase_date.replace(tzinfo=None)).days
        return None
    
    @property
    def is_under_warranty(self) -> bool:
        """Check if item is still under warranty."""
        if self.warranty_expiry:
            return datetime.now().replace(tzinfo=None) < self.warranty_expiry.replace(tzinfo=None)
        return False
    
    # Validation methods
    def validate_serial_number_format(self) -> bool:
        """Validate serial number format (basic check)."""
        if not self.serial_number:
            return True
        return len(self.serial_number.strip()) >= 3
    
    def validate_barcode_format(self) -> bool:
        """Validate barcode format (basic check)."""
        if not self.barcode:
            return True
        # Basic validation - should be numeric and appropriate length
        return (self.barcode.isdigit() and 
                len(self.barcode) in [8, 12, 13, 14])  # Common barcode lengths
    
    def validate_price_values(self) -> bool:
        """Validate that price values are non-negative."""
        if self.purchase_price and self.purchase_price < 0:
            return False
        if self.current_value and self.current_value < 0:
            return False
        return True
    
    def validate_weight(self) -> bool:
        """Validate that weight is non-negative."""
        if self.weight and self.weight < 0:
            return False
        return True
    
    def validate_dates(self) -> bool:
        """Validate date relationships."""
        now = datetime.now().replace(tzinfo=None)
        
        # Purchase date shouldn't be in the future
        if self.purchase_date and self.purchase_date.replace(tzinfo=None) > now:
            return False
        
        # Warranty expiry should be after purchase date
        if (self.purchase_date and self.warranty_expiry and 
            self.warranty_expiry.replace(tzinfo=None) < self.purchase_date.replace(tzinfo=None)):
            return False
        
        return True
    
    # Business logic methods
    def move_to_location(self, new_location_id: int, quantity: int = 1) -> None:
        """Move item to a new location by updating inventory."""
        # This method now needs to be handled at the service layer
        # since it involves inventory management
        raise NotImplementedError(
            "Item movement now requires inventory management. "
            "Use InventoryService.move_item_to_location() instead."
        )
    
    def update_condition(self, new_condition: ItemCondition, notes: Optional[str] = None) -> None:
        """Update the condition of the item."""
        self.condition = new_condition
        if notes:
            if self.notes:
                self.notes += f"\n{datetime.now().strftime('%Y-%m-%d')}: {notes}"
            else:
                self.notes = f"{datetime.now().strftime('%Y-%m-%d')}: {notes}"
        self.updated_at = datetime.now().replace(tzinfo=None)
        self.version = (self.version or 0) + 1
    
    def update_status(self, new_status: ItemStatus, notes: Optional[str] = None) -> None:
        """Update the status of the item."""
        self.status = new_status
        if notes:
            if self.notes:
                self.notes += f"\n{datetime.now().strftime('%Y-%m-%d')}: Status changed to {new_status.value}. {notes}"
            else:
                self.notes = f"{datetime.now().strftime('%Y-%m-%d')}: Status changed to {new_status.value}. {notes}"
        self.updated_at = datetime.now().replace(tzinfo=None)
        self.version = (self.version or 0) + 1
    
    def update_value(self, new_value: Decimal, notes: Optional[str] = None) -> None:
        """Update the current value of the item."""
        old_value = self.current_value
        self.current_value = new_value
        if notes:
            value_note = f"Value updated from ${old_value or 'N/A'} to ${new_value}. {notes}"
        else:
            value_note = f"Value updated from ${old_value or 'N/A'} to ${new_value}."
        
        if self.notes:
            self.notes += f"\n{datetime.now().strftime('%Y-%m-%d')}: {value_note}"
        else:
            self.notes = f"{datetime.now().strftime('%Y-%m-%d')}: {value_note}"
        
        self.updated_at = datetime.now().replace(tzinfo=None)
        self.version = (self.version or 0) + 1
    
    def soft_delete(self, reason: Optional[str] = None) -> None:
        """Soft delete the item."""
        self.is_active = False
        self.status = ItemStatus.DISPOSED
        
        delete_note = f"Item deactivated"
        if reason:
            delete_note += f": {reason}"
        
        if self.notes:
            self.notes += f"\n{datetime.now().strftime('%Y-%m-%d')}: {delete_note}"
        else:
            self.notes = f"{datetime.now().strftime('%Y-%m-%d')}: {delete_note}"
        
        self.updated_at = datetime.now().replace(tzinfo=None)
        self.version = (self.version or 0) + 1
    
    def restore(self, new_status: ItemStatus = ItemStatus.AVAILABLE) -> None:
        """Restore a soft-deleted item."""
        self.is_active = True
        self.status = new_status
        
        restore_note = f"Item restored with status: {new_status.value}"
        if self.notes:
            self.notes += f"\n{datetime.now().strftime('%Y-%m-%d')}: {restore_note}"
        else:
            self.notes = f"{datetime.now().strftime('%Y-%m-%d')}: {restore_note}"
        
        self.updated_at = datetime.now().replace(tzinfo=None)
        self.version = (self.version or 0) + 1
    
    # Search and filtering methods
    @classmethod
    def validate_item(cls, item_data: dict) -> List[str]:
        """Validate item data and return list of errors."""
        errors = []
        
        # Required fields
        if not item_data.get('name', '').strip():
            errors.append("Item name is required")
        
        # Note: location now handled through inventory table
        
        # Enum validations
        if 'item_type' in item_data:
            try:
                ItemType(item_data['item_type'])
            except ValueError:
                errors.append(f"Invalid item type: {item_data['item_type']}")
        
        if 'condition' in item_data:
            try:
                ItemCondition(item_data['condition'])
            except ValueError:
                errors.append(f"Invalid condition: {item_data['condition']}")
        
        if 'status' in item_data:
            try:
                ItemStatus(item_data['status'])
            except ValueError:
                errors.append(f"Invalid status: {item_data['status']}")
        
        # Value validations
        for field in ['purchase_price', 'current_value', 'weight']:
            value = item_data.get(field)
            if value is not None:
                try:
                    decimal_value = Decimal(str(value))
                    if decimal_value < 0:
                        errors.append(f"{field} cannot be negative")
                except (ValueError, TypeError):
                    errors.append(f"Invalid {field} format")
        
        return errors
    
    def get_tag_list(self) -> List[str]:
        """Get tags as a list."""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the item."""
        current_tags = self.get_tag_list()
        if tag not in current_tags:
            current_tags.append(tag)
            self.tags = ', '.join(current_tags)
            self.updated_at = datetime.now().replace(tzinfo=None)
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the item."""
        current_tags = self.get_tag_list()
        if tag in current_tags:
            current_tags.remove(tag)
            self.tags = ', '.join(current_tags)
            self.updated_at = datetime.now().replace(tzinfo=None)