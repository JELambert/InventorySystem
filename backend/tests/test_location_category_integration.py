"""
Comprehensive tests for Location-Category integration.

Tests the relationship between Location and Category models,
API endpoints for category assignment, and validation logic.
"""

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.location import Location
from app.models.category import Category
from app.database.base import get_async_session, create_tables, drop_tables


@pytest.fixture(scope="function")
async def setup_database():
    """Set up test database."""
    await create_tables()
    yield
    await drop_tables()


@pytest.fixture
async def client():
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        await create_tables()
        yield client
        await drop_tables()


@pytest.fixture
async def async_session():
    """Create async session for database tests."""
    await create_tables()
    
    session_gen = get_async_session()
    session = await session_gen.__anext__()
    
    try:
        yield session
    finally:
        await session.close()
        await drop_tables()


class TestLocationCategoryIntegration:
    """Test Location-Category relationship and integration."""

    @pytest.fixture
    async def test_category(self, async_session: AsyncSession) -> Category:
        """Create a test category."""
        category = Category(
            name="Test Electronics",
            description="Electronics and gadgets for testing",
            color="#0056B3"
        )
        async_session.add(category)
        await async_session.commit()
        await async_session.refresh(category)
        return category

    @pytest.fixture
    async def test_location_with_category(
        self, 
        async_session: AsyncSession, 
        test_category: Category
    ) -> Location:
        """Create a test location with category assignment."""
        location = Location(
            name="Tech Office",
            description="Office with electronic equipment",
            location_type="room",
            category_id=test_category.id
        )
        async_session.add(location)
        await async_session.commit()
        await async_session.refresh(location)
        return location

    @pytest.mark.asyncio
    async def test_location_category_relationship(
        self, 
        async_session: AsyncSession, 
        test_location_with_category: Location,
        test_category: Category
    ):
        """Test that Location-Category relationship works correctly."""
        # Verify the relationship is established
        assert test_location_with_category.category_id == test_category.id
        
        # Test loading the relationship
        result = await async_session.execute(
            select(Location)
            .where(Location.id == test_location_with_category.id)
        )
        location = result.scalar_one()
        assert location.category_id == test_category.id

    async def test_location_without_category(self, async_session: AsyncSession):
        """Test creating location without category (category_id = None)."""
        location = Location(
            name="Basic Room",
            description="Room without category assignment",
            location_type="room",
            category_id=None
        )
        async_session.add(location)
        await async_session.commit()
        await async_session.refresh(location)
        
        assert location.category_id is None

    async def test_multiple_locations_same_category(
        self, 
        async_session: AsyncSession, 
        test_category: Category
    ):
        """Test multiple locations can share the same category."""
        locations = []
        for i in range(3):
            location = Location(
                name=f"Electronic Device {i+1}",
                description=f"Device {i+1} with electronics category",
                location_type="container",
                category_id=test_category.id
            )
            locations.append(location)
            async_session.add(location)
        
        await async_session.commit()
        
        # Verify all locations have the same category
        for location in locations:
            await async_session.refresh(location)
            assert location.category_id == test_category.id

    async def test_category_deletion_handling(
        self, 
        async_session: AsyncSession, 
        test_location_with_category: Location,
        test_category: Category
    ):
        """Test what happens when a category is deleted."""
        # Note: This test depends on the FK constraint behavior
        # Currently, we don't have CASCADE DELETE, so this should fail
        # if we try to delete a category that's referenced by locations
        
        # First verify the location exists with category
        assert test_location_with_category.category_id == test_category.id
        
        # Try to delete the category (should be blocked by FK constraint)
        with pytest.raises(Exception):  # Should raise FK constraint violation
            await async_session.delete(test_category)
            await async_session.commit()


