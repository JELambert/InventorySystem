# 📚 API Reference

Complete API documentation for the Home Inventory Management System.

**Base URL**: `http://localhost:8000/api/v1`  
**Documentation**: `http://localhost:8000/docs` (Swagger UI)

## Authentication

Currently, the API does not require authentication. This will be added in Phase 3.

## Common Response Formats

### Success Response
```json
{
  "id": 1,
  "name": "Example Item",
  "created_at": "2025-07-03T10:00:00Z",
  "updated_at": "2025-07-03T10:00:00Z"
}
```

### Error Response
```json
{
  "detail": "Error message here"
}
```

### Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## Endpoints by Category

### 📦 Items API

#### List Items
```http
GET /items/
```

Query Parameters:
- `skip` (int): Number of items to skip (default: 0)
- `limit` (int): Maximum items to return (default: 100)
- `search` (str): Search in name, description, brand, model
- `item_type` (str): Filter by type (electronics, books, etc.)
- `status` (str): Filter by status (available, in_use, etc.)
- `condition` (str): Filter by condition
- `category_id` (int): Filter by category
- `min_value` (float): Minimum current value
- `max_value` (float): Maximum current value

Example:
```bash
curl "http://localhost:8000/api/v1/items/?search=laptop&status=available"
```

#### Create Item
```http
POST /items/
```

Request Body:
```json
{
  "name": "MacBook Pro",
  "description": "16-inch laptop",
  "item_type": "electronics",
  "condition": "excellent",
  "status": "available",
  "brand": "Apple",
  "model": "A2141",
  "purchase_price": 2399.00,
  "current_value": 1800.00,
  "category_id": 1
}
```

#### Create Item with Location
```http
POST /items/with-location
```

Request Body:
```json
{
  "name": "Wireless Mouse",
  "item_type": "electronics",
  "location_id": 5,
  "quantity": 1
}
```

#### Update Item
```http
PUT /items/{item_id}
```

#### Delete Item
```http
DELETE /items/{item_id}
```

Query Parameters:
- `permanent` (bool): Permanently delete (default: false - soft delete)

#### Item Statistics
```http
GET /items/statistics/overview
```

Returns comprehensive statistics about items by type, condition, status, and value.

### 📍 Locations API

#### List Locations
```http
GET /locations/
```

Query Parameters:
- `skip`, `limit`: Pagination
- `search`: Search in name and description
- `location_type`: Filter by type (house, room, container, shelf)
- `parent_id`: Filter by parent location

#### Create Location
```http
POST /locations/
```

Request Body:
```json
{
  "name": "Master Bedroom",
  "location_type": "room",
  "description": "Main bedroom upstairs",
  "parent_id": 1,
  "category_id": 2
}
```

#### Get Location Tree
```http
GET /locations/tree
```

Returns hierarchical tree structure of all locations.

#### Get Location Children
```http
GET /locations/{location_id}/children
```

### 🏷️ Categories API

#### List Categories
```http
GET /categories/
```

Query Parameters:
- `skip`, `limit`: Pagination
- `search`: Search in name and description
- `include_inactive`: Include soft-deleted categories

#### Create Category
```http
POST /categories/
```

Request Body:
```json
{
  "name": "Electronics",
  "description": "Electronic devices and accessories",
  "color": "#4287f5"
}
```

### 📊 Inventory API

#### List Inventory Entries
```http
GET /inventory/
```

Query Parameters:
- `item_id`: Filter by item
- `location_id`: Filter by location
- `min_quantity`, `max_quantity`: Quantity range

#### Create Inventory Entry
```http
POST /inventory/
```

Request Body:
```json
{
  "item_id": 1,
  "location_id": 5,
  "quantity": 2
}
```

#### Move Items
```http
POST /inventory/move/{item_id}
```

Request Body:
```json
{
  "to_location_id": 8,
  "quantity": 1,
  "notes": "Moved to office"
}
```

#### Get Inventory Summary
```http
GET /inventory/summary
```

Returns overall inventory statistics and summaries.

### 🔍 Search API (Semantic)

#### Semantic Search
```http
POST /search/semantic
```

Request Body:
```json
{
  "query": "blue electronics in garage",
  "limit": 50,
  "certainty": 0.7,
  "filters": {
    "item_types": ["electronics"],
    "status": "available",
    "min_value": 0,
    "max_value": 1000
  }
}
```

Response:
```json
{
  "results": [
    {
      "item": { /* full item object */ },
      "score": 0.89,
      "match_type": "semantic"
    }
  ],
  "total_results": 15,
  "search_type": "semantic",
  "semantic_enabled": true,
  "search_time_ms": 123
}
```

#### Find Similar Items
```http
GET /search/similar/{item_id}
```

Query Parameters:
- `limit` (int): Maximum similar items to return (default: 5)

#### Check Search Health
```http
GET /search/health
```

Returns Weaviate service status and availability.

#### Sync Items to Weaviate
```http
POST /search/sync-to-weaviate
```

Request Body:
```json
{
  "item_ids": [1, 2, 3],
  "batch_size": 50
}
```

### 🚀 Performance API

#### Get Performance Metrics
```http
GET /performance/metrics
```

Returns API performance statistics.

#### Query Analysis
```http
GET /performance/query-analysis
```

Returns slow query analysis and optimization suggestions.

## Status Codes

- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `204 No Content`: Successful deletion
- `400 Bad Request`: Invalid request data
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict (e.g., duplicate)
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

## Data Types and Enums

### Item Types
- `electronics`
- `furniture`
- `clothing`
- `books`
- `documents`
- `tools`
- `kitchen`
- `decor`
- `collectibles`
- `hobby`
- `office`
- `personal`
- `seasonal`
- `storage`
- `other`

### Item Conditions
- `excellent`
- `very_good`
- `good`
- `fair`
- `poor`
- `for_repair`
- `not_working`

### Item Status
- `available`
- `in_use`
- `reserved`
- `loaned`
- `missing`
- `disposed`
- `sold`

### Location Types
- `house`
- `room`
- `container`
- `shelf`

## Pagination

Most list endpoints support pagination:
```
GET /items/?skip=20&limit=10
```

Response includes items 21-30.

## Filtering

Combine multiple filters:
```
GET /items/?item_type=electronics&status=available&min_value=100
```

## Search

Text search is case-insensitive and searches multiple fields:
```
GET /items/?search=laptop
```

Searches in: name, description, brand, model, serial number, notes, tags

## Error Handling

### Common Errors

#### Validation Error (422)
```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

#### Not Found (404)
```json
{
  "detail": "Item not found"
}
```

#### Duplicate Resource (409)
```json
{
  "detail": "Item with serial number ABC123 already exists"
}
```

## Rate Limiting

Currently no rate limiting is implemented. This will be added in production deployment.

## Webhooks

Webhook support is planned for Phase 3 to notify external systems of inventory changes.

## SDK Examples

### Python
```python
import requests

# Get all items
response = requests.get("http://localhost:8000/api/v1/items/")
items = response.json()

# Create item
new_item = {
    "name": "Test Item",
    "item_type": "other",
    "status": "available"
}
response = requests.post(
    "http://localhost:8000/api/v1/items/",
    json=new_item
)
```

### JavaScript
```javascript
// Get all items
fetch('http://localhost:8000/api/v1/items/')
  .then(response => response.json())
  .then(items => console.log(items));

// Create item
fetch('http://localhost:8000/api/v1/items/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    name: 'Test Item',
    item_type: 'other',
    status: 'available'
  })
});
```

## Health Check

```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "weaviate": "connected"
  }
}
```