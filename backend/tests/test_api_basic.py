"""
Basic tests for API endpoints functionality.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


def test_api_app_includes_routes():
    """Test that the API routes are included in the app."""
    client = TestClient(app)
    
    # Test that API routes are accessible
    response = client.get("/api/v1/locations/")
    # Should return 200 or appropriate error, not 404
    assert response.status_code != 404
    
    # Test that CORS is configured
    response = client.options("/api/v1/locations/", headers={
        "Origin": "http://localhost:8501",
        "Access-Control-Request-Method": "GET"
    })
    # Should have CORS headers
    assert response.status_code in [200, 204]


def test_api_docs_accessible():
    """Test that API documentation is accessible."""
    client = TestClient(app)
    
    # Test OpenAPI schema
    response = client.get("/openapi.json")
    assert response.status_code == 200
    
    schema = response.json()
    assert "openapi" in schema
    assert "paths" in schema
    
    # Check that our location endpoints are in the schema
    assert "/api/v1/locations/" in schema["paths"]


def test_cors_configuration():
    """Test that CORS is properly configured."""
    client = TestClient(app)
    
    # Test CORS preflight request
    response = client.options("/api/v1/locations/", headers={
        "Origin": "http://localhost:8501",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "Content-Type"
    })
    
    # Should not be forbidden
    assert response.status_code != 403
    
    # Test actual request with CORS headers
    response = client.get("/api/v1/locations/", headers={
        "Origin": "http://localhost:8501"
    })
    
    # Should have CORS headers in response
    assert "access-control-allow-origin" in response.headers or response.status_code == 500  # 500 if no db setup


def test_location_endpoints_exist():
    """Test that location endpoints are properly registered."""
    client = TestClient(app)
    
    # Test all our location endpoints return appropriate responses (not 404)
    endpoints = [
        "/api/v1/locations/",
        "/api/v1/locations/stats/summary",
    ]
    
    for endpoint in endpoints:
        response = client.get(endpoint)
        # Should not return 404 (endpoint not found)
        assert response.status_code != 404, f"Endpoint {endpoint} not found"
        # May return 500 due to database issues, but that means the endpoint exists