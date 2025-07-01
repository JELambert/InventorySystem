# Testing Runbook - Home Inventory System

**Last Updated**: 2025-07-01  
**Testing Framework**: Comprehensive API & Frontend Testing Suite  
**Coverage**: 75+ API endpoints, Error handling, Business rules, Integration workflows

---

## 🧪 Testing Overview

The Home Inventory System includes a comprehensive testing suite covering:
- **API Endpoint Testing**: 100% coverage of 75+ API endpoints
- **Error Handling Testing**: HTTP errors, validation errors, system failures
- **Business Logic Testing**: Movement validation, data integrity, business rules
- **Integration Testing**: End-to-end workflows and cross-API dependencies
- **Performance Testing**: Cache management, optimization, load testing

---

## 📋 Quick Start Testing

### Backend API Testing
```bash
cd backend

# Run all tests
python run_tests.py

# Run specific test suites
python run_tests.py tests/test_api_items_comprehensive.py -v
python run_tests.py tests/test_api_inventory_operations.py -v
python run_tests.py tests/test_api_performance_monitoring.py -v

# Run with coverage
python run_tests.py --cov=app --cov-report=html
```

### Frontend Testing
```bash
cd frontend

# Run all frontend tests
python run_frontend_tests.py

# Run specific frontend test categories
poetry run pytest tests/test_components/ -v
poetry run pytest tests/test_error_boundaries/ -v
```

---

## 🗂️ Test Suite Organization

### Backend Tests (`backend/tests/`)

#### API Endpoint Tests
- **`test_api_items_comprehensive.py`** (500+ lines)
  - **Coverage**: 25+ Items API endpoints
  - **Tests**: CRUD operations, search, bulk operations, tag management, statistics
  - **Run**: `python run_tests.py tests/test_api_items_comprehensive.py`

- **`test_api_inventory_operations.py`** (600+ lines)
  - **Coverage**: 30+ Inventory API endpoints  
  - **Tests**: Movement operations, quantity management, validation, history
  - **Run**: `python run_tests.py tests/test_api_inventory_operations.py`

- **`test_api_performance_monitoring.py`** (350+ lines)
  - **Coverage**: 8+ Performance API endpoints
  - **Tests**: Metrics, cache management, optimization, query analysis
  - **Run**: `python run_tests.py tests/test_api_performance_monitoring.py`

#### Integration & Error Tests
- **`test_api_integration_workflows.py`** (400+ lines)
  - **Coverage**: End-to-end user journeys
  - **Tests**: Complete item lifecycle, cross-API dependencies, bulk operations
  - **Run**: `python run_tests.py tests/test_api_integration_workflows.py`

- **`test_api_error_scenarios.py`** (350+ lines)
  - **Coverage**: HTTP errors, validation errors, system failures
  - **Tests**: 400/404/409/422/500 errors, malformed requests, database failures
  - **Run**: `python run_tests.py tests/test_api_error_scenarios.py`

- **`test_api_validation_business_rules.py`** (350+ lines)
  - **Coverage**: Business rule enforcement, data integrity
  - **Tests**: Movement validation, constraints, referential integrity
  - **Run**: `python run_tests.py tests/test_api_validation_business_rules.py`

#### Core System Tests
- **`test_error_handler.py`** (450+ lines)
  - **Coverage**: Error handling infrastructure
  - **Tests**: Structured errors, analytics, middleware, correlation IDs

- **`test_movement_validation.py`** (480+ lines)
  - **Coverage**: Movement validation system
  - **Tests**: Business rules, bulk validation, validation reporting

- **`test_performance_optimization.py`** (350+ lines)
  - **Coverage**: Performance optimization system
  - **Tests**: Query optimization, caching, performance analysis

### Frontend Tests (`frontend/tests/`)

#### Component Tests
- **`test_error_boundaries.py`** (Planned)
  - **Coverage**: Error boundary components
  - **Tests**: Page boundaries, component boundaries, error recovery

- **`test_notifications.py`** (Planned)
  - **Coverage**: Notification system
  - **Tests**: Toast notifications, progress indicators, user feedback

- **`test_safe_utilities.py`** (Planned)
  - **Coverage**: Safe utility functions
  - **Tests**: Safe string handling, session state management, error recovery

---

## 🎯 Testing Scenarios by Category

