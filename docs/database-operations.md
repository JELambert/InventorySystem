# Database Operations Runbook - Home Inventory System

**Last Updated**: 2025-01-26  
**Version**: 1.0  
**Related**: [Main Runbook](../RUNBOOK.md) | [Testing Runbook](./testing-runbook.md)

This guide provides comprehensive procedures for database management, operations, and maintenance in the Home Inventory System.

---

## 🗄️ Database Overview

### Current Database Architecture

**Development Environment:**
- **Database Type**: PostgreSQL 17.5
- **Host**: 192.168.68.88:5432 (Proxmox LXC)
- **Database**: inventory_system
- **Connection**: Async via asyncpg
- **ORM**: SQLAlchemy 2.0 with async support

**Testing Environment:**
- **Database Type**: In-memory SQLite
- **Lifecycle**: Created/destroyed per test
- **Isolation**: Each test gets fresh database
- **Note**: Tests automatically use SQLite for speed and isolation

**Production:**
- **Database Type**: PostgreSQL 17.5
- **Connection**: Same as development
- **Migration**: Alembic schema versioning
- **Deployment**: Proxmox LXC container

### Database Configuration

**Connection String Patterns:**
```python
# Development & Production
DATABASE_URL = "postgresql+asyncpg://postgres:vaultlock1@192.168.68.88:5432/inventory_system"

# Testing (automatic fallback)
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Local SQLite fallback (if PostgreSQL unavailable)
DATABASE_URL = "sqlite+aiosqlite:///./data/inventory.db"
```

**Environment Variables:**
```bash
# PostgreSQL connection (development & production)
POSTGRES_HOST=192.168.68.88
POSTGRES_PORT=5432
POSTGRES_DB=inventory_system
POSTGRES_USER=postgres
POSTGRES_PASSWORD=vaultlock1

# Alternative: Full database URL override
DATABASE_URL=postgresql+asyncpg://postgres:vaultlock1@192.168.68.88:5432/inventory_system
```

---

## 📋 Current Database Schema

### Tables Overview

#### `locations` Table

**Purpose**: Hierarchical location structure for inventory organization

**Schema:**
```sql
CREATE TABLE locations (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    location_type VARCHAR(9) NOT NULL,
    parent_id INTEGER REFERENCES locations(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Indexes
CREATE INDEX ix_locations_id ON locations (id);
CREATE INDEX ix_locations_name ON locations (name);
CREATE INDEX ix_locations_location_type ON locations (location_type);
CREATE INDEX ix_locations_parent_id ON locations (parent_id);
```

**Fields:**
- `id`: Primary key, auto-increment
- `name`: Location name (max 255 chars), indexed
- `description`: Optional detailed description
- `location_type`: Enum (HOUSE, ROOM, CONTAINER, SHELF), indexed
- `parent_id`: Self-referential foreign key, indexed, cascade delete
- `created_at`: Automatic timestamp on creation
- `updated_at`: Automatic timestamp on modification

**Relationships:**
- **Self-referential**: `parent_id` → `locations.id`
- **Cascade**: Deleting parent deletes all children
- **Bidirectional**: Parent has children collection, child has parent reference

**Constraints:**
- NOT NULL: id, name, location_type, created_at, updated_at
- FOREIGN KEY: parent_id references locations(id) with cascade delete
- CHECK: location_type IN ('HOUSE', 'ROOM', 'CONTAINER', 'SHELF')

---

## 🚀 Basic Database Operations

### Database Creation and Setup

#### Automatic Creation

Database is created automatically on first application run:

```bash
cd backend
python -c "from app.database.base import create_tables; import asyncio; asyncio.run(create_tables())"
```

#### Manual Database Verification

```bash
# Comprehensive database verification
cd backend
python scripts/verify_step_1_2a.py
```

**Expected output:**
```
✅ Database Connection
✅ Session Creation
✅ Table Operations
✅ Database Configuration
✅ Base Functionality
✅ Async Operations

Results: 6/6 tests passed
🎉 Database foundation is working correctly!
```

### Database Inspection

#### File System Operations

```bash
# Check database file
cd backend
ls -la inventory.db

# View file size
du -h inventory.db

# File permissions
stat inventory.db
```

#### SQLite Command Line Interface

```bash
# Open database in SQLite CLI
cd backend
sqlite3 inventory.db

# Within SQLite CLI:
.tables                    # List all tables
.schema locations         # Show table schema
SELECT * FROM locations;  # View all data
.quit                     # Exit CLI
```

#### Programmatic Inspection