class TestLocationCategoryAPI:
    """Test API endpoints for Location-Category integration."""

    @pytest.fixture
    async def test_category_via_api(self, client: AsyncClient) -> dict:
        """Create a test category via API."""
        category_data = {
            "name": "API Test Category",
            "description": "Category created via API for testing",
            "color": "#FF5722"
        }
        
        response = await client.post("/api/v1/categories/", json=category_data)
        assert response.status_code == 201
        return response.json()

    async def test_create_location_with_category(
        self, 
        client: AsyncClient, 
        test_category_via_api: dict
    ):
        """Test creating location with category via API."""
        location_data = {
            "name": "API Tech Room",
            "description": "Room created via API with category",
            "location_type": "room",
            "parent_id": None,
            "category_id": test_category_via_api["id"]
        }
        
        response = await client.post("/api/v1/locations/", json=location_data)
        assert response.status_code == 201
        
        result = response.json()
        assert result["category_id"] == test_category_via_api["id"]
        assert result["name"] == location_data["name"]

    async def test_create_location_without_category(self, client: AsyncClient):
        """Test creating location without category via API."""
        location_data = {
            "name": "No Category Room",
            "description": "Room without category assignment",
            "location_type": "room",
            "parent_id": None,
            "category_id": None
        }
        
        response = await client.post("/api/v1/locations/", json=location_data)
        assert response.status_code == 201
        
        result = response.json()
        assert result["category_id"] is None
        assert result["name"] == location_data["name"]

    async def test_update_location_category(
        self, 
        client: AsyncClient, 
        test_category_via_api: dict
    ):
        """Test updating location's category via API."""
        # First create a location without category
        location_data = {
            "name": "Update Test Room",
            "description": "Room for category update testing",
            "location_type": "room",
            "parent_id": None,
            "category_id": None
        }
        
        response = await client.post("/api/v1/locations/", json=location_data)
        assert response.status_code == 201
        location = response.json()
        assert location["category_id"] is None
        
        # Update to assign category
        update_data = {
            "category_id": test_category_via_api["id"]
        }
        
        response = await client.put(
            f"/api/v1/locations/{location['id']}", 
            json=update_data
        )
        assert response.status_code == 200
        
        updated_location = response.json()
        assert updated_location["category_id"] == test_category_via_api["id"]

    async def test_remove_location_category(
        self, 
        client: AsyncClient, 
        test_category_via_api: dict
    ):
        """Test removing category from location via API."""
        # Create location with category
        location_data = {
            "name": "Remove Category Room",
            "description": "Room for category removal testing",
            "location_type": "room",
            "parent_id": None,
            "category_id": test_category_via_api["id"]
        }
        
        response = await client.post("/api/v1/locations/", json=location_data)
        assert response.status_code == 201
        location = response.json()
        assert location["category_id"] == test_category_via_api["id"]
        
        # Remove category (set to null)
        update_data = {
            "category_id": None
        }
        
        response = await client.put(
            f"/api/v1/locations/{location['id']}", 
            json=update_data
        )
        assert response.status_code == 200
        
        updated_location = response.json()
        assert updated_location["category_id"] is None

    async def test_invalid_category_id(self, client: AsyncClient):
        """Test creating location with non-existent category ID."""
        location_data = {
            "name": "Invalid Category Room",
            "description": "Room with invalid category",
            "location_type": "room",
            "parent_id": None,
            "category_id": 99999  # Non-existent category
        }
        
        response = await client.post("/api/v1/locations/", json=location_data)
        assert response.status_code == 400
        assert "Category not found" in response.json()["detail"]

    async def test_update_with_invalid_category_id(self, client: AsyncClient):
        """Test updating location with non-existent category ID."""
        # Create location first
        location_data = {
            "name": "Update Invalid Category Room",
            "description": "Room for invalid category update testing",
            "location_type": "room",
            "parent_id": None,
            "category_id": None
        }
        
        response = await client.post("/api/v1/locations/", json=location_data)
        assert response.status_code == 201
        location = response.json()
        
        # Try to update with invalid category
        update_data = {
            "category_id": 99999  # Non-existent category
        }
        
        response = await client.put(
            f"/api/v1/locations/{location['id']}", 
            json=update_data
        )
        assert response.status_code == 400
        assert "New category not found" in response.json()["detail"]

    async def test_get_location_with_category(
        self, 
        client: AsyncClient, 
        test_category_via_api: dict
    ):
        """Test retrieving location includes category information."""
        # Create location with category
        location_data = {
            "name": "Get Test Room",
            "description": "Room for get testing with category",
            "location_type": "room",
            "parent_id": None,
            "category_id": test_category_via_api["id"]
        }
        
        response = await client.post("/api/v1/locations/", json=location_data)
        assert response.status_code == 201
        location = response.json()
        
        # Retrieve the location
        response = await client.get(f"/api/v1/locations/{location['id']}")
        assert response.status_code == 200
        
        retrieved_location = response.json()
        assert retrieved_location["category_id"] == test_category_via_api["id"]
        assert retrieved_location["name"] == location_data["name"]