### 1. CRUD Operations Testing
**Purpose**: Validate basic create, read, update, delete operations
```bash
# Items CRUD
python run_tests.py tests/test_api_items_comprehensive.py::TestItemsAPICRUD -v

# Inventory CRUD  
python run_tests.py tests/test_api_inventory_operations.py::TestInventoryAPICRUD -v
```

**What's Tested**:
- Item creation with validation
- Item updates with constraint checking
- Soft/hard deletion
- Data retrieval with filtering

### 2. Advanced Search Testing
**Purpose**: Validate complex search and filtering capabilities
```bash
# Advanced item search
python run_tests.py tests/test_api_items_comprehensive.py::TestItemsAPIAdvancedOperations::test_advanced_search -v

# Cross-entity search
python run_tests.py tests/test_api_integration_workflows.py::TestSearchAndFilteringWorkflows -v
```

**What's Tested**:
- Multi-criteria filtering
- Text search across fields
- Date range filtering
- Value range filtering
- Tag-based search

### 3. Movement Operations Testing
**Purpose**: Validate item movement and quantity management
```bash
# Movement operations
python run_tests.py tests/test_api_inventory_operations.py::TestInventoryAPIMovementOperations -v

# Movement validation
python run_tests.py tests/test_api_inventory_operations.py::TestInventoryAPIMovementValidation -v
```

**What's Tested**:
- Item movements between locations
- Quantity split/merge operations
- Movement history tracking
- Business rule enforcement

### 4. Error Handling Testing
**Purpose**: Validate comprehensive error handling
```bash
# HTTP error scenarios
python run_tests.py tests/test_api_error_scenarios.py::TestHTTPErrorHandling -v

# System failure scenarios
python run_tests.py tests/test_api_error_scenarios.py::TestSystemFailureHandling -v
```

**What's Tested**:
- HTTP status codes (400, 404, 409, 422, 500)
- Validation error responses
- Database connection failures
- Malformed request handling

### 5. Business Rules Testing
**Purpose**: Validate business logic and constraints
```bash
# Movement validation rules
python run_tests.py tests/test_api_validation_business_rules.py::TestMovementValidationRules -v

# Data integrity constraints
python run_tests.py tests/test_api_validation_business_rules.py::TestDataIntegrityConstraints -v
```

**What's Tested**:
- Movement quantity limits
- Location capacity constraints
- Item status restrictions
- Duplicate prevention rules

### 6. Performance Testing
**Purpose**: Validate system performance and optimization
```bash
# Performance monitoring
python run_tests.py tests/test_api_performance_monitoring.py::TestPerformanceAPIMetrics -v

# Cache management
python run_tests.py tests/test_api_performance_monitoring.py::TestPerformanceAPICacheManagement -v
```

**What's Tested**:
- Performance metrics collection
- Cache hit/miss ratios
- Query optimization
- System load handling

---

## 🔧 Test Configuration & Setup

### Environment Setup
```bash
# Backend test environment
cd backend
export PYTHONPATH=$(pwd)
export DATABASE_URL="sqlite:///./test.db"
export TESTING=true

# Frontend test environment  
cd frontend
export PYTHONPATH=$(pwd)
export STREAMLIT_SERVER_PORT=8501
```

### Database Setup for Integration Testing
```bash
# Create test database
cd backend
poetry run alembic upgrade head

# Seed test data (optional)
poetry run python scripts/seed_test_data.py
```

### Mock Configuration
Tests use comprehensive mocking to avoid external dependencies:
- **Database Sessions**: Mocked with SQLAlchemy AsyncMock
- **External APIs**: Mocked with unittest.mock
- **File System**: Mocked for file operations
- **Cache Systems**: Mocked for performance testing

---

## 📊 Test Execution Patterns

### Running All Tests
```bash
# Complete test suite
cd backend && python run_tests.py
cd frontend && python run_frontend_tests.py

# With coverage reporting
cd backend && python run_tests.py --cov=app --cov-report=html --cov-report=term
```

### Running Specific Test Categories
```bash
# API endpoint tests only
python run_tests.py tests/test_api_*.py

# Error handling tests only
python run_tests.py tests/test_*error*.py tests/test_api_error_scenarios.py

# Integration tests only
python run_tests.py tests/test_api_integration_workflows.py

# Performance tests only
python run_tests.py tests/test_*performance*.py
```