```python
# Database connection test
cd backend
python -c "
from app.database.base import check_connection
import asyncio
result = asyncio.run(check_connection())
print(f'Database connection: {result}')
"

# Table inspection
python -c "
from app.database.base import engine
from sqlalchemy import text
import asyncio

async def inspect():
    async with engine.begin() as conn:
        result = await conn.execute(text('SELECT name FROM sqlite_master WHERE type=\"table\"'))
        tables = result.fetchall()
        print(f'Tables: {[t[0] for t in tables]}')

asyncio.run(inspect())
"
```

---

## 🔧 Database Maintenance

### Database Reset and Cleanup

#### Complete Database Reset

```bash
cd backend

# Method 1: Delete database file
rm inventory.db

# Method 2: Programmatic drop and recreate
python -c "
from app.database.base import drop_tables, create_tables
import asyncio

async def reset():
    await drop_tables()
    await create_tables()
    print('Database reset complete')

asyncio.run(reset())
"
```

#### Selective Table Operations

```python
# Drop all tables
python -c "
from app.database.base import drop_tables
import asyncio
asyncio.run(drop_tables())
print('All tables dropped')
"

# Create all tables
python -c "
from app.database.base import create_tables
import asyncio
asyncio.run(create_tables())
print('All tables created')
"
```

### Database Backup and Restore

#### Backup Operations

```bash
cd backend

# Simple file copy backup
cp inventory.db inventory_backup_$(date +%Y%m%d_%H%M%S).db

# SQLite dump backup
sqlite3 inventory.db .dump > inventory_backup_$(date +%Y%m%d_%H%M%S).sql

# Compressed backup
sqlite3 inventory.db .dump | gzip > inventory_backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

#### Restore Operations

```bash
cd backend

# Restore from file copy
cp inventory_backup_20250126_123000.db inventory.db

# Restore from SQL dump
sqlite3 inventory.db < inventory_backup_20250126_123000.sql

# Restore from compressed dump
gunzip -c inventory_backup_20250126_123000.sql.gz | sqlite3 inventory.db
```

### Database Migration (Future)

When Alembic is implemented:

```bash
# Generate migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Downgrade migration
alembic downgrade -1

# Migration history
alembic history
```

---

## 📊 Data Operations

### Location Data Management

#### Creating Locations

```python
# Interactive location creation
cd backend
python -c "
from app.database.base import async_session
from app.models.location import Location, LocationType
import asyncio

async def create_sample_data():
    async with async_session() as session:
        # Create house
        house = Location(
            name='My House',
            location_type=LocationType.HOUSE,
            description='Main residence'
        )
        session.add(house)
        await session.commit()
        await session.refresh(house)
        
        # Create room
        room = Location(
            name='Living Room',
            location_type=LocationType.ROOM,
            parent_id=house.id,
            description='Main living area'
        )
        session.add(room)
        await session.commit()
        await session.refresh(room)
        
        print(f'Created: {house}')
        print(f'Created: {room}')
        print(f'Room path: {room.full_path}')

asyncio.run(create_sample_data())
"
```

#### Querying Locations

```python
# Location queries
cd backend
python -c "
from app.database.base import async_session
from app.models.location import Location, LocationType
from sqlalchemy import select
import asyncio

async def query_locations():
    async with async_session() as session:
        # Get all locations
        result = await session.execute(select(Location))
        all_locations = result.scalars().all()
        print(f'Total locations: {len(all_locations)}')
        
        # Get by type
        result = await session.execute(
            select(Location).where(Location.location_type == LocationType.HOUSE)
        )
        houses = result.scalars().all()
        print(f'Houses: {len(houses)}')
        
        # Get root locations (no parent)
        result = await session.execute(
            select(Location).where(Location.parent_id.is_(None))
        )
        roots = result.scalars().all()
        print(f'Root locations: {len(roots)}')
        
        for location in all_locations:
            print(f'  {location.full_path} ({location.location_type.value})')

asyncio.run(query_locations())
"
```

#### Updating Locations

```python
# Location updates
cd backend
python -c "
from app.database.base import async_session
from app.models.location import Location
from sqlalchemy import select
import asyncio

async def update_location():
    async with async_session() as session:
        # Find location by name
        result = await session.execute(
            select(Location).where(Location.name == 'Living Room')
        )
        location = result.scalar_one_or_none()
        
        if location:
            location.description = 'Updated description'
            await session.commit()
            print(f'Updated: {location}')
        else:
            print('Location not found')

asyncio.run(update_location())
"
```

#### Deleting Locations

```python
# Location deletion (with cascade)
cd backend
python -c "
from app.database.base import async_session
from app.models.location import Location
from sqlalchemy import select
import asyncio

