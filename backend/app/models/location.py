"""
Location model for hierarchical inventory organization.

Supports nested location structure: House → Room → Container → Shelf
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
import enum

from app.database.base import Base


class LocationType(enum.Enum):
    """Enumeration of supported location types."""

    HOUSE = "house"
    ROOM = "room"
    CONTAINER = "container"
    SHELF = "shelf"


class Location(Base):
    """
    Location model representing hierarchical inventory locations.

    Supports self-referential relationships for nested structures like:
    - House (top level)
    - Room (within house)
    - Container (within room)
    - Shelf (within container)
    """

    __tablename__ = "locations"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Core fields
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location_type: Mapped[LocationType] = mapped_column(
        Enum(LocationType), nullable=False, index=True
    )

    # Self-referential relationship
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("locations.id"), nullable=True, index=True
    )
    
    # Category relationship
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=True, index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    parent: Mapped[Optional["Location"]] = relationship(
        "Location", remote_side=[id], back_populates="children"
    )
    children: Mapped[List["Location"]] = relationship(
        "Location", back_populates="parent", cascade="all, delete-orphan"
    )
    category: Mapped[Optional["Category"]] = relationship(
        "Category", back_populates="locations"
    )
    items: Mapped[List["Item"]] = relationship(
        "Item", back_populates="location"
    )

    def __repr__(self) -> str:
        """String representation of the location."""
        return (
            f"<Location(id={self.id}, name='{self.name}', "
            f"type='{self.location_type.value}')>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.name} ({self.location_type.value})"

    @property
    def full_path(self) -> str:
        """
        Get the full hierarchical path of this location.

        Returns:
            String representation of the full path (e.g., "House/Living Room/Bookshelf")
        """
        if self.parent is None:
            return self.name
        return f"{self.parent.full_path}/{self.name}"

    @property
    def depth(self) -> int:
        """
        Get the depth level of this location in the hierarchy.

        Returns:
            Integer depth (0 for root level, 1 for first child, etc.)
        """
        if self.parent is None:
            return 0
        return self.parent.depth + 1

    def is_ancestor_of(self, other: "Location") -> bool:
        """
        Check if this location is an ancestor of another location.

        Args:
            other: Location to check against

        Returns:
            True if this location is an ancestor of the other location
        """
        current = other.parent
        while current is not None:
            if current.id == self.id:
                return True
            current = current.parent
        return False

    def is_descendant_of(self, other: "Location") -> bool:
        """
        Check if this location is a descendant of another location.

        Args:
            other: Location to check against

        Returns:
            True if this location is a descendant of the other location
        """
        return other.is_ancestor_of(self)

    def get_root(self) -> "Location":
        """
        Get the root location in this hierarchy.

        Returns:
            The top-level (root) location
        """
        current = self
        while current.parent is not None:
            current = current.parent
        return current

    def get_all_descendants(self) -> List["Location"]:
        """
        Get all descendant locations recursively.

        Returns:
            List of all descendant locations
        """
        descendants = []
        for child in self.children:
            descendants.append(child)
            descendants.extend(child.get_all_descendants())
        return descendants

    # Validation Methods

    def validate_hierarchy(self) -> bool:
        """
        Validate that this location doesn't create circular references.

        Returns:
            True if hierarchy is valid, False if circular reference detected
        """
        if self.parent_id is None:
            return True

        visited = {self.id}
        current_parent_id = self.parent_id

        # Walk up the parent chain
        while current_parent_id is not None:
            if current_parent_id in visited:
                return False  # Circular reference detected
            visited.add(current_parent_id)

            # Find the parent (this would need session in real use)
            # For now, assume parent is already loaded
            if (
                hasattr(self, "parent")
                and self.parent
                and self.parent.id == current_parent_id
            ):
                current_parent_id = self.parent.parent_id
            else:
                break  # Can't continue validation without session

        return True

    def validate_location_type_order(self) -> bool:
        """
        Validate that location type follows proper nesting order.

        HOUSE can contain: ROOM
        ROOM can contain: CONTAINER
        CONTAINER can contain: SHELF
        SHELF cannot contain anything

        Returns:
            True if nesting order is valid
        """
        if not self.parent:
            # Root locations should be HOUSE
            return self.location_type == LocationType.HOUSE

        parent_type = self.parent.location_type
        current_type = self.location_type

        valid_combinations = {
            LocationType.HOUSE: [LocationType.ROOM],
            LocationType.ROOM: [LocationType.CONTAINER],
            LocationType.CONTAINER: [LocationType.SHELF],
            LocationType.SHELF: [],  # SHELF cannot contain anything
        }

        return current_type in valid_combinations.get(parent_type, [])

    # Bulk Operations

    @classmethod
    def validate_subtree(cls, locations: List["Location"]) -> List[str]:
        """
        Validate a collection of locations for hierarchy and type order issues.

        Args:
            locations: List of Location objects to validate

        Returns:
            List of validation error messages (empty if all valid)
        """
        errors = []

        for location in locations:
            if not location.validate_hierarchy():
                errors.append(
                    f"Circular reference detected for location "
                    f"'{location.name}' (ID: {location.id})"
                )

            if not location.validate_location_type_order():
                parent_type = (
                    location.parent.location_type.value if location.parent else "none"
                )
                errors.append(
                    f"Invalid nesting: {location.location_type.value} cannot be "
                    f"child of {parent_type} for location '{location.name}' "
                    f"(ID: {location.id})"
                )

        return errors

    # Search and Filtering Methods

    @classmethod
    def find_by_pattern(
        cls, pattern: str, locations: List["Location"]
    ) -> List["Location"]:
        """
        Find locations matching a name pattern.

        Args:
            pattern: Pattern to match (case-insensitive substring search)
            locations: List of locations to search

        Returns:
            List of matching locations
        """
        pattern_lower = pattern.lower()
        return [
            loc
            for loc in locations
            if pattern_lower in loc.name.lower()
            or (loc.description and pattern_lower in loc.description.lower())
        ]

    @classmethod
    def filter_by_type(
        cls, location_type: LocationType, locations: List["Location"]
    ) -> List["Location"]:
        """
        Filter locations by type.

        Args:
            location_type: LocationType to filter by
            locations: List of locations to filter

        Returns:
            List of locations matching the type
        """
        return [loc for loc in locations if loc.location_type == location_type]

    def search_descendants(self, pattern: str) -> List["Location"]:
        """
        Search for locations within this location's descendants.

        Args:
            pattern: Pattern to match (case-insensitive substring search)

        Returns:
            List of descendant locations matching the pattern
        """
        descendants = self.get_all_descendants()
        return self.find_by_pattern(pattern, descendants)

    # Performance and Utility Methods

    def get_path_components(self) -> List[str]:
        """
        Get the path components as a list.

        Returns:
            List of location names from root to this location
        """
        components = []
        current = self
        while current is not None:
            components.insert(0, current.name)
            current = current.parent
        return components

    def get_descendant_count(self) -> int:
        """
        Get the total number of descendants.

        Returns:
            Total count of all descendant locations
        """
        return len(self.get_all_descendants())

    def has_children(self) -> bool:
        """
        Check if this location has any child locations.

        Returns:
            True if this location has children
        """
        return len(self.children) > 0
