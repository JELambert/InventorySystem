# Testing Runbook - Home Inventory System

**Last Updated**: 2025-01-26  
**Version**: 1.0  
**Related**: [Main Runbook](../RUNBOOK.md)

This guide provides comprehensive testing procedures for the Home Inventory System, covering all test types, execution methods, and troubleshooting approaches.

---

## 🧪 Testing Overview

### Test Architecture

The testing strategy uses a multi-layered approach:

1. **Unit Tests** - Individual component testing
2. **Integration Tests** - Database and API integration
3. **Manual Verification** - Standalone validation scripts
4. **Environment Diagnostics** - System health checks

### Current Test Coverage

**✅ 17/17 Tests Passing (100% Success Rate)**

- **Database Foundation**: 5 tests
- **Location Model**: 10 tests  
- **FastAPI Endpoints**: 2 tests
- **Manual Verification**: 14 checks

---

## 🚀 Quick Test Execution

### Standard Test Runs

```bash
# Primary method (recommended)
cd backend && python run_tests.py

# All tests with verbose output
cd backend && PYTHONPATH=. python -m pytest tests/ -v

# Specific test file
cd backend && PYTHONPATH=. python -m pytest tests/test_location_model.py -v

# Single test function
cd backend && PYTHONPATH=. python -m pytest tests/test_location_model.py::test_location_creation -v
```

### Manual Verification

```bash
# Database foundation verification (6 checks)
cd backend && python scripts/verify_step_1_2a.py

# Location model verification (8 checks)
cd backend && python scripts/verify_step_1_2b.py

# Complete environment diagnostics (8 checks)
cd backend && python scripts/diagnose_environment.py
```

---

## 📋 Detailed Test Catalog

### Database Foundation Tests (`test_database_base.py`)

#### 1. `test_database_connection()`
**Purpose**: Verify basic database connectivity  
**What it tests**: 
- SQLAlchemy engine connection
- Basic SQL execution
- Connection reliability

**Expected behavior**: Returns `True` for successful connection

#### 2. `test_session_creation()`
**Purpose**: Validate async session factory  
**What it tests**:
- AsyncSession creation
- Session type validation
- Session lifecycle management

**Expected behavior**: Creates valid AsyncSession instance

#### 3. `test_create_and_drop_tables()`
**Purpose**: Test table management operations  
**What it tests**:
- Table creation from models
- Table dropping functionality
- Database schema operations

**Expected behavior**: Successfully creates and drops all tables

#### 4. `test_database_config()`
**Purpose**: Validate database configuration  
**What it tests**:
- Database URL generation
- Configuration validation
- Environment variable handling

**Expected behavior**: Returns valid database configuration

#### 5. `test_base_declarative()`
**Purpose**: Test SQLAlchemy Base functionality  
**What it tests**:
- Base class functionality
- Model registration
- Metadata consistency

**Expected behavior**: Base object functions correctly

### Location Model Tests (`test_location_model.py`)

#### 1. `test_location_creation()`
**Purpose**: Basic location instance creation  
**What it tests**:
- Model instantiation
- Field assignment and validation
- Database persistence
- Timestamp generation

**Expected behavior**: Creates location with all fields populated

#### 2. `test_location_string_representations()`
**Purpose**: String representation methods  
**What it tests**:
- `__str__()` method output
- `__repr__()` method output
- Consistent formatting

**Expected behavior**: 
- `str(location)` returns "Name (type)"
- `repr(location)` returns detailed object info

#### 3. `test_hierarchical_relationship()`
**Purpose**: Parent-child relationships  
**What it tests**:
- Parent assignment via parent_id
- Bidirectional relationship loading
- Children collection management

**Expected behavior**: Parent and children relationships work correctly

#### 4. `test_location_full_path()`
**Purpose**: Hierarchical path generation  
**What it tests**:
- Path generation through parent chain
- Correct delimiter usage (/)
- Multi-level hierarchy support

**Expected behavior**: Generates paths like "House/Room/Container/Shelf"

#### 5. `test_location_depth()`
**Purpose**: Hierarchy depth calculation  
**What it tests**:
- Depth calculation accuracy
- Root node handling (depth 0)
- Multi-level depth tracking

**Expected behavior**: Returns correct depth for each level

#### 6. `test_ancestor_descendant_relationships()`
**Purpose**: Relationship query methods  
**What it tests**:
- `is_ancestor_of()` method
- `is_descendant_of()` method
- Relationship traversal logic

**Expected behavior**: Correctly identifies ancestor/descendant relationships

#### 7. `test_get_root()`
**Purpose**: Root location identification  
**What it tests**:
- Root location finding
- Traversal to top of hierarchy
- Consistent root identification

**Expected behavior**: All locations in hierarchy return same root

#### 8. `test_get_all_descendants()`
**Purpose**: Descendant collection retrieval  
**What it tests**:
- Direct children access
- Manual hierarchy traversal
- Collection management

**Expected behavior**: Returns all descendant locations

#### 9. `test_cascade_delete()`
**Purpose**: Cascade deletion behavior  
**What it tests**:
- Parent deletion
- Automatic child deletion
- Database constraint enforcement