async def delete_location():
    async with async_session() as session:
        # Find location by name
        result = await session.execute(
            select(Location).where(Location.name == 'My House')
        )
        location = result.scalar_one_or_none()
        
        if location:
            # This will cascade delete all children
            await session.delete(location)
            await session.commit()
            print(f'Deleted: {location} (and all children)')
        else:
            print('Location not found')

asyncio.run(delete_location())
"
```

---

## 🧪 Database Testing

### Test Database Operations

#### Running Database Tests

```bash
cd backend

# All database tests
PYTHONPATH=. python -m pytest tests/test_database_base.py -v

# Specific database test
PYTHONPATH=. python -m pytest tests/test_database_base.py::test_database_connection -v

# Location model tests
PYTHONPATH=. python -m pytest tests/test_location_model.py -v
```

#### Manual Database Verification

```bash
# Database foundation verification
python scripts/verify_step_1_2a.py

# Location model verification
python scripts/verify_step_1_2b.py
```

### Test Database Management

#### Test Database Lifecycle

**Test databases are:**
- Created fresh for each test
- In-memory SQLite (no file system impact)
- Automatically cleaned up after test completion
- Isolated between tests

#### Test Database Debugging

```python
# Debug test database state
cd backend
python -c "
from app.database.base import create_tables, drop_tables, async_session
from app.models.location import Location, LocationType
import asyncio

async def debug_test_db():
    # Create test database
    await create_tables()
    
    async with async_session() as session:
        # Create test data
        location = Location(
            name='Test Location',
            location_type=LocationType.HOUSE
        )
        session.add(location)
        await session.commit()
        await session.refresh(location)
        
        print(f'Test location created: {location}')
        print(f'Location ID: {location.id}')
        print(f'Created at: {location.created_at}')
    
    # Cleanup
    await drop_tables()
    print('Test database cleaned up')

asyncio.run(debug_test_db())
"
```

---

## 🔍 Database Diagnostics

### Performance Monitoring

#### Query Performance

```python
# Enable SQL logging for development
cd backend
python -c "
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

from app.database.base import async_session
from app.models.location import Location
from sqlalchemy import select
import asyncio

async def monitor_queries():
    async with async_session() as session:
        result = await session.execute(select(Location))
        locations = result.scalars().all()
        print(f'Fetched {len(locations)} locations')

asyncio.run(monitor_queries())
"
```

#### Database Size Monitoring

```bash
cd backend

# Database file size
ls -lh inventory.db

# Detailed size information
sqlite3 inventory.db "
SELECT 
    name,
    COUNT(*) as row_count
FROM sqlite_master sm
LEFT JOIN pragma_table_info(sm.name) pti ON 1=1
WHERE sm.type = 'table'
GROUP BY name;
"

# Database statistics
sqlite3 inventory.db "
SELECT 
    'Database Size (bytes)' as metric,
    page_count * page_size as value
FROM pragma_page_count(), pragma_page_size()
UNION ALL
SELECT 
    'Page Count' as metric,
    page_count as value
FROM pragma_page_count()
UNION ALL
SELECT 
    'Page Size' as metric,
    page_size as value
FROM pragma_page_size();
"
```

### Health Checks

#### Database Health Verification

```bash
cd backend

# Comprehensive health check
python scripts/diagnose_environment.py

# Database-specific health check
python -c "
from app.database.base import check_connection, create_tables, drop_tables
import asyncio

async def health_check():
    print('=== Database Health Check ===')
    
    # Connection test
    connected = await check_connection()
    print(f'Connection: {'✅' if connected else '❌'}')
    
    # Table operations test
    try:
        await create_tables()
        await drop_tables()
        print('Table operations: ✅')
    except Exception as e:
        print(f'Table operations: ❌ {e}')
    
    print('Health check complete')

asyncio.run(health_check())
"
```

#### Data Integrity Checks

```python
# Check data integrity
cd backend
python -c "
from app.database.base import async_session
from app.models.location import Location
from sqlalchemy import select, func
import asyncio

async def integrity_check():
    async with async_session() as session:
        # Check for orphaned locations (parent_id points to non-existent parent)
        result = await session.execute(
            select(Location)
            .where(Location.parent_id.isnot(None))
            .where(~Location.parent_id.in_(
                select(Location.id)
            ))
        )
        orphaned = result.scalars().all()
        
        if orphaned:
            print(f'❌ Found {len(orphaned)} orphaned locations')
            for loc in orphaned:
                print(f'  - {loc.name} (parent_id: {loc.parent_id})')
        else:
            print('✅ No orphaned locations found')
        
        # Check for circular references
        result = await session.execute(select(Location))
        all_locations = result.scalars().all()
        
        circular_refs = []
        for location in all_locations:
            visited = set()
            current = location
            while current and current.parent_id:
                if current.id in visited:
                    circular_refs.append(location)
                    break
                visited.add(current.id)
                # Get parent
                parent_result = await session.execute(
                    select(Location).where(Location.id == current.parent_id)
                )
                current = parent_result.scalar_one_or_none()
        
        if circular_refs:
            print(f'❌ Found {len(circular_refs)} circular references')
            for loc in circular_refs:
                print(f'  - {loc.name}')
        else:
            print('✅ No circular references found')

asyncio.run(integrity_check())
"
```

---

## 🔧 Troubleshooting Database Issues

### Common Database Problems

#### Connection Issues

**Symptom**: Cannot connect to database

**Diagnosis:**
```bash
cd backend
python scripts/verify_step_1_2a.py
```

**Solutions:**
```bash
# 1. Check database file permissions
ls -la inventory.db

# 2. Verify working directory
pwd  # Should end with /backend

# 3. Check virtual environment
which python  # Should point to venv

# 4. Reset database
rm inventory.db
python -c "from app.database.base import create_tables; import asyncio; asyncio.run(create_tables())"
```

#### Schema Issues

**Symptom**: Table does not exist or schema errors

**Diagnosis:**
```bash
# Check table existence
sqlite3 inventory.db .tables

# Check table schema
sqlite3 inventory.db .schema
```

**Solutions:**
```bash
# 1. Recreate tables
python -c "
from app.database.base import drop_tables, create_tables
import asyncio
async def recreate():
    await drop_tables()
    await create_tables()
asyncio.run(recreate())
"

# 2. Complete database reset
rm inventory.db
python scripts/verify_step_1_2a.py
```

#### Performance Issues

**Symptom**: Slow database operations

**Diagnosis:**
```bash
# Check database file size
ls -lh inventory.db

# Check for locks
lsof inventory.db

# Enable SQL logging
python -c "
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
# Then run your operations
"
```

**Solutions:**
```bash
# 1. Database cleanup
sqlite3 inventory.db "VACUUM;"

# 2. Check indexes
sqlite3 inventory.db ".schema locations"

# 3. Reset if corrupted
rm inventory.db
python scripts/setup_test_environment.py
```

#### Data Corruption

**Symptom**: Unexpected data or integrity errors

**Diagnosis:**
```bash
# SQLite integrity check
sqlite3 inventory.db "PRAGMA integrity_check;"

# Check data consistency
python -c "
# Run integrity check script from above
"
```

**Solutions:**
```bash
# 1. Database backup and restore
cp inventory.db inventory_corrupted.db
sqlite3 inventory.db .dump | sqlite3 inventory_new.db
mv inventory_new.db inventory.db

# 2. Complete rebuild
rm inventory.db
# Recreate and reload data

# 3. Restore from backup
cp inventory_backup.db inventory.db
```

---

## 📈 Future Database Considerations

### Migration to PostgreSQL

**Planned changes:**
- Connection string updates
- AsyncPG driver implementation
- Connection pooling configuration
- Environment-specific settings

**Migration strategy:**
```bash
# Export data from SQLite
sqlite3 inventory.db .dump > migration_data.sql

# Convert to PostgreSQL format (future)
# Load into PostgreSQL instance
```

### Alembic Migration System

**Implementation plan:**
- Initialize Alembic configuration
- Create initial migration from current schema
- Set up migration automation
- Version control integration

**Commands (future):**
```bash
# Initialize migrations
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head
```

### Performance Optimization

**Future enhancements:**
- Query optimization analysis
- Index performance monitoring
- Connection pool tuning
- Read replica configuration

---

## 📞 Support and References

### Related Documentation

- **[Main Runbook](../RUNBOOK.md)** - Complete operational guide
- **[Testing Runbook](./testing-runbook.md)** - Database testing procedures
- **[Scripts Reference](./scripts-reference.md)** - Database-related scripts

### External References

- **SQLAlchemy Documentation**: https://docs.sqlalchemy.org/en/20/
- **Aiosqlite Documentation**: https://aiosqlite.omnilib.dev/
- **SQLite Documentation**: https://www.sqlite.org/docs.html
- **Alembic Documentation**: https://alembic.sqlalchemy.org/

### Database Schema Reference

**Current Models:**
- `Location` - Hierarchical location structure

**Planned Models:**
- `Category` - Item categorization
- `Item` - Inventory items
- `User` - Authentication (future)

---

**Last Updated**: 2025-01-26  
**Next Review**: When new models are added  
**Maintainer**: Development team