class TestLocationCategoryValidation:
    """Test validation logic for Location-Category integration."""

    async def test_category_id_validation_in_schema(self, client: AsyncClient):
        """Test that category_id validation works in Pydantic schemas."""
        # Test with invalid data types
        invalid_data = {
            "name": "Invalid Data Room",
            "description": "Room with invalid category_id type",
            "location_type": "room", 
            "parent_id": None,
            "category_id": "not_an_integer"  # Invalid type
        }
        
        response = await client.post("/api/v1/locations/", json=invalid_data)
        assert response.status_code == 422  # Validation error

    async def test_category_id_optional_in_create(self, client: AsyncClient):
        """Test that category_id is optional during location creation."""
        location_data = {
            "name": "Optional Category Room",
            "description": "Room without category_id field",
            "location_type": "room",
            "parent_id": None
            # category_id is omitted
        }
        
        response = await client.post("/api/v1/locations/", json=location_data)
        assert response.status_code == 201
        
        result = response.json()
        assert result["category_id"] is None

    async def test_category_id_optional_in_update(self, client: AsyncClient):
        """Test that category_id is optional during location updates."""
        # Create location first
        location_data = {
            "name": "Optional Update Room",
            "description": "Room for optional update testing",
            "location_type": "room",
            "parent_id": None,
            "category_id": None
        }
        
        response = await client.post("/api/v1/locations/", json=location_data)
        assert response.status_code == 201
        location = response.json()
        
        # Update without specifying category_id
        update_data = {
            "description": "Updated description without category change"
        }
        
        response = await client.put(
            f"/api/v1/locations/{location['id']}", 
            json=update_data
        )
        assert response.status_code == 200
        
        updated_location = response.json()
        assert updated_location["category_id"] is None  # Should remain unchanged
        assert updated_location["description"] == update_data["description"]


class TestLocationCategoryPerformance:
    """Test performance aspects of Location-Category integration."""

    async def test_bulk_location_creation_with_categories(
        self, 
        client: AsyncClient, 
        test_category_via_api: dict
    ):
        """Test creating multiple locations with categories efficiently."""
        locations_created = []
        
        # Create 10 locations with the same category
        for i in range(10):
            location_data = {
                "name": f"Bulk Location {i+1}",
                "description": f"Bulk created location {i+1}",
                "location_type": "container",
                "parent_id": None,
                "category_id": test_category_via_api["id"]
            }
            
            response = await client.post("/api/v1/locations/", json=location_data)
            assert response.status_code == 201
            locations_created.append(response.json())
        
        # Verify all locations were created with correct category
        assert len(locations_created) == 10
        for location in locations_created:
            assert location["category_id"] == test_category_via_api["id"]

    async def test_location_listing_with_categories(
        self, 
        client: AsyncClient, 
        test_category_via_api: dict
    ):
        """Test that location listing includes category information."""
        # Create a few locations with categories
        for i in range(3):
            location_data = {
                "name": f"List Test Location {i+1}",
                "description": f"Location {i+1} for listing test",
                "location_type": "room",
                "parent_id": None,
                "category_id": test_category_via_api["id"]
            }
            
            response = await client.post("/api/v1/locations/", json=location_data)
            assert response.status_code == 201
        
        # Get locations list
        response = await client.get("/api/v1/locations/")
        assert response.status_code == 200
        
        locations = response.json()
        
        # Find our test locations
        test_locations = [
            loc for loc in locations 
            if loc["name"].startswith("List Test Location")
        ]
        
        assert len(test_locations) >= 3
        for location in test_locations:
            assert location["category_id"] == test_category_via_api["id"]