**Expected behavior**: Deleting parent removes all children

#### 10. `test_location_type_enum()`
**Purpose**: LocationType enum validation  
**What it tests**:
- All enum values (HOUSE, ROOM, CONTAINER, SHELF)
- Enum assignment and retrieval
- Database enum storage

**Expected behavior**: All location types work correctly

### FastAPI Endpoint Tests (`test_main.py`)

#### 1. `test_root()`
**Purpose**: Root endpoint functionality  
**What it tests**:
- GET / endpoint response
- JSON response format
- Status code validation

**Expected behavior**: Returns 200 with message

#### 2. `test_health_check()`
**Purpose**: Health endpoint functionality  
**What it tests**:
- GET /health endpoint response
- Health status reporting
- API availability

**Expected behavior**: Returns 200 with health status

---

## 🔧 Test Execution Methods

### Method 1: Primary Test Runner (Recommended)

```bash
cd backend
python run_tests.py
```

**Advantages:**
- Handles Python path automatically
- Consistent execution environment
- Integrated error handling
- Works in all environments

**When to use:** Standard test execution, CI/CD, development workflow

### Method 2: Direct Pytest Execution

```bash
cd backend
PYTHONPATH=. python -m pytest tests/ -v
```

**Advantages:**
- Full pytest features and options
- Detailed output control
- Direct pytest configuration access

**When to use:** Debugging, specific test selection, advanced pytest features

### Method 3: Safe Test Runner

```bash
cd backend
python scripts/run_tests_safe.py
```

**Advantages:**
- Enhanced error handling
- Environment validation
- Graceful failure handling

**When to use:** Debugging environment issues, CI/CD with error recovery

### Method 4: Docker Test Execution

```bash
# From project root
docker-compose -f backend/docker-compose.dev.yml run backend-dev python run_tests.py
```

**Advantages:**
- Isolated environment
- Consistent across systems
- No local dependency issues

**When to use:** Environment isolation, system compatibility issues

---

## 🔍 Manual Verification Procedures

### Database Foundation Verification

**Script**: `scripts/verify_step_1_2a.py`

**Checks Performed:**
1. **Database Connection** - Basic connectivity test
2. **Session Creation** - AsyncSession factory validation
3. **Table Operations** - Create/drop functionality
4. **Configuration** - Database URL and settings
5. **Base Functionality** - SQLAlchemy Base operations
6. **Async Operations** - Async/await functionality

**Expected Output:**
```
✅ PASS Database Connection
✅ PASS Session Creation  
✅ PASS Table Operations
✅ PASS Configuration
✅ PASS Base Functionality
✅ PASS Async Operations

Results: 6/6 checks passed
🎉 Database foundation is working correctly
```

### Location Model Verification

**Script**: `scripts/verify_step_1_2b.py`

**Checks Performed:**
1. **Location Creation** - Basic model instantiation and persistence
2. **Location Types** - All enum values (HOUSE, ROOM, CONTAINER, SHELF)
3. **String Representations** - __str__ and __repr__ methods
4. **Hierarchical Relationships** - Parent/child functionality
5. **Full Path Generation** - Path string generation
6. **Depth Calculation** - Hierarchy depth tracking
7. **Ancestor/Descendant Methods** - Relationship query methods
8. **Get Root Method** - Root location identification

**Expected Output:**
```
✅ Location Creation
✅ Location Types
✅ String Representations
✅ Hierarchical Relationships
✅ Full Path Generation
✅ Depth Calculation
✅ Ancestor/Descendant Methods
✅ Get Root Method

Results: 8/8 tests passed
🎉 All Location model tests passed! Step 1.2b is complete.
```

### Environment Diagnostics

**Script**: `scripts/diagnose_environment.py`

**Checks Performed:**
1. **Working Directory** - Correct location validation
2. **Python Path and Imports** - Module import capability
3. **Virtual Environment** - Virtual environment status
4. **Dependencies** - Required package installation
5. **SQLite Functionality** - Database operations
6. **Async Functionality** - Async/await operations
7. **Database Permissions** - File system permissions
8. **Pytest Configuration** - Test framework setup

**Expected Output:**
```
✅ Working Directory Check
✅ Python Path and Imports
✅ Virtual Environment Check
✅ Dependencies Check
✅ SQLite Functionality Check
✅ Async Functionality Check
✅ Database Permissions Check
✅ Pytest Configuration Check

Results: 8/8 checks passed
🚀 Environment is ready for testing!
```

---

## 🐛 Test Debugging Guide

### Common Test Failures

#### Import Errors

**Symptom**: `ImportError: No module named 'app'`

**Solutions:**
```bash
# 1. Verify working directory
pwd  # Should end with /backend

# 2. Use primary test runner
python run_tests.py

# 3. Set Python path explicitly
export PYTHONPATH=.
python -m pytest tests/ -v

# 4. Run environment diagnostics
python scripts/diagnose_environment.py
```

#### SQLAlchemy Session Errors

**Symptom**: `DetachedInstanceError` or session-related failures