### Running Tests by API Category
```bash
# Items API tests
python run_tests.py tests/test_api_items_comprehensive.py

# Inventory API tests
python run_tests.py tests/test_api_inventory_operations.py

# Performance API tests
python run_tests.py tests/test_api_performance_monitoring.py
```

---

## 🐛 Debugging Failed Tests

### Common Test Failures

#### Database Connection Issues
```bash
# Symptoms: sqlite3.OperationalError: no such table
# Solution: Run database migrations
cd backend
poetry run alembic upgrade head
```

#### Import Path Issues
```bash
# Symptoms: ImportError: cannot import name
# Solution: Use run_tests.py wrapper
python run_tests.py tests/test_file.py  # Instead of pytest directly
```

#### Mock Configuration Issues
```bash
# Symptoms: AttributeError in mock objects
# Solution: Check mock setup in test fixtures
# Ensure proper async mock configuration
```

### Debugging Commands
```bash
# Run single test with verbose output
python run_tests.py tests/test_api_items_comprehensive.py::TestItemsAPICRUD::test_create_item_success -v -s

# Run with debugging
python run_tests.py tests/test_file.py --pdb

# Run with print statements
python run_tests.py tests/test_file.py -s
```

---

## 📈 Test Coverage & Reporting

### Coverage Analysis
```bash
# Generate coverage report
cd backend
python run_tests.py --cov=app --cov-report=html --cov-report=term

# View coverage report
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

### Expected Coverage Metrics
- **API Endpoints**: 100% (75+ endpoints tested)
- **Error Scenarios**: 90%+ (comprehensive error testing)
- **Business Logic**: 95%+ (movement validation, constraints)
- **Integration Workflows**: 85%+ (end-to-end journeys)

### Coverage Targets by Module
- **`app/api/`**: 100% endpoint coverage
- **`app/services/`**: 90%+ business logic coverage
- **`app/core/`**: 95%+ error handling coverage
- **`app/performance/`**: 85%+ optimization coverage

---

## 🚀 CI/CD Integration

### GitHub Actions Configuration
```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]
jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.12
      - name: Install dependencies
        run: |
          cd backend
          pip install poetry
          poetry install
      - name: Run tests
        run: |
          cd backend
          python run_tests.py --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v1
```

### Pre-commit Hooks
```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

---

## 📝 Test Maintenance

### Adding New Tests
1. **API Endpoint Tests**: Add to appropriate `test_api_*.py` file
2. **Business Logic Tests**: Add to `test_*_validation.py` files
3. **Error Scenarios**: Add to `test_api_error_scenarios.py`
4. **Integration Tests**: Add to `test_api_integration_workflows.py`

### Test Data Management
- **Use Fixtures**: Create reusable test data in pytest fixtures
- **Mock Consistently**: Use consistent mocking patterns across tests
- **Isolate Tests**: Ensure tests don't depend on each other

### Performance Considerations
- **Fast Tests**: Use mocking to avoid slow database operations
- **Parallel Execution**: Tests designed to run in parallel
- **Resource Cleanup**: Proper cleanup in fixtures and teardown

---

## 🔍 Test Quality Checklist

### Before Committing Tests
- [ ] All tests pass locally
- [ ] Tests use proper mocking
- [ ] Tests are isolated and don't depend on each other
- [ ] Error scenarios are covered
- [ ] Happy path and edge cases are tested
- [ ] Tests have clear, descriptive names
- [ ] Test documentation is updated

### Code Review Checklist
- [ ] Test coverage is adequate (>90% for new code)
- [ ] Tests follow established patterns
- [ ] Mock objects are properly configured
- [ ] Error handling is tested
- [ ] Integration scenarios are covered
- [ ] Performance implications are considered

---

## 📞 Support & Troubleshooting

### Getting Help
1. **Check this runbook** for common scenarios
2. **Review test logs** for specific error messages  
3. **Check DEVELOPMENT_LOG.md** for recent changes
4. **Review test patterns** in existing tests for examples

### Common Solutions
- **Database Issues**: Run `alembic upgrade head`
- **Import Issues**: Use `python run_tests.py` wrapper
- **Mock Issues**: Check async mock configuration
- **Coverage Issues**: Review test isolation and cleanup

This comprehensive testing runbook ensures reliable, maintainable testing practices across the entire Home Inventory System.