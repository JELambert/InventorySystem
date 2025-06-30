"""
Tests for Location API endpoints.
"""

import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.database.base import create_tables, drop_tables, get_async_session
from app.models.location import Location, LocationType


@pytest.fixture(scope="function")
async def setup_database():
    """Set up test database."""
    await create_tables()
    yield
    await drop_tables()


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
async def sample_locations():
    """Create sample locations for testing."""
    # Ensure tables exist
    await create_tables()
    
    session_gen = get_async_session()
    session = await session_gen.__anext__()
    
    try:
        # Create house
        house = Location(
            name="Test House",
            location_type=LocationType.HOUSE,
            description="A test house"
        )
        session.add(house)
        await session.commit()
        await session.refresh(house)
        
        # Create room
        room = Location(
            name="Living Room",
            location_type=LocationType.ROOM,
            parent_id=house.id,
            description="Main living area"
        )
        session.add(room)
        await session.commit()
        await session.refresh(room)
        
        # Create container
        container = Location(
            name="Bookshelf",
            location_type=LocationType.CONTAINER,
            parent_id=room.id,
            description="Wooden bookshelf"
        )
        session.add(container)
        await session.commit()
        await session.refresh(container)
        
        yield {"house": house, "room": room, "container": container}
    
    finally:
        await session.close()
        await drop_tables()


class TestLocationAPI:
    """Test Location API endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_locations(self, client, sample_locations):
        """Test getting all locations."""
        response = client.get("/api/v1/locations/")
        assert response.status_code == 200
        
        locations = response.json()
        assert len(locations) == 3
        assert all("id" in loc for loc in locations)
        assert all("name" in loc for loc in locations)
        assert all("full_path" in loc for loc in locations)
    
    def test_get_locations_with_filters(self, client, sample_locations):
        """Test getting locations with filters."""
        # Filter by type
        response = client.get("/api/v1/locations/?location_type=HOUSE")
        assert response.status_code == 200
        
        locations = response.json()
        assert len(locations) == 1
        assert locations[0]["location_type"] == "HOUSE"
        
        # Filter by parent
        house_id = sample_locations["house"].id
        response = client.get(f"/api/v1/locations/?parent_id={house_id}")
        assert response.status_code == 200
        
        locations = response.json()
        assert len(locations) == 1
        assert locations[0]["location_type"] == "ROOM"
    
    def test_get_location_by_id(self, client, sample_locations):
        """Test getting a specific location."""
        house_id = sample_locations["house"].id
        response = client.get(f"/api/v1/locations/{house_id}")
        assert response.status_code == 200
        
        location = response.json()
        assert location["id"] == house_id
        assert location["name"] == "Test House"
        assert location["location_type"] == "HOUSE"
        assert location["full_path"] == "Test House"
    
    def test_get_location_not_found(self, client, sample_locations):
        """Test getting non-existent location."""
        response = client.get("/api/v1/locations/999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_get_location_children(self, client, sample_locations):
        """Test getting location children."""
        house_id = sample_locations["house"].id
        response = client.get(f"/api/v1/locations/{house_id}/children")
        assert response.status_code == 200
        
        children = response.json()
        assert len(children) == 1
        assert children[0]["name"] == "Living Room"
        assert children[0]["parent_id"] == house_id
    
    def test_get_location_tree(self, client, sample_locations):
        """Test getting location tree."""
        house_id = sample_locations["house"].id
        response = client.get(f"/api/v1/locations/{house_id}/tree")
        assert response.status_code == 200
        
        tree = response.json()
        assert tree["location"]["name"] == "Test House"
        assert len(tree["children"]) == 1
        
        room_tree = tree["children"][0]
        assert room_tree["location"]["name"] == "Living Room"
        assert len(room_tree["children"]) == 1
        
        container_tree = room_tree["children"][0]
        assert container_tree["location"]["name"] == "Bookshelf"
    
    def test_create_location(self, client, setup_database):
        """Test creating a new location."""
        location_data = {
            "name": "New House",
            "description": "A newly created house",
            "location_type": "HOUSE",
            "parent_id": None
        }
        
        response = client.post("/api/v1/locations/", json=location_data)
        assert response.status_code == 201
        
        location = response.json()
        assert location["name"] == "New House"
        assert location["location_type"] == "HOUSE"
        assert location["parent_id"] is None
        assert "id" in location
        assert "created_at" in location
    
    def test_create_location_with_parent(self, client, sample_locations):
        """Test creating location with parent."""
        house_id = sample_locations["house"].id
        location_data = {
            "name": "Kitchen",
            "description": "Kitchen area",
            "location_type": "ROOM",
            "parent_id": house_id
        }
        
        response = client.post("/api/v1/locations/", json=location_data)
        assert response.status_code == 201
        
        location = response.json()
        assert location["name"] == "Kitchen"
        assert location["parent_id"] == house_id
        assert "Test House/Kitchen" in location["full_path"]
    
    def test_create_location_invalid_parent(self, client, setup_database):
        """Test creating location with invalid parent."""
        location_data = {
            "name": "Invalid Room",
            "location_type": "ROOM",
            "parent_id": 999
        }
        
        response = client.post("/api/v1/locations/", json=location_data)
        assert response.status_code == 400
        assert "Parent location not found" in response.json()["detail"]
    
    def test_update_location(self, client, sample_locations):
        """Test updating a location."""
        room_id = sample_locations["room"].id
        update_data = {
            "name": "Updated Living Room",
            "description": "Updated description"
        }
        
        response = client.put(f"/api/v1/locations/{room_id}", json=update_data)
        assert response.status_code == 200
        
        location = response.json()
        assert location["name"] == "Updated Living Room"
        assert location["description"] == "Updated description"
        assert location["id"] == room_id
    
    def test_update_location_not_found(self, client, setup_database):
        """Test updating non-existent location."""
        update_data = {"name": "Not Found"}
        
        response = client.put("/api/v1/locations/999", json=update_data)
        assert response.status_code == 404
    
    def test_delete_location(self, client, sample_locations):
        """Test deleting a location."""
        container_id = sample_locations["container"].id
        
        response = client.delete(f"/api/v1/locations/{container_id}")
        assert response.status_code == 204
        
        # Verify location is deleted
        response = client.get(f"/api/v1/locations/{container_id}")
        assert response.status_code == 404
    
    def test_delete_location_with_children(self, client, sample_locations):
        """Test deleting location with children (cascade delete)."""
        house_id = sample_locations["house"].id
        
        response = client.delete(f"/api/v1/locations/{house_id}")
        assert response.status_code == 204
        
        # Verify all descendants are deleted
        response = client.get("/api/v1/locations/")
        locations = response.json()
        assert len(locations) == 0
    
    def test_search_locations(self, client, sample_locations):
        """Test searching locations."""
        search_data = {
            "pattern": "living",
            "location_type": "ROOM"
        }
        
        response = client.post("/api/v1/locations/search", json=search_data)
        assert response.status_code == 200
        
        locations = response.json()
        assert len(locations) == 1
        assert locations[0]["name"] == "Living Room"
    
    def test_validate_location(self, client, sample_locations):
        """Test location validation."""
        room_id = sample_locations["room"].id
        
        response = client.post(f"/api/v1/locations/{room_id}/validate")
        assert response.status_code == 200
        
        validation = response.json()
        assert validation["is_valid"] is True
        assert len(validation["errors"]) == 0
    
    def test_location_stats(self, client, sample_locations):
        """Test location statistics."""
        response = client.get("/api/v1/locations/stats/summary")
        assert response.status_code == 200
        
        stats = response.json()
        assert stats["total_locations"] == 3
        assert stats["by_type"]["HOUSE"] == 1
        assert stats["by_type"]["ROOM"] == 1
        assert stats["by_type"]["CONTAINER"] == 1
        assert stats["root_locations"] == 1