**Solutions:**
```bash
# 1. Remove database file
rm inventory.db

# 2. Run database verification
python scripts/verify_step_1_2a.py

# 3. Use manual verification instead
python scripts/verify_step_1_2b.py

# 4. Check SQLAlchemy version compatibility
python -c "import sqlalchemy; print(sqlalchemy.__version__)"
```

#### Virtual Environment Issues

**Symptom**: Dependency not found or wrong Python version

**Solutions:**
```bash
# 1. Verify virtual environment is active
which python  # Should point to venv/bin/python

# 2. Recreate virtual environment
deactivate
rm -rf venv/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt

# 3. Run setup script
python scripts/setup_test_environment.py
```

#### Async Test Failures

**Symptom**: `RuntimeError: Event loop is closed` or similar

**Solutions:**
```bash
# 1. Check pytest-asyncio installation
pip list | grep pytest-asyncio

# 2. Verify pytest.ini configuration
cat pytest.ini  # Should have asyncio_mode = strict

# 3. Use safe test runner
python scripts/run_tests_safe.py
```

### Debug Test Execution

#### Verbose Test Output

```bash
# Maximum verbosity
PYTHONPATH=. python -m pytest tests/ -vvv

# Show local variables on failure
PYTHONPATH=. python -m pytest tests/ -v --tb=long

# Show print statements
PYTHONPATH=. python -m pytest tests/ -v -s
```

#### Single Test Debugging

```bash
# Run single failing test
PYTHONPATH=. python -m pytest tests/test_location_model.py::test_hierarchical_relationship -v

# Debug with pdb
PYTHONPATH=. python -m pytest tests/test_location_model.py::test_hierarchical_relationship -v --pdb
```

#### Database State Debugging

```bash
# Check database file
ls -la inventory.db

# Remove and recreate
rm inventory.db
python -c "from app.database.base import create_tables; import asyncio; asyncio.run(create_tables())"

# Manual database verification
python scripts/verify_step_1_2a.py
```

---

## 📊 Test Performance Analysis

### Expected Test Execution Times

- **Unit Tests**: < 0.1 seconds each
- **Integration Tests**: < 0.2 seconds each  
- **Full Test Suite**: < 1 second total
- **Manual Verification**: 2-5 seconds per script

### Performance Benchmarks

```bash
# Time test execution
time python run_tests.py

# Detailed timing with pytest
PYTHONPATH=. python -m pytest tests/ --durations=0

# Profile slow tests
PYTHONPATH=. python -m pytest tests/ --profile
```

### Performance Troubleshooting

**If tests are slow:**

1. **Check database file size:**
   ```bash
   ls -la inventory.db  # Should be small for development
   ```

2. **Verify virtual environment location:**
   ```bash
   which python  # Should be local venv, not system
   ```

3. **Monitor system resources:**
   ```bash
   top  # Check CPU and memory usage during tests
   ```

4. **Reset environment:**
   ```bash
   rm inventory.db
   python run_tests.py
   ```

---

## 🔄 Continuous Integration

### CI/CD Test Pipeline

**Recommended pipeline stages:**

1. **Environment Setup**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements-dev.txt
   ```

2. **Environment Validation**
   ```bash
   python scripts/diagnose_environment.py
   ```

3. **Code Quality Checks**
   ```bash
   black --check .
   flake8
   mypy app/
   ```

4. **Test Execution**
   ```bash
   python run_tests.py
   ```

5. **Manual Verification**
   ```bash
   python scripts/verify_step_1_2a.py
   python scripts/verify_step_1_2b.py
   ```

### CI/CD Exit Criteria

- All 17 automated tests pass ✅
- All 14 manual verification checks pass ✅
- Code quality checks pass ✅
- No critical mypy errors ✅

---

## 📈 Test Coverage Expansion

### Adding New Tests

When adding features, ensure:

1. **Unit Tests** for all new functions/methods
2. **Integration Tests** for database operations
3. **Manual Verification** for complex workflows
4. **Update this runbook** with new test documentation

### Test File Organization

```bash
tests/
├── test_main.py              # FastAPI endpoint tests
├── test_database_base.py     # Database foundation tests
├── test_location_model.py    # Location model tests
└── test_new_feature.py       # New feature tests (template)
```

### Test Template

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

async def _get_test_session():
    """Helper to get a test session with setup/teardown."""
    from app.database.base import create_tables, drop_tables, async_session
    await create_tables()
    try:
        async with async_session() as session:
            yield session
    finally:
        await drop_tables()

@pytest.mark.asyncio
async def test_new_feature():
    """Test new feature functionality."""
    async for session in _get_test_session():
        # Test implementation
        assert True  # Replace with actual test
```

---

## 📞 Support and References

### Related Documentation

- **[Main Runbook](../RUNBOOK.md)** - Complete operational guide
- **[Scripts Reference](./scripts-reference.md)** - Detailed script documentation
- **[Database Operations](./database-operations.md)** - Database management procedures

### External References

- **Pytest Documentation**: https://docs.pytest.org/
- **Pytest-Asyncio**: https://pytest-asyncio.readthedocs.io/
- **SQLAlchemy Testing**: https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites

---

**Last Updated**: 2025-01-26  
**Next Review**: When new test categories are added  
**Maintainer**: Development team