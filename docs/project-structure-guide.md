# Project Structure Guide - Home Inventory System

**Last Updated**: 2025-01-26  
**Version**: 1.0  
**Related**: [Main Runbook](../RUNBOOK.md) | [Development Workflow](./development-workflow.md)

This guide provides comprehensive navigation and understanding of the Home Inventory System codebase structure, module organization, and architectural patterns.

---

## 📁 Project Overview

### Repository Structure

```
InventorySystem/
├── 📄 Architecture.md              # System architecture and design decisions
├── 📄 CLAUDE.md                   # Development guidance for AI assistance
├── 📄 DEVELOPMENT_LOG.md          # Progress tracking and completed tasks
├── 📄 RUNBOOK.md                  # Main operational runbook
├── 📂 docs/                       # Specialized documentation
│   ├── 📄 testing-runbook.md      # Comprehensive testing guide
│   ├── 📄 scripts-reference.md    # All scripts documentation
│   ├── 📄 database-operations.md  # Database management guide
│   ├── 📄 development-workflow.md # Development procedures
│   ├── 📄 troubleshooting-playbook.md # Problem-solving guide
│   └── 📄 project-structure-guide.md  # This file
└── 📂 backend/                    # Backend application root
    ├── 📄 README.md               # Basic setup instructions
    ├── 📄 requirements-dev.txt    # Development dependencies
    ├── 📄 requirements.txt        # Production dependencies
    ├── 📄 run_tests.py           # Primary test runner
    ├── 📄 pytest.ini            # Pytest configuration
    ├── 📄 .flake8               # Linting configuration
    ├── 📄 docker-compose.dev.yml # Docker development setup
    ├── 📄 Dockerfile            # Production container
    ├── 📄 Dockerfile.dev        # Development container
    ├── 📂 app/                   # Application source code
    ├── 📂 tests/                 # Test suite
    ├── 📂 scripts/               # Operational scripts
    └── 📂 venv/                  # Virtual environment (local)
```

---

## 🏗️ Backend Application Structure

### Core Application (`backend/app/`)

```
app/
├── 📄 __init__.py              # Package initialization
├── 📄 main.py                 # FastAPI application entry point
├── 📂 database/               # Database configuration and management
│   ├── 📄 __init__.py         # Package initialization
│   ├── 📄 base.py            # SQLAlchemy setup and session management
│   └── 📄 config.py          # Database configuration utilities
├── 📂 models/                 # SQLAlchemy data models
│   ├── 📄 __init__.py         # Package initialization
│   └── 📄 location.py        # Location model with hierarchical structure
├── 📂 schemas/                # Pydantic schemas (planned)
│   └── 📄 __init__.py         # Package initialization
├── 📂 services/               # Business logic layer (planned)
│   └── 📄 __init__.py         # Package initialization
└── 📂 api/                    # FastAPI routes (planned)
    ├── 📄 __init__.py         # Package initialization
    └── 📂 v1/                 # API version 1
        └── 📄 __init__.py     # Package initialization
```

### Application Entry Point (`app/main.py`)

**Purpose**: FastAPI application initialization and configuration

**Key Components**:
- FastAPI app instance creation
- Basic health endpoints
- API documentation configuration
- CORS settings (future)
- Middleware configuration (future)

**Current Endpoints**:
- `GET /` - Root endpoint with welcome message
- `GET /health` - Health check endpoint
- `GET /docs` - Auto-generated API documentation

**Usage**:
```bash
# Start development server
uvicorn app.main:app --reload --port 8000

# Access endpoints
curl http://localhost:8000/          # Root
curl http://localhost:8000/health    # Health check
open http://localhost:8000/docs      # API docs
```

---

## 🗄️ Database Layer

### Database Configuration (`app/database/`)

#### `base.py` - Core Database Setup

**Purpose**: SQLAlchemy async configuration and session management

**Key Components**:
```python
# Core exports
Base                 # SQLAlchemy declarative base
engine               # Async SQLAlchemy engine
async_session        # Session factory
get_session()        # Dependency for FastAPI
create_tables()      # Table creation utility
drop_tables()        # Table deletion utility
check_connection()   # Connection health check
```

**Configuration**:
- **Development**: SQLite with aiosqlite driver
- **Connection String**: `sqlite+aiosqlite:///./inventory.db`
- **Engine Settings**: Echo enabled for development, async future mode
- **Session Factory**: `async_sessionmaker` with auto-expire disabled

**Model Registration**:
```python
# All models must be imported here to register with Base
from app.models import location  # noqa: F401
# Add new model imports here
```

#### `config.py` - Database Configuration Utilities

**Purpose**: Environment-based database configuration management

**Key Components**:
- Database URL generation
- Environment variable handling
- Configuration validation
- Connection string formatting

### Database Schema

#### Current Tables

**`locations` Table**:
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

-- Indexes for performance
CREATE INDEX ix_locations_name ON locations (name);
CREATE INDEX ix_locations_location_type ON locations (location_type);
CREATE INDEX ix_locations_parent_id ON locations (parent_id);
```

#### Planned Tables

**Categories** (Step 1.3):
- Item categorization system
- Hierarchical category structure
- Category metadata and descriptions

**Items** (Step 1.4):
- Core inventory items
- Relationships to locations and categories
- Item metadata and properties

---

## 📊 Data Models Layer

### Current Models (`app/models/`)

#### `location.py` - Hierarchical Location Model

**Purpose**: Represents the physical organization structure for inventory

**Class Structure**:
```python
class LocationType(enum.Enum):
    """Location type enumeration."""
    HOUSE = "house"
    ROOM = "room"
    CONTAINER = "container"
    SHELF = "shelf"

class Location(Base):
    """Hierarchical location model."""
    __tablename__ = "locations"
    
    # Primary key and core fields
    id: Mapped[int]
    name: Mapped[str]
    description: Mapped[Optional[str]]
    location_type: Mapped[LocationType]
    
    # Self-referential hierarchy
    parent_id: Mapped[Optional[int]]
    parent: Mapped[Optional["Location"]]
    children: Mapped[List["Location"]]
    
    # Timestamps
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

**Key Features**:
- **Self-referential relationships**: Parent/child hierarchy
- **Cascade deletion**: Deleting parent removes all children
- **Type safety**: Full SQLAlchemy 2.0 type annotations
- **Utility methods**: Path generation, depth calculation, relationship queries

**Utility Methods**:
```python
location.full_path          # "House/Room/Container/Shelf"
location.depth              # Hierarchy depth (0 = root)
location.is_ancestor_of()   # Check if ancestor of another location
location.is_descendant_of() # Check if descendant of another location
location.get_root()         # Get top-level location
location.get_all_descendants() # Get all children recursively
```

**Usage Examples**:
```python
# Create location hierarchy
house = Location(name="My House", location_type=LocationType.HOUSE)
room = Location(name="Kitchen", location_type=LocationType.ROOM, parent=house)
cabinet = Location(name="Upper Cabinet", location_type=LocationType.CONTAINER, parent=room)

# Query relationships
print(cabinet.full_path)  # "My House/Kitchen/Upper Cabinet"
print(cabinet.depth)      # 2
print(house.is_ancestor_of(cabinet))  # True
```

---

## 🧪 Testing Structure

### Test Organization (`backend/tests/`)

```
tests/
├── 📄 __init__.py              # Package initialization
├── 📄 test_main.py            # FastAPI endpoint tests
├── 📄 test_database_base.py   # Database foundation tests
└── 📄 test_location_model.py  # Location model tests
```

#### Test File Patterns

**Naming Convention**:
- `test_{module_name}.py` for module tests
- `test_{feature_name}.py` for feature tests
- Test functions: `test_{specific_functionality}`

**Test Structure Pattern**:
```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

async def _get_test_session():
    """Helper for test session with setup/teardown."""
    from app.database.base import create_tables, drop_tables, async_session
    await create_tables()
    try:
        async with async_session() as session:
            yield session
    finally:
        await drop_tables()

@pytest.mark.asyncio
async def test_specific_functionality():
    """Test specific functionality."""
    async for session in _get_test_session():
        # Test implementation
        assert True
```

#### Test Categories

**Unit Tests** (`test_*.py`):
- Individual component testing
- Model functionality
- Utility method testing

**Integration Tests** (embedded in unit tests):
- Database operations
- Model relationships
- Cross-component interactions

**Endpoint Tests** (`test_main.py`):
- FastAPI route testing
- Response validation
- API contract verification

### Test Configuration

#### `pytest.ini`

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
python_classes = Test*
addopts = -v --tb=short
asyncio_mode = strict
pythonpath = .
```

**Key Settings**:
- **Test Discovery**: Automatic discovery of test files and functions
- **Async Mode**: Strict mode for pytest-asyncio
- **Python Path**: Configured for proper import resolution
- **Verbosity**: Verbose output for better debugging

---

## 🔧 Operational Scripts

### Scripts Organization (`backend/scripts/`)

```
scripts/
├── 📄 diagnose_environment.py     # Comprehensive environment diagnostics
├── 📄 setup_test_environment.py   # Automated environment setup
├── 📄 run_tests_safe.py          # Enhanced test runner with error handling
├── 📄 verify_step_1_2a.py        # Database foundation verification
└── 📄 verify_step_1_2b.py        # Location model verification
```

#### Script Categories

**Diagnostic Scripts**:
- Environment validation
- System health checks
- Troubleshooting tools

**Setup Scripts**:
- Environment initialization
- Dependency installation
- Configuration validation

**Test Scripts**:
- Alternative test runners
- Manual verification procedures
- Integration testing

**Verification Scripts**:
- Step completion validation
- Feature verification
- Manual testing procedures

#### Script Structure Pattern

```python
#!/usr/bin/env python3
"""
Script description and purpose.
"""

import asyncio
import sys
import os

# Python path setup for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def print_section(title: str) -> None:
    """Print formatted section header."""
    print(f"\n{'='*60}")
    print(f"🔧 {title}")
    print(f"{'='*60}")

def print_result(check: str, success: bool, details: str = "") -> None:
    """Print check result with status indicator."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {check}")
    if details:
        print(f"    {details}")

async def main() -> None:
    """Main script execution."""
    # Script implementation
    pass

if __name__ == "__main__":
    asyncio.run(main())
```

---

## ⚙️ Configuration Files

### Development Configuration

#### `requirements-dev.txt`

**Purpose**: Minimal stable dependencies for development

**Key Dependencies**:
```
# Core application
fastapi==0.104.1
uvicorn[standard]==0.24.0

# Database (SQLite for development)
sqlalchemy==2.0.21
aiosqlite==0.19.0
typing-extensions==4.8.0
greenlet==3.0.1

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1

# Code quality
black==23.11.0
flake8==6.1.0
mypy==1.7.1
```

**Version Strategy**:
- **Pinned versions** for stability
- **Compatibility tested** combinations
- **Minimal set** to avoid compilation issues

#### `requirements.txt`

**Purpose**: Full production dependencies (may require system packages)

**Additional Dependencies**:
- PostgreSQL drivers (asyncpg)
- Production-grade web servers
- Monitoring and logging tools
- Security enhancements

#### `.flake8`

**Purpose**: Linting configuration compatible with Black

```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = 
    .git,
    __pycache__,
    .venv,
    venv,
    .eggs,
    *.egg,
    build,
    dist,
    .mypy_cache,
    .pytest_cache,
    migrations,
    scripts
```

**Key Settings**:
- **Line Length**: 88 characters (Black standard)
- **Ignored Errors**: E203, W503 (Black compatibility)
- **Excluded Directories**: Standard exclusion patterns

### Container Configuration

#### `docker-compose.dev.yml`

**Purpose**: Development environment containerization

**Services**:
- **backend-dev**: Development backend container
- **Volume mounts**: Live code reloading
- **Port mapping**: Host access to services

#### `Dockerfile` / `Dockerfile.dev`

**Purpose**: Container image definitions

**Development Features**:
- Live code reloading
- Development dependencies
- Debug-friendly configuration

**Production Features** (planned):
- Optimized image size
- Security hardening
- Performance optimization

---

## 🏛️ Architectural Patterns

### Code Organization Principles

#### 1. Separation of Concerns

**Database Layer** (`app/database/`):
- Connection management
- Session handling
- Configuration

**Model Layer** (`app/models/`):
- Data models
- Business logic
- Relationships

**API Layer** (`app/api/`) - Planned:
- HTTP endpoints
- Request/response handling
- Validation

**Service Layer** (`app/services/`) - Planned:
- Business logic
- Data processing
- Cross-model operations

#### 2. Dependency Injection

**Current Pattern**:
```python
# Database session dependency
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

# Usage in FastAPI endpoints (future)
@app.get("/locations/")
async def get_locations(session: AsyncSession = Depends(get_session)):
    # Endpoint implementation
    pass
```

#### 3. Async-First Architecture

**Consistent Patterns**:
- All database operations use `async`/`await`
- Async session management
- Async-compatible test patterns
- Future-ready for high concurrency

#### 4. Type Safety

**SQLAlchemy 2.0 Patterns**:
```python
# Typed column definitions
name: Mapped[str] = mapped_column(String(255), nullable=False)
parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey(...))

# Typed relationships
parent: Mapped[Optional["Location"]] = relationship(...)
children: Mapped[List["Location"]] = relationship(...)
```

### Design Patterns Used

#### 1. Repository Pattern (Future)

**Planned Structure**:
```python
class LocationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_id(self, location_id: int) -> Optional[Location]:
        # Implementation
        pass
    
    async def get_by_type(self, location_type: LocationType) -> List[Location]:
        # Implementation
        pass
```

#### 2. Service Layer Pattern (Future)

**Planned Structure**:
```python
class LocationService:
    def __init__(self, repository: LocationRepository):
        self.repository = repository
    
    async def create_hierarchy(self, hierarchy_data: dict) -> Location:
        # Business logic implementation
        pass
```

#### 3. Factory Pattern

**Current Usage**:
```python
# Session factory
async_session = async_sessionmaker(bind=engine, expire_on_commit=False)

# Model factories in tests
def create_test_location(**kwargs) -> Location:
    defaults = {
        'name': 'Test Location',
        'location_type': LocationType.ROOM
    }
    defaults.update(kwargs)
    return Location(**defaults)
```

---

## 🔄 Development Workflow Integration

### File Modification Workflow

#### 1. Adding New Models

**Steps**:
1. Create model file in `app/models/`
2. Import model in `app/database/base.py`
3. Create test file in `tests/`
4. Create verification script in `scripts/`
5. Update documentation

#### 2. Adding New API Endpoints

**Steps** (Future):
1. Define schema in `app/schemas/`
2. Create service in `app/services/`
3. Create routes in `app/api/v1/`
4. Create endpoint tests
5. Update main app routing

#### 3. Adding New Scripts

**Steps**:
1. Create script in `scripts/`
2. Follow script structure pattern
3. Add to scripts reference documentation
4. Test script functionality
5. Update main runbook

### Import Dependencies

#### Module Import Hierarchy

```
app/main.py
├── app/database/base.py
│   ├── app/models/location.py
│   └── app/database/config.py
└── app/api/ (future)
    └── app/schemas/ (future)
        └── app/services/ (future)
```

#### Import Best Practices

**Absolute Imports**:
```python
from app.database.base import Base, async_session
from app.models.location import Location, LocationType
```

**Relative Imports** (avoid in this project):
```python
# Don't use relative imports
from .base import Base  # Avoid
```

**Circular Import Prevention**:
- Models don't import from services
- Database layer doesn't import from API layer
- Clear dependency hierarchy

---

## 📈 Future Structure Evolution

### Planned Additions

#### 1. Authentication System

**Structure**:
```
app/
├── auth/
│   ├── __init__.py
│   ├── models.py          # User, Role models
│   ├── schemas.py         # Auth schemas
│   ├── service.py         # Auth business logic
│   └── routes.py          # Auth endpoints
```

#### 2. API Versioning

**Structure**:
```
app/api/
├── v1/
│   ├── locations.py       # Location endpoints
│   ├── categories.py      # Category endpoints
│   └── items.py          # Item endpoints
└── v2/                   # Future API version
```

#### 3. Background Tasks

**Structure**:
```
app/
├── tasks/
│   ├── __init__.py
│   ├── celery_app.py     # Celery configuration
│   ├── inventory_sync.py  # Sync tasks
│   └── maintenance.py    # Maintenance tasks
```

#### 4. External Integrations

**Structure**:
```
app/
├── integrations/
│   ├── __init__.py
│   ├── weaviate_client.py # Vector database
│   ├── storage_service.py # File storage
│   └── notification_service.py # Notifications
```

### Migration Strategies

#### Database Migrations

**When Alembic is Added**:
```
backend/
├── alembic/
│   ├── versions/          # Migration files
│   ├── env.py            # Alembic environment
│   └── script.py.mako    # Migration template
└── alembic.ini           # Alembic configuration
```

#### Code Structure Migrations

**Refactoring Approach**:
1. Create new structure alongside existing
2. Migrate functionality incrementally
3. Update tests and documentation
4. Remove old structure when complete

---

## 📞 Navigation and References

### Quick Navigation

**Common File Locations**:
- **Main App**: `backend/app/main.py`
- **Database Setup**: `backend/app/database/base.py`
- **Models**: `backend/app/models/`
- **Tests**: `backend/tests/`
- **Scripts**: `backend/scripts/`
- **Documentation**: `docs/`

**Common Commands**:
```bash
# Navigate to backend
cd backend

# Run tests
python run_tests.py

# Environment check
python scripts/diagnose_environment.py

# Start server
uvicorn app.main:app --reload --port 8000
```

### Related Documentation

- **[Main Runbook](../RUNBOOK.md)** - Operational procedures
- **[Development Workflow](./development-workflow.md)** - Development processes
- **[Testing Runbook](./testing-runbook.md)** - Testing procedures
- **[Database Operations](./database-operations.md)** - Database management

### External Resources

- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **SQLAlchemy 2.0 Documentation**: https://docs.sqlalchemy.org/en/20/
- **Python Project Structure**: https://docs.python-guide.org/writing/structure/

---

**Last Updated**: 2025-01-26  
**Next Review**: When significant structural changes are made  
**Maintainer**: Development team