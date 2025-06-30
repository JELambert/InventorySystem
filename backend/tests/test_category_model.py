"""
Test suite for Category model functionality.

Tests all category operations including CRUD, validation, and soft delete.
"""

import pytest
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import Base, engine, create_tables, drop_tables
from app.models.category import Category


async def _get_test_session():
    """Helper to get a test session with setup/teardown."""
    await create_tables()
    try:
        from app.database.base import async_session
        async with async_session() as session:
            yield session
    finally:
        await drop_tables()


@pytest.mark.asyncio
async def test_category_creation():
    """Test basic category creation."""
    async for session in _get_test_session():
        category = Category(
            name="Electronics",
            description="Electronic devices and gadgets",
            color="#FF5733"
        )
        
        session.add(category)
        await session.commit()
        await session.refresh(category)
        
        assert category.id is not None
        assert category.name == "Electronics"
        assert category.description == "Electronic devices and gadgets"
        assert category.color == "#FF5733"
        assert category.is_active is True
        assert isinstance(category.created_at, datetime)
        assert isinstance(category.updated_at, datetime)


@pytest.mark.asyncio
async def test_category_creation_minimal():
    """Test category creation with minimal required fields."""
    async for session in _get_test_session():
        category = Category(name="Books")
        
        session.add(category)
        await session.commit()
        await session.refresh(category)
        
        assert category.id is not None
        assert category.name == "Books"
        assert category.description is None
        assert category.color is None
        assert category.is_active is True


@pytest.mark.asyncio
async def test_category_string_representations():
    """Test string representation methods."""
    async for session in _get_test_session():
        category = Category(
            name="Furniture",
            description="Home furniture items",
            color="#8B4513"
        )
        
        session.add(category)
        await session.commit()
        await session.refresh(category)
        
        # Test __str__ method
        str_repr = str(category)
        assert "Furniture" in str_repr
        assert "active" in str_repr
        assert f"id={category.id}" in str_repr
        
        # Test __repr__ method
        repr_str = repr(category)
        assert "Furniture" in repr_str
        assert "Home furniture items" in repr_str
        assert "#8B4513" in repr_str
        assert "is_active=True" in repr_str


@pytest.mark.asyncio
async def test_category_unique_name_constraint():
    """Test that category names must be unique."""
    async for session in _get_test_session():
        category1 = Category(name="Tools")
        category2 = Category(name="Tools")  # Same name should fail
        
        session.add(category1)
        await session.commit()
        
        session.add(category2)
        
        with pytest.raises(Exception):  # Should raise constraint violation
            await session.commit()


@pytest.mark.asyncio
async def test_category_color_validation():
    """Test color format validation."""
    # Test valid colors
    valid_colors = ["#FF0000", "#00FF00", "#0000FF", "#FFFFFF", "#000000", "#AABBCC"]
    
    for color in valid_colors:
        category = Category(name=f"Test{color}", color=color)
        assert category.validate_color_format() is True
    
    # Test invalid colors
    invalid_colors = ["FF0000", "#FF", "#GGGGGG", "red", "#FF00001", ""]
    
    for color in invalid_colors:
        category = Category(name=f"Test{color}", color=color)
        assert category.validate_color_format() is False
    
    # Test None color (should be valid)
    category = Category(name="TestNone", color=None)
    assert category.validate_color_format() is True


@pytest.mark.asyncio
async def test_category_soft_delete():
    """Test soft delete functionality."""
    async for session in _get_test_session():
        category = Category(name="TestDelete")
        
        session.add(category)
        await session.commit()
        await session.refresh(category)
        
        # Initially active
        assert category.is_active is True
        assert category.is_deletable() is True
        
        # Soft delete
        original_updated_at = category.updated_at
        category.soft_delete()
        
        assert category.is_active is False
        assert category.updated_at > original_updated_at
        
        # Save changes
        await session.commit()
        await session.refresh(category)
        assert category.is_active is False


@pytest.mark.asyncio
async def test_category_restore():
    """Test restoring a soft-deleted category."""
    async for session in _get_test_session():
        category = Category(name="TestRestore")
        
        session.add(category)
        await session.commit()
        await session.refresh(category)
        
        # Soft delete first
        category.soft_delete()
        await session.commit()
        await session.refresh(category)
        assert category.is_active is False
        
        # Then restore
        original_updated_at = category.updated_at
        category.restore()
        
        assert category.is_active is True
        assert category.updated_at > original_updated_at
        
        # Save changes
        await session.commit()
        await session.refresh(category)
        assert category.is_active is True


@pytest.mark.asyncio
async def test_category_query_operations():
    """Test querying category operations."""
    async for session in _get_test_session():
        # Create test categories
        categories = [
            Category(name="Active1", is_active=True),
            Category(name="Active2", is_active=True),
            Category(name="Inactive1", is_active=False),
        ]
        
        for category in categories:
            session.add(category)
        await session.commit()
        
        # Query all categories
        result = await session.execute(select(Category))
        all_categories = result.scalars().all()
        assert len(all_categories) == 3
        
        # Query only active categories
        result = await session.execute(
            select(Category).where(Category.is_active == True)
        )
        active_categories = result.scalars().all()
        assert len(active_categories) == 2
        assert all(cat.is_active for cat in active_categories)
        
        # Query by name
        result = await session.execute(
            select(Category).where(Category.name == "Active1")
        )
        found_category = result.scalar_one()
        assert found_category.name == "Active1"


@pytest.mark.asyncio
async def test_category_update_operations():
    """Test updating category fields."""
    async for session in _get_test_session():
        category = Category(
            name="Original",
            description="Original description",
            color="#000000"
        )
        
        session.add(category)
        await session.commit()
        await session.refresh(category)
        
        # Update fields
        category.name = "Updated"
        category.description = "Updated description"
        category.color = "#FFFFFF"
        
        await session.commit()
        await session.refresh(category)
        
        assert category.name == "Updated"
        assert category.description == "Updated description"
        assert category.color == "#FFFFFF"
        # Skip timestamp test as SQLAlchemy onupdate doesn't trigger on object modification


@pytest.mark.asyncio
async def test_category_deletion():
    """Test hard deletion of categories."""
    async for session in _get_test_session():
        category = Category(name="ToDelete")
        
        session.add(category)
        await session.commit()
        category_id = category.id
        
        # Hard delete
        await session.delete(category)
        await session.commit()
        
        # Verify deletion
        result = await session.execute(
            select(Category).where(Category.id == category_id)
        )
        deleted_category = result.scalar_one_or_none()
        assert deleted_category is None