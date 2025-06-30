# Home Inventory System - Operational Runbook

**Last Updated**: 2025-01-26  
**Version**: 1.0  
**Environment**: Development Phase - Week 1

This is the comprehensive operational guide for the Home Inventory System. Use this runbook for all development, testing, troubleshooting, and maintenance procedures.

---

## 🚀 Quick Reference

### Essential Commands (Poetry)
```bash
# Start development environment
cd backend && poetry run uvicorn app.main:app --reload --port 8000

# Run all tests
cd backend && poetry run pytest

# Run code quality checks
cd backend && poetry run black . && poetry run flake8 && poetry run mypy app/

# Environment diagnostics
cd backend && poetry run python scripts/diagnose_environment.py

# Manual verification
cd backend && poetry run python scripts/verify_step_1_2b.py

# Install dependencies
cd backend && poetry install
cd frontend && poetry install
```

### Full Stack Testing Commands (Poetry)
```bash
# Complete system test (run from project root)

# 1. Start backend (Terminal 1)
cd backend
poetry install
poetry run uvicorn app.main:app --reload --port 8000

# 2. Start frontend (Terminal 2)
cd frontend
poetry install
poetry run streamlit run app.py
# Note: Streamlit runs on fixed port 8501

# 3. Test all components (Terminal 3)
cd backend && poetry run pytest
cd frontend && poetry run python scripts/verify_frontend_phase2.py

# 4. Manual testing URLs
# Backend API: http://localhost:8000/docs
# Frontend App: http://localhost:8501
# API Health: http://localhost:8000/health

# 5. Docker Compose (Alternative)
docker-compose up --build
# Access: http://localhost:8000 (backend), http://localhost:8501 (frontend)
```

### Frontend Startup Notes
- Streamlit runs on fixed port 8501 (developmentMode = false)
- Access frontend at: http://localhost:8501
- Look for "You can now view your Streamlit app in your browser" message
- URL will consistently show: http://0.0.0.0:8501

### Emergency Procedures (Poetry)
- **Backend environment broken**: Run `cd backend && poetry install`
- **Tests failing**: Run `cd backend && poetry run python scripts/diagnose_environment.py`
- **Fresh start**: Delete Poetry virtual envs with `poetry env remove --all`, then `poetry install`
- **Database issues**: Run `cd backend && poetry run python scripts/setup_postgres_database.py`
- **PostgreSQL down**: Check Proxmox LXC container at 192.168.68.88:5432
- **Frontend not loading**: Check `cd frontend && poetry run streamlit run app.py`
- **API connectivity issues**: Verify backend is running on port 8000
- **Import/Export not working**: Check API client connection and file permissions
- **Validation errors**: Check data format and business rules
- **Performance issues**: Clear Streamlit cache with `poetry run streamlit cache clear`
- **Keyboard shortcuts not working**: Refresh browser page and check JavaScript console
- **Poetry issues**: Check `poetry --version`, reinstall if needed

---

## 📋 Table of Contents

1. [Development Environment](#development-environment)
2. [Frontend Operations](#frontend-operations)
3. [Testing Strategy](#testing-strategy)  
4. [Code Quality Pipeline](#code-quality-pipeline)
5. [Database Operations](#database-operations)
6. [Development Workflow](#development-workflow)
7. [Scripts Reference](#scripts-reference)
8. [Troubleshooting](#troubleshooting)
9. [Project Structure](#project-structure)

---

## 🔧 Development Environment

### Initial Setup

#### Option 1: Poetry Development (Recommended)

1. **Install Poetry (if not installed):**
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   # OR
   pip install poetry
   ```

2. **Navigate to backend directory and install dependencies:**
   ```bash
   cd backend
   poetry install
   ```

3. **Navigate to frontend directory and install dependencies:**
   ```bash
   cd ../frontend
   poetry install
   ```

4. **Verify installation:**
   ```bash
   cd ../backend
   poetry run python scripts/diagnose_environment.py
   ```

#### Option 2: Legacy pip Development (Not Recommended)

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # OR
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies:**
   ```bash
   # Development dependencies (minimal, stable)
   pip install -r requirements-dev.txt
   
   # If installation fails, try:
   pip install --upgrade pip
   pip install -r requirements-dev.txt
   ```

4. **Verify installation:**
   ```bash
   python scripts/diagnose_environment.py
   ```

#### Option 3: Docker Development

If local installation fails:

```bash
# Build and run full-stack development environment
docker-compose up --build

# Run commands in backend container
docker-compose exec backend poetry run python scripts/diagnose_environment.py

# Run tests in backend container
docker-compose exec backend poetry run pytest

# Run frontend verification
docker-compose exec frontend poetry run python scripts/verify_frontend_phase2.py
```

### Environment Validation

**Always run after setup or when encountering issues:**

```bash
# Comprehensive environment diagnostics (Poetry)
cd backend && poetry run python scripts/diagnose_environment.py

# Quick environment setup (fixes common issues)
cd backend && poetry run python scripts/setup_test_environment.py

# Legacy pip approach
python scripts/diagnose_environment.py
python scripts/setup_test_environment.py
```

**Expected output:** All 8 diagnostic checks should pass ✅

### Poetry Quick Reference

**Essential Poetry Commands:**

```bash
# Install dependencies
poetry install                    # Install all dependencies
poetry install --only=main       # Install only main dependencies
poetry install --only=dev        # Install only dev dependencies

# Run commands
poetry run python script.py      # Run Python script
poetry run pytest               # Run tests
poetry run uvicorn app.main:app # Run server

# Environment management
poetry shell                     # Activate virtual environment
poetry env info                  # Show environment info
poetry env list                  # List environments
poetry env remove python        # Remove environment

# Dependency management
poetry add package               # Add new dependency
poetry add --group dev package   # Add dev dependency
poetry remove package           # Remove dependency
poetry update                   # Update all dependencies
poetry lock                     # Update lock file

# Troubleshooting
poetry check                     # Validate pyproject.toml
poetry config --list            # Show configuration
poetry cache clear --all        # Clear caches
```

### Virtual Environment Management

**Activate environment:**
```bash
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

**Deactivate environment:**
```bash
deactivate
```

**Recreate environment (if corrupted):**
```bash
rm -rf venv/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

---

## 🖥️ Frontend Operations

### Streamlit Application Setup

#### Initial Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install frontend dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation:**
   ```bash
   python scripts/verify_frontend_phase2.py
   ```

#### Running the Frontend Application

**Standard Development Mode (Poetry):**
```bash
cd frontend
poetry run streamlit run app.py
```

**Custom Configuration (Poetry):**
```bash
cd frontend
poetry run streamlit run app.py --server.address 0.0.0.0
```

**Debug Mode (Poetry):**
```bash
cd frontend
poetry run streamlit run app.py --logger.level=debug
```

### Frontend-Backend Integration

#### Starting Full Stack

**Terminal 1 - Backend (Poetry):**
```bash
cd backend
poetry run uvicorn app.main:app --reload --port 8000
```

**Terminal 2 - Frontend (Poetry):**
```bash
cd frontend
poetry run streamlit run app.py
```

**Access Points:**
- **Frontend**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

#### Configuration

**Environment Variables:**
```bash
# API Configuration
export API_BASE_URL=http://127.0.0.1:8000
export API_TIMEOUT=30
export DEBUG=true

# Streamlit Configuration
export STREAMLIT_SERVER_PORT=8501
export STREAMLIT_SERVER_ADDRESS=0.0.0.0
```

### Frontend Features

#### Available Pages

1. **📊 Dashboard** (`http://localhost:8501`)
   - **Enhanced Visualizations**: Advanced charts with tabbed interface
     - Overview: Pie charts and bar charts with interactive features
     - Hierarchy: Treemap visualization with depth controls
     - Timeline: Creation timeline and cumulative statistics
     - Analytics: Comprehensive metrics dashboard
   - **Performance Metrics**: System monitoring and cache management
   - **Keyboard Shortcuts**: Alt+D for quick navigation
   - **Real-time Statistics**: Live connection status and quick stats

2. **📍 Locations** (`http://localhost:8501/Locations`)
   - **Advanced Search**: Enhanced search with clear buttons and filters
   - **Quick Type Filters**: One-click filtering by location type
   - **Enhanced Pagination**: Jump-to-page controls and improved navigation
   - **Search Analytics**: Real-time search result metrics
   - **Bulk Selection**: Multi-select capabilities for batch operations
   - **Keyboard Shortcuts**: Alt+L for navigation, Alt+S for search focus
   - **Interactive Actions**: View, edit, delete, and view children for each location

3. **⚙️ Manage** (`http://localhost:8501/Manage`)
   - **Multi-tab Interface**:
     - **Individual**: Single location creation/editing with enhanced validation
     - **Bulk Operations**: Template-based bulk creation and CSV/JSON import
     - **Import/Export**: Complete data management capabilities
   - **Location Templates**: Pre-built structures (Basic House, Office, Kitchen, Garage)
   - **Advanced Validation**: Real-time validation with business rules
   - **Data Import/Export**: 
     - CSV and JSON import with validation
     - Multiple export formats (CSV, JSON, ZIP backup)
     - Template-based bulk creation
   - **Keyboard Shortcuts**: Alt+M for navigation, Alt+N for new location

#### API Client Features

**Health Checking:**
- Automatic backend connectivity testing
- Real-time connection status in sidebar
- Graceful error handling when backend is down

**Data Operations:**
- Full CRUD operations for locations
- Search and filtering with multiple criteria
- Hierarchical data display (parent-child relationships)
- Data validation and error reporting

### Frontend Development

#### File Structure
```
frontend/
├── app.py                              # Main Streamlit application
├── requirements.txt                    # Frontend dependencies
├── .streamlit/config.toml             # Streamlit configuration
├── pages/                             # Multi-page application
│   ├── 01_📊_Dashboard.py             # Enhanced dashboard with visualizations
│   ├── 02_📍_Locations.py             # Advanced location browser
│   └── 03_⚙️_Manage.py                # Comprehensive location management
├── components/                        # Advanced UI components
│   ├── visualizations.py             # Advanced charts and analytics
│   ├── location_templates.py         # Template system and bulk operations
│   ├── keyboard_shortcuts.py         # Keyboard shortcuts and UX enhancements
│   ├── performance.py                # Performance monitoring and optimization
│   ├── import_export.py               # Data import/export functionality
│   └── validation.py                 # Advanced data validation
├── utils/                             # Utility modules
│   ├── api_client.py                  # Backend API client
│   ├── config.py                      # Configuration management
│   └── helpers.py                     # UI helper functions
└── scripts/                           # Verification scripts
    └── verify_frontend_phase2.py      # Frontend verification
```

#### Development Commands

**Testing and Verification:**
```bash
cd frontend
python scripts/verify_frontend_phase2.py

# Test specific components
python -c "from components.visualizations import LocationVisualizationBuilder; print('Visualizations OK')"
python -c "from components.import_export import show_import_export_interface; print('Import/Export OK')"
python -c "from components.validation import LocationValidator; print('Validation OK')"
```

**Configuration Testing:**
```bash
cd frontend
streamlit config show

# Test API connectivity
python -c "from utils.api_client import APIClient; print('API Connected:', APIClient().health_check())"
```

**Cache and Performance Management:**
```bash
cd frontend
streamlit cache clear

# Clear all caches including session state
python -c "
import streamlit as st
st.cache_data.clear()
print('All caches cleared')
"

# Monitor performance
python -c "
from components.performance import perf_monitor
print('Performance monitoring enabled')
"
```

**Feature Testing:**
```bash
# Test keyboard shortcuts (manual)
echo "Test keyboard shortcuts in browser:"
echo "Alt+D = Dashboard, Alt+L = Locations, Alt+M = Manage"
echo "Alt+S = Search focus, Alt+R = Refresh, Esc = Cancel"

# Test import/export (requires sample data)
echo "Test import/export with sample CSV/JSON files"

# Test templates
echo "Test location templates: Basic House, Office, Kitchen, Garage"
```

### Troubleshooting Frontend Issues

#### Common Issues

**Problem**: Streamlit app won't start
```bash
# Solution 1: Check Poetry environment
cd frontend && poetry env info

# Solution 2: Reinstall dependencies with Poetry
cd frontend && poetry install

# Solution 3: Clear Streamlit cache
cd frontend && poetry run streamlit cache clear
```

**Problem**: API connection errors
```bash
# Solution 1: Verify backend is running
curl http://127.0.0.1:8000/health

# Solution 2: Check API configuration
python -c "from utils.config import AppConfig; print(AppConfig.API_BASE_URL)"

# Solution 3: Test API client
cd frontend
python -c "from utils.api_client import APIClient; print(APIClient().health_check())"
```

**Problem**: Pages not loading correctly
```bash
# Solution 1: Check page syntax
python scripts/verify_frontend_phase2.py

# Solution 2: Restart Streamlit with Poetry
# Ctrl+C to stop, then poetry run streamlit run app.py

# Solution 3: Check browser console for JavaScript errors
# Open browser developer tools (F12)
```

#### Performance Optimization

**Cache Configuration:**
```bash
# Streamlit configuration in .streamlit/config.toml
[server]
enableStaticServing = true
maxUploadSize = 1028

[client]
showErrorDetails = true
```

**API Client Optimization:**
```bash
# Configuration in utils/config.py
API_TIMEOUT = 30
API_RETRY_COUNT = 3
```

### Frontend Monitoring

#### Health Checks

**Frontend Application:**
```bash
# Check if Streamlit is running
curl -I http://localhost:8501
```

**API Connectivity:**
```bash
# Test from frontend environment
cd frontend
python -c "
from utils.api_client import APIClient
client = APIClient()
print('Health:', client.health_check())
print('Connection:', client.get_connection_info())
"
```

#### Logs and Debugging

**Streamlit Logs:**
```bash
cd frontend
poetry run streamlit run app.py --logger.level=debug
```

**API Client Logs:**
```bash
# Enable debug logging in frontend
export LOG_LEVEL=DEBUG
poetry run streamlit run app.py
```

---

## 🧪 Testing Strategy

### Test Hierarchy

1. **Unit Tests** (pytest) - Isolated component testing
2. **Integration Tests** (pytest) - Database and API integration
3. **Manual Verification** (scripts) - Standalone validation
4. **Environment Diagnostics** (scripts) - System validation

### Running Tests

#### Primary Test Execution

```bash
# Recommended: Run all tests with proper Python path handling
python run_tests.py

# Alternative: Manual pytest execution
PYTHONPATH=. python -m pytest tests/ -v

# Specific test file
PYTHONPATH=. python -m pytest tests/test_location_model.py -v

# Single test function
PYTHONPATH=. python -m pytest tests/test_location_model.py::test_location_creation -v
```

#### Manual Verification Scripts

```bash
# Database foundation verification
python scripts/verify_step_1_2a.py

# Location model verification  
python scripts/verify_step_1_2b.py

# Safe test runner (handles failures gracefully)
python scripts/run_tests_safe.py
```

### Test Coverage Analysis

**Current Coverage:**
- **Total Tests**: 23/23 passing (100%)
- **Database Base**: 5/5 tests
- **Location Model**: 15/15 tests (enhanced coverage)
- **FastAPI Endpoints**: 2/2 tests
- **Config Testing**: 1/1 test
- **Manual Verification**: 19/19 checks passing (includes PostgreSQL verification)

### Test Debugging

**If tests fail:**

1. **Run diagnostics first:**
   ```bash
   python scripts/diagnose_environment.py
   ```

2. **Check Python path issues:**
   ```bash
   # Ensure you're in backend directory
   pwd  # Should end with /backend
   
   # Run with explicit Python path
   PYTHONPATH=. python -m pytest tests/ -v
   ```

3. **Database issues:**
   ```bash
   # Remove database file and retry
   rm inventory.db
   python -m pytest tests/ -v
   ```

4. **Virtual environment issues:**
   ```bash
   # Verify virtual environment is active
   which python  # Should point to venv/bin/python
   
   # Reinstall dependencies
   pip install -r requirements-dev.txt
   ```

---

## ⚡ Code Quality Pipeline

### Automated Formatting

```bash
# Format all Python files
black .

# Check formatting without changes
black --check .

# Format specific files
black app/models/location.py
```

### Linting

```bash
# Run flake8 linter
flake8

# Check specific files
flake8 app/models/location.py

# Ignore specific errors (configured in .flake8)
flake8 --ignore=E203,W503 .
```

### Type Checking

```bash
# Run mypy type checker
mypy app/

# Check specific files
mypy app/models/location.py

# Show detailed error information
mypy app/ --show-error-codes
```

### Complete Quality Check

```bash
# Run all quality checks in sequence
black . && flake8 && mypy app/

# Quality check with test execution
black . && flake8 && mypy app/ && python run_tests.py
```

**Expected Results:**
- **black**: All files formatted ✅
- **flake8**: No linting errors ✅  
- **mypy**: No critical type errors ✅ (minor SQLAlchemy warnings acceptable)

---

## 🗄️ Database Operations

### Database Setup

**Current Configuration:**
- **Development**: PostgreSQL 17.5 (192.168.68.88:5432)
- **Testing**: In-memory SQLite (automatic)
- **Production**: PostgreSQL 17.5 (same as development)

### PostgreSQL Operations

```bash
# Setup PostgreSQL database (first time)
python scripts/setup_postgres_database.py

# Verify PostgreSQL integration
python scripts/verify_postgres_integration.py

# Check database connection
python -c "
from app.database.config import DatabaseConfig; 
print('Database URL:', DatabaseConfig.get_database_url())
"
```

### Migration Operations

```bash
# Check migration status
python scripts/manage_migrations.py status

# Apply pending migrations
python scripts/manage_migrations.py apply

# Create new migration
python scripts/manage_migrations.py create "Description of changes"

# Rollback migrations
python scripts/manage_migrations.py rollback <revision>

# Validate migration integrity
python scripts/manage_migrations.py validate
```

### Basic Operations

```bash
# Manual database verification (PostgreSQL)
python scripts/verify_postgres_integration.py

# Legacy database verification (SQLite tests)
python scripts/verify_step_1_2a.py

# Reset database (DANGER: removes all data)
python scripts/manage_migrations.py reset
```

### Database Schema

**Current Tables:**
- `locations` - Hierarchical location structure with self-referential relationships

**Table Structure:**
```sql
CREATE TABLE locations (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    location_type VARCHAR(9) NOT NULL,  -- HOUSE, ROOM, CONTAINER, SHELF
    parent_id INTEGER REFERENCES locations(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Database Validation

```bash
# Comprehensive database testing
PYTHONPATH=. python -m pytest tests/test_database_base.py -v

# Location model testing
PYTHONPATH=. python -m pytest tests/test_location_model.py -v

# Manual database verification
python scripts/verify_step_1_2a.py
python scripts/verify_step_1_2b.py
```

---

## 🔄 Development Workflow

### Step-by-Step Development Process

#### 1. Environment Setup
```bash
cd backend
source venv/bin/activate
python scripts/diagnose_environment.py  # Should pass 8/8 checks
```

#### 2. Development Work
```bash
# Make code changes
# Follow existing patterns in app/models/, app/database/, etc.
```

#### 3. Testing and Validation
```bash
# Run tests after changes
python run_tests.py

# Manual verification if available
python scripts/verify_step_1_2b.py

# Code quality checks
black . && flake8 && mypy app/
```

#### 4. Step Completion Verification

**Current Step Completion Criteria:**
- All tests pass (17/17)
- Manual verification passes (14/14 checks)
- Code quality checks pass
- Documentation updated

### Feature Development Workflow

1. **Plan the feature** (update DEVELOPMENT_LOG.md if needed)
2. **Create/update models** (follow Location model patterns)
3. **Write tests first** (TDD approach)
4. **Implement functionality**
5. **Run comprehensive testing**
6. **Manual verification**
7. **Code quality checks**
8. **Documentation updates**

### Branch Management (Future)

```bash
# When Git is initialized
git checkout -b feature/new-model
# Make changes
git add .
git commit -m "Add new model with tests"
# Run quality checks before push
black . && flake8 && python run_tests.py
```

---

## 📜 Scripts Reference

### Diagnostic Scripts

#### `scripts/diagnose_environment.py`
**Purpose**: Comprehensive environment validation  
**When to use**: Setup issues, test failures, environment problems  
**Output**: 8 diagnostic categories with pass/fail status

```bash
python scripts/diagnose_environment.py
```

**Checks performed:**
- Working directory validation
- Python path and imports
- Virtual environment status
- Dependencies verification
- SQLite functionality
- Async operations
- Database permissions
- Pytest configuration

#### `scripts/setup_test_environment.py`
**Purpose**: Automated environment setup and repair  
**When to use**: Initial setup, environment corruption, dependency issues

```bash
python scripts/setup_test_environment.py
```

**Actions performed:**
- Directory validation and navigation
- Python path configuration
- Virtual environment verification
- Dependency installation
- Database environment setup
- Pytest configuration validation
- Basic functionality testing

### Test Runner Scripts

#### `run_tests.py`
**Purpose**: Primary test runner with proper Python path handling  
**When to use**: Standard test execution

```bash
python run_tests.py
```

#### `scripts/run_tests_safe.py`
**Purpose**: Test runner with enhanced error handling  
**When to use**: Debugging test failures, CI/CD environments

```bash
python scripts/run_tests_safe.py
```

### Verification Scripts

#### `scripts/verify_step_1_2a.py`
**Purpose**: Database foundation verification  
**When to use**: After database setup, troubleshooting database issues

```bash
python scripts/verify_step_1_2a.py
```

**Verifies:**
- Database connection
- Table creation/deletion
- Session management
- Configuration validation
- SQLAlchemy Base functionality

#### `scripts/verify_step_1_2b.py`
**Purpose**: Location model functionality verification  
**When to use**: After Location model changes, manual validation

```bash
python scripts/verify_step_1_2b.py
```

**Verifies:**
- Location creation and validation
- Hierarchical relationships
- All location types (HOUSE, ROOM, CONTAINER, SHELF)
- Path generation and depth calculation
- Ancestor/descendant relationships

---

## 🔧 Troubleshooting

### Common Issues and Solutions

#### Environment Issues

**Problem**: `ImportError: No module named 'app'`
```bash
# Solution 1: Check working directory
pwd  # Should end with /backend

# Solution 2: Set Python path explicitly
export PYTHONPATH=.
python -m pytest tests/ -v

# Solution 3: Use main test runner
python run_tests.py
```

**Problem**: Virtual environment not working
```bash
# Solution: Recreate virtual environment
rm -rf venv/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

#### Test Failures

**Problem**: Tests failing with SQLAlchemy errors
```bash
# Solution 1: Check dependencies
python scripts/diagnose_environment.py

# Solution 2: Reinstall dependencies with correct versions
pip install -r requirements-dev.txt

# Solution 3: Remove database and retry
rm inventory.db
python run_tests.py
```

**Problem**: `DetachedInstanceError` in tests
```bash
# This is expected for some advanced SQLAlchemy operations
# Tests are designed to handle this gracefully
# Run manual verification instead:
python scripts/verify_step_1_2b.py
```

#### Installation Issues

**Problem**: `pip install` failing with compilation errors
```bash
# Solution 1: Upgrade pip
pip install --upgrade pip

# Solution 2: Use Docker
docker-compose -f docker-compose.dev.yml up --build

# Solution 3: Install dependencies individually
pip install fastapi uvicorn sqlalchemy aiosqlite pytest
```

#### Database Issues

**Problem**: Database connection failures
```bash
# Solution 1: Remove corrupted database
rm inventory.db

# Solution 2: Run database diagnostics
python scripts/verify_step_1_2a.py

# Solution 3: Full environment setup
python scripts/setup_test_environment.py
```

### Performance Issues

**Problem**: Tests running slowly
```bash
# Normal test execution time: ~0.5-1 second for all tests
# If slower, check:

# 1. Database file size
ls -la inventory.db

# 2. Virtual environment location (should be local)
which python

# 3. System resources
top  # Check CPU/memory usage
```

### Diagnostic Procedures

#### Full System Check
```bash
# Complete diagnostic procedure
cd backend
source venv/bin/activate
python scripts/diagnose_environment.py
python scripts/verify_step_1_2a.py  
python scripts/verify_step_1_2b.py
python run_tests.py
black --check . && flake8 && mypy app/
```

#### Environment Recovery
```bash
# Nuclear option: complete environment reset
cd backend
deactivate  # If virtual environment is active
rm -rf venv/ inventory.db
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
python scripts/setup_test_environment.py
python run_tests.py
```

---

## 📁 Project Structure

### Directory Layout

```
InventorySystem/
├── Architecture.md              # System architecture documentation
├── CLAUDE.md                   # Development guidance for Claude
├── DEVELOPMENT_LOG.md          # Progress tracking and decisions
├── RUNBOOK.md                  # This operational guide
└── backend/                    # Backend application
    ├── README.md               # Basic setup instructions
    ├── requirements-dev.txt    # Development dependencies
    ├── requirements.txt        # Production dependencies
    ├── run_tests.py           # Primary test runner
    ├── pytest.ini            # Pytest configuration
    ├── docker-compose.dev.yml # Docker development setup
    ├── Dockerfile             # Production container
    ├── Dockerfile.dev         # Development container
    ├── app/                   # Application source code
    │   ├── main.py           # FastAPI application entry point
    │   ├── database/         # Database configuration and setup
    │   │   ├── base.py       # SQLAlchemy base and session management
    │   │   └── config.py     # Database configuration
    │   ├── models/           # SQLAlchemy models
    │   │   └── location.py   # Location model with hierarchical structure
    │   ├── schemas/          # Pydantic schemas (planned)
    │   ├── services/         # Business logic layer (planned)
    │   └── api/              # FastAPI routes (planned)
    │       └── v1/           # API version 1 routes
    ├── tests/                # Test suite
    │   ├── test_main.py      # FastAPI endpoint tests
    │   ├── test_database_base.py    # Database foundation tests
    │   └── test_location_model.py   # Location model tests
    └── scripts/              # Operational scripts
        ├── diagnose_environment.py     # Environment diagnostics
        ├── setup_test_environment.py   # Environment setup
        ├── run_tests_safe.py          # Safe test runner
        ├── verify_step_1_2a.py        # Database verification
        └── verify_step_1_2b.py        # Location model verification
```

### Key Files and Their Purpose

**Configuration Files:**
- `pytest.ini` - Pytest configuration with async support and Python path
- `.flake8` - Linting configuration (line length, ignored errors)
- `requirements-dev.txt` - Minimal stable dependencies for development
- `requirements.txt` - Full production dependencies

**Application Code:**
- `app/main.py` - FastAPI application with health endpoints
- `app/database/base.py` - SQLAlchemy async setup and session management
- `app/models/location.py` - Hierarchical location model with self-referential relationships

**Testing Infrastructure:**
- `run_tests.py` - Primary test runner with Python path handling
- `tests/` - Comprehensive test suite (17 tests currently)
- `scripts/verify_*.py` - Manual verification scripts

### Code Organization Principles

1. **Separation of Concerns**: Models, database, API, and services in separate modules
2. **Async-First**: All database operations use async/await patterns
3. **Type Safety**: Full type annotations with SQLAlchemy 2.0 patterns
4. **Test Coverage**: Every component has corresponding tests
5. **Manual Verification**: Critical functionality has standalone verification scripts

---

## 📞 Support and References

### Documentation Hierarchy

1. **RUNBOOK.md** (this file) - Operational procedures
2. **DEVELOPMENT_LOG.md** - Progress tracking and decisions
3. **Architecture.md** - System design and technical architecture
4. **CLAUDE.md** - Development guidance for future AI assistance
5. **backend/README.md** - Basic setup and quick start

### Getting Help

1. **Environment Issues**: Run `python scripts/diagnose_environment.py`
2. **Test Failures**: Check this runbook's troubleshooting section
3. **Development Questions**: Refer to DEVELOPMENT_LOG.md for context
4. **Architecture Questions**: See Architecture.md

### Useful Links

- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **SQLAlchemy 2.0 Documentation**: https://docs.sqlalchemy.org/en/20/
- **Pytest Documentation**: https://docs.pytest.org/
- **Docker Compose Documentation**: https://docs.docker.com/compose/

---

**Last Updated**: 2025-01-26  
**Next Review**: When Step 1.2d is completed  
**Maintainer**: Development team