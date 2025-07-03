# 🧪 Testing Guide

Comprehensive testing documentation for the Home Inventory System.

## Table of Contents
- [Overview](#overview)
- [Quick Start](#quick-start)
- [Test Architecture](#test-architecture)
- [Backend Testing](#backend-testing)
- [Frontend Testing](#frontend-testing)
- [Service Layer Tests](#service-layer-tests)
- [Test Database Setup](#test-database-setup)
- [Coverage Reports](#coverage-reports)
- [Continuous Integration](#continuous-integration)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Overview

The Home Inventory System uses a comprehensive testing strategy:

- **Unit Tests**: Individual component testing with mocking
- **Integration Tests**: Database and API integration testing
- **Service Tests**: Business logic and external service testing
- **End-to-End Tests**: Complete user workflows
- **Performance Tests**: Load testing and optimization verification

### Current Test Coverage
- **Backend**: 75+ API endpoints, 100+ unit tests
- **Frontend**: Component tests, error boundary tests
- **Services**: Weaviate, Item, Movement service tests
- **Models**: Complete model validation tests

## Quick Start

### Run All Tests
```bash
# Backend tests (recommended method)
cd backend
python run_tests.py

# Frontend tests
cd frontend
python run_frontend_tests.py
```

### Run Specific Test Categories
```bash
# API tests
python run_tests.py tests/test_api_items_comprehensive.py -v

# Service tests
python run_tests.py tests/test_item_service.py -v

# Model tests
python run_tests.py tests/test_item_model.py -v
```

### Run with Coverage
```bash
# Generate coverage report
python run_tests.py --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Test Architecture

### Directory Structure
```
backend/tests/
├── conftest.py                 # Pytest configuration and fixtures
├── test_api_*.py              # API endpoint tests
├── test_*_model.py            # Database model tests
├── test_*_service.py          # Service layer tests
├── test_error_handler.py      # Error handling tests
└── test_performance_*.py      # Performance tests

frontend/tests/
├── test_components/           # UI component tests
├── test_error_boundaries/     # Error handling tests
└── test_utils/               # Utility function tests
```

### Test Categories

#### 1. Unit Tests
- Model validation
- Schema validation
- Utility functions
- Business logic

#### 2. Integration Tests
- Database operations
- API endpoints
- External services
- Cross-component interactions

#### 3. End-to-End Tests
- Complete workflows
- User journeys
- Multi-step operations

## Backend Testing

### API Endpoint Tests

#### Items API (`test_api_items_comprehensive.py`)
```python
# Test all CRUD operations
def test_create_item()
def test_get_item()
def test_update_item()
def test_delete_item()

# Test search functionality
def test_search_items()
def test_filter_by_type()
def test_filter_by_location()

# Test bulk operations
def test_bulk_update_items()
def test_bulk_delete_items()
```

#### Inventory API (`test_api_inventory_operations.py`)
```python
# Test movement operations
def test_move_item()
def test_adjust_quantity()
def test_transfer_between_locations()

# Test validation
def test_negative_quantity_rejected()
def test_invalid_location_rejected()
```

### Model Tests

#### Location Model (`test_location_model.py`)
```python
def test_location_creation()
def test_location_hierarchy()
def test_cascade_delete()
def test_path_generation()
def test_type_validation()
```

#### Item Model (`test_item_model.py`)
```python
def test_item_creation()
def test_enum_validation()
def test_price_validation()
def test_relationship_loading()
```

### Database Tests

#### Test Database Configuration
```python
# conftest.py
@pytest.fixture(scope="session")
def test_db():
    """Create test database for session."""
    # Uses SQLite in-memory for speed
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    # ... setup and teardown
```

#### Running Database Tests
```bash
# Test database operations
python run_tests.py tests/test_database_base.py -v

# Test migrations
poetry run alembic upgrade head
poetry run alembic downgrade -1
```

## Service Layer Tests

### Weaviate Service (`test_weaviate_service.py`)
```python
# Test vector database operations
def test_initialize_connection()
def test_create_embedding()
def test_semantic_search()
def test_similarity_search()
def test_batch_operations()
```

### Item Service (`test_item_service.py`)
```python
# Test dual-write pattern
def test_create_item_with_weaviate_sync()
def test_update_item_updates_embedding()
def test_delete_item_removes_embedding()
def test_weaviate_failure_doesnt_block()
```

### Movement Service (`test_movement_service.py`)
```python
# Test audit trail
def test_record_movement()
def test_movement_validation()
def test_bulk_movements()
def test_movement_history()
```

## Frontend Testing

### Component Tests
```bash
cd frontend
poetry run pytest tests/test_components/ -v
```

Example component test:
```python
def test_item_card_renders():
    """Test ItemCard component renders correctly."""
    item = {"id": 1, "name": "Test Item"}
    rendered = render_component(ItemCard, item=item)
    assert "Test Item" in rendered
```

### Error Boundary Tests
```python
def test_error_boundary_catches_errors():
    """Test error boundaries prevent app crashes."""
    with error_boundary():
        raise ValueError("Test error")
    # App should not crash
```

### Integration Tests
```python
def test_api_client_error_handling():
    """Test API client handles errors gracefully."""
    client = APIClient()
    response = client.get_item(999999)  # Non-existent
    assert response is None
```

## Test Database Setup

### Automatic Test Database
Tests automatically use SQLite in-memory database:
- No setup required
- Fast execution
- Isolated between tests
- Automatic cleanup

### Manual Database Testing
```bash
# Create test database
cd backend
TESTING=true python -c "
from app.database.base import create_tables
import asyncio
asyncio.run(create_tables())
"

# Run tests against test database
TESTING=true python run_tests.py
```

## Coverage Reports

### Generate Coverage Report
```bash
# Backend coverage
cd backend
python run_tests.py --cov=app --cov-report=html --cov-report=term

# View report
open htmlcov/index.html
```

### Coverage Goals
- **Target**: 80%+ overall coverage
- **Critical paths**: 95%+ coverage
- **New code**: Must include tests

### Exclude from Coverage
```python
# pragma: no cover
if TYPE_CHECKING:  # pragma: no cover
    from typing import Any
```

## Continuous Integration

### GitHub Actions Configuration
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install Poetry
        run: pip install poetry
      
      - name: Install dependencies
        run: |
          cd backend
          poetry install
      
      - name: Run tests
        run: |
          cd backend
          poetry run pytest --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: tests
        name: tests
        entry: cd backend && python run_tests.py
        language: system
        pass_filenames: false
        always_run: true
```

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# Fix: Use run_tests.py which sets PYTHONPATH
python run_tests.py

# Or set manually
PYTHONPATH=. pytest tests/
```

#### Database Errors
```bash
# Ensure test mode is active
TESTING=true python run_tests.py

# Check database URL
python -c "from app.database.config import DatabaseConfig; print(DatabaseConfig.get_database_url())"
```

#### Async Test Errors
```python
# Use pytest-asyncio
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

#### Mock Issues
```python
# Mock at correct level
with patch('app.services.weaviate_service.get_weaviate_service'):
    # Not at import level
```

### Debug Test Failures
```bash
# Run with verbose output
python run_tests.py -vv

# Run with print statements
python run_tests.py -s

# Run single test
python run_tests.py tests/test_file.py::test_function -vv
```

## Best Practices

### Test Structure
```python
# Arrange - Act - Assert pattern
def test_item_creation():
    # Arrange
    item_data = {"name": "Test Item", "type": "electronics"}
    
    # Act
    item = create_item(item_data)
    
    # Assert
    assert item.name == "Test Item"
    assert item.type == ItemType.ELECTRONICS
```

### Fixture Usage
```python
@pytest.fixture
def sample_item():
    """Reusable test item."""
    return Item(
        name="Test Item",
        item_type=ItemType.ELECTRONICS
    )

def test_with_fixture(sample_item):
    assert sample_item.name == "Test Item"
```

### Mocking External Services
```python
@pytest.fixture
def mock_weaviate():
    """Mock Weaviate service."""
    service = Mock()
    service.health_check.return_value = True
    service.create_embedding.return_value = True
    return service
```

### Parameterized Tests
```python
@pytest.mark.parametrize("status,expected", [
    (ItemStatus.AVAILABLE, True),
    (ItemStatus.SOLD, False),
    (ItemStatus.DISPOSED, False),
])
def test_item_availability(status, expected):
    item = Item(status=status)
    assert item.is_available() == expected
```

### Async Testing
```python
@pytest.mark.asyncio
async def test_async_operation():
    async with AsyncSession() as session:
        result = await create_item_async(session, item_data)
        assert result is not None
```

## Test Maintenance

### Regular Tasks
- Run tests before commits
- Update tests when changing code
- Review coverage reports weekly
- Clean up deprecated tests

### Adding New Tests
1. Create test file following naming convention
2. Add fixtures to conftest.py if needed
3. Write tests covering happy path and edge cases
4. Verify coverage increases
5. Document complex test scenarios

### Test Performance
- Use in-memory database for unit tests
- Mock external services
- Parallelize independent tests
- Profile slow tests

## Summary

The testing suite ensures:
- ✅ Code reliability through comprehensive coverage
- ✅ Fast feedback with automated tests
- ✅ Confidence in deployments
- ✅ Documentation through test examples
- ✅ Regression prevention

Run tests frequently and maintain high coverage standards!