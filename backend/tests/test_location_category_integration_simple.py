"""
Essential Location-Category integration tests.

Tests the most critical aspects of the Location-Category relationship.
"""

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

from app.main import app
from app.database.base import create_tables, drop_tables


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.mark.asyncio
async def test_create_location_with_category():
    """Test creating location with category via API."""
    # Setup database
    await create_tables()
    
    try:
        client = TestClient(app)
        
        # First create a category
        category_data = {
            "name": "Test Electronics",
            "description": "Electronics for testing",
            "color": "#0056B3"
        }
        
        response = client.post("/api/v1/categories/", json=category_data)
        assert response.status_code == 201
        category = response.json()
        
        # Create location with category
        location_data = {
            "name": "Tech Room",
            "description": "Room with electronics",
            "location_type": "room",
            "parent_id": None,
            "category_id": category["id"]
        }
        
        response = client.post("/api/v1/locations/", json=location_data)
        assert response.status_code == 201
        
        location = response.json()
        assert location["category_id"] == category["id"]
        assert location["name"] == "Tech Room"
        
    finally:
        await drop_tables()


@pytest.mark.asyncio 
async def test_create_location_without_category():
    """Test creating location without category via API."""
    await create_tables()
    
    try:
        client = TestClient(app)
        
        location_data = {
            "name": "Basic Room",
            "description": "Room without category",
            "location_type": "room",
            "parent_id": None,
            "category_id": None
        }
        
        response = client.post("/api/v1/locations/", json=location_data)
        assert response.status_code == 201
        
        location = response.json()
        assert location["category_id"] is None
        assert location["name"] == "Basic Room"
        
    finally:
        await drop_tables()


@pytest.mark.asyncio
async def test_update_location_category():
    """Test updating location's category via API."""
    await create_tables()
    
    try:
        client = TestClient(app)
        
        # Create category
        category_data = {
            "name": "Update Test Category",
            "description": "Category for update testing",
            "color": "#FF5722"
        }
        
        response = client.post("/api/v1/categories/", json=category_data)
        assert response.status_code == 201
        category = response.json()
        
        # Create location without category
        location_data = {
            "name": "Update Test Room",
            "description": "Room for category update testing",
            "location_type": "room",
            "parent_id": None,
            "category_id": None
        }
        
        response = client.post("/api/v1/locations/", json=location_data)
        assert response.status_code == 201
        location = response.json()
        assert location["category_id"] is None
        
        # Update to assign category
        update_data = {
            "category_id": category["id"]
        }
        
        response = client.put(f"/api/v1/locations/{location['id']}", json=update_data)
        assert response.status_code == 200
        
        updated_location = response.json()
        assert updated_location["category_id"] == category["id"]
        
    finally:
        await drop_tables()


@pytest.mark.asyncio
async def test_invalid_category_id():
    """Test creating location with non-existent category ID."""
    await create_tables()
    
    try:
        client = TestClient(app)
        
        location_data = {
            "name": "Invalid Category Room",
            "description": "Room with invalid category",
            "location_type": "room", 
            "parent_id": None,
            "category_id": 99999  # Non-existent category
        }
        
        response = client.post("/api/v1/locations/", json=location_data)
        assert response.status_code == 400
        assert "Category not found" in response.json()["detail"]
        
    finally:
        await drop_tables()


@pytest.mark.asyncio
async def test_remove_location_category():
    """Test removing category from location via API."""
    await create_tables()
    
    try:
        client = TestClient(app)
        
        # Create category
        category_data = {
            "name": "Remove Test Category",
            "description": "Category for removal testing",
            "color": "#9C27B0"
        }
        
        response = client.post("/api/v1/categories/", json=category_data)
        assert response.status_code == 201
        category = response.json()
        
        # Create location with category
        location_data = {
            "name": "Remove Category Room",
            "description": "Room for category removal testing",
            "location_type": "room",
            "parent_id": None,
            "category_id": category["id"]
        }
        
        response = client.post("/api/v1/locations/", json=location_data)
        assert response.status_code == 201
        location = response.json()
        assert location["category_id"] == category["id"]
        
        # Remove category (set to null)
        update_data = {
            "category_id": None
        }
        
        response = client.put(f"/api/v1/locations/{location['id']}", json=update_data)
        assert response.status_code == 200
        
        updated_location = response.json()
        assert updated_location["category_id"] is None
        
    finally:
        await drop_tables()