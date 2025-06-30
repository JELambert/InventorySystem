# Troubleshooting Playbook - Home Inventory System

**Last Updated**: 2025-01-26  
**Version**: 1.0  
**Related**: [Main Runbook](../RUNBOOK.md) | [Scripts Reference](./scripts-reference.md)

This comprehensive troubleshooting guide provides step-by-step solutions for common issues, diagnostic procedures, and recovery strategies for the Home Inventory System.

---

## 🔍 Quick Diagnostic Commands

### First-Line Diagnostics

```bash
# Run these commands first for any issue
cd backend
source venv/bin/activate
python scripts/diagnose_environment.py
python scripts/verify_step_1_2a.py
python scripts/verify_step_1_2b.py
python run_tests.py
```

### Emergency Recovery

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

## 🔧 Environment Issues

### Virtual Environment Problems

#### Problem: Virtual Environment Not Working

**Symptoms:**
- `command not found: python`
- Wrong Python version
- Import errors for installed packages

**Diagnosis:**
```bash
# Check if virtual environment is active
which python  # Should point to venv/bin/python

# Check Python version
python --version  # Should be 3.7+

# Check virtual environment status
echo $VIRTUAL_ENV  # Should show path to venv
```

**Solutions:**

**Option 1: Activate Existing Environment**
```bash
cd backend
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows
```

**Option 2: Recreate Virtual Environment**
```bash
cd backend
rm -rf venv/
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
```

**Option 3: Use System Python (Not Recommended)**
```bash
# Only if virtual environment cannot be created
cd backend
pip install --user -r requirements-dev.txt
export PYTHONPATH=.
python -m pytest tests/ -v
```

#### Problem: Pip Installation Failures

**Symptoms:**
- `error: Microsoft Visual C++ 14.0 is required`
- `Failed building wheel for package`
- Compilation errors during installation

**Diagnosis:**
```bash
# Check pip version
pip --version

# Check available packages
pip list

# Try installing individual packages
pip install fastapi
pip install sqlalchemy
```

**Solutions:**

**Option 1: Upgrade Pip and Tools**
```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements-dev.txt
```

**Option 2: Use Pre-compiled Packages**
```bash
# Install with binary wheels only
pip install --only-binary=all -r requirements-dev.txt
```

**Option 3: Use Docker Environment**
```bash
# From project root
docker-compose -f backend/docker-compose.dev.yml up --build
```

**Option 4: Install Dependencies Individually**
```bash
# Core packages first
pip install fastapi==0.104.1
pip install uvicorn[standard]==0.24.0
pip install sqlalchemy==2.0.21
pip install aiosqlite==0.19.0
pip install pytest==7.4.3
pip install pytest-asyncio==0.21.1

# Continue with remaining packages
```

### Python Path and Import Issues

#### Problem: Module Import Errors

**Symptoms:**
- `ModuleNotFoundError: No module named 'app'`
- `ImportError: attempted relative import with no known parent package`

**Diagnosis:**
```bash
# Check current directory
pwd  # Should end with /backend

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Test import manually
python -c "import app; print('Import successful')"
```

**Solutions:**

**Option 1: Use Primary Test Runner**
```bash
cd backend
python run_tests.py  # Handles Python path automatically
```

**Option 2: Set Python Path Manually**
```bash
cd backend
export PYTHONPATH=.
python -m pytest tests/ -v
```

**Option 3: Use Scripts (Recommended)**
```bash
# Scripts handle Python path automatically
python scripts/diagnose_environment.py
python scripts/verify_step_1_2b.py
```

**Option 4: Check Working Directory**
```bash
# Ensure you're in the correct directory
cd /path/to/InventorySystem/backend
pwd  # Should end with /backend
ls   # Should see app/, tests/, scripts/
```

---

## 🗄️ Database Issues

### Database Connection Problems

#### Problem: Cannot Connect to Database

**Symptoms:**
- `sqlite3.OperationalError: unable to open database file`
- `sqlalchemy.exc.OperationalError`
- Database connection timeouts

**Diagnosis:**
```bash
cd backend

# Test basic database connection
python scripts/verify_step_1_2a.py

# Check database file
ls -la inventory.db

# Test SQLite directly
sqlite3 inventory.db .tables
```

**Solutions:**

**Option 1: Database File Issues**
```bash
# Check file permissions
ls -la inventory.db
chmod 644 inventory.db  # If permission issue

# Recreate database file
rm inventory.db
python -c "from app.database.base import create_tables; import asyncio; asyncio.run(create_tables())"
```

**Option 2: Directory Permissions**
```bash
# Check directory permissions
ls -la .
chmod 755 .  # If needed

# Test database creation in current directory
touch test_file.db
rm test_file.db
```

**Option 3: Complete Database Reset**
```bash
rm inventory.db
python scripts/setup_test_environment.py
python scripts/verify_step_1_2a.py
```

#### Problem: Database Schema Errors

**Symptoms:**
- `sqlite3.OperationalError: no such table`
- `sqlalchemy.exc.ProgrammingError`
- Table does not exist errors

**Diagnosis:**
```bash
# Check existing tables
sqlite3 inventory.db .tables

# Check table schema
sqlite3 inventory.db .schema

# Test table creation
python -c "
from app.database.base import create_tables
import asyncio
asyncio.run(create_tables())
print('Tables created successfully')
"
```

**Solutions:**

**Option 1: Recreate Tables**
```bash
python -c "
from app.database.base import drop_tables, create_tables
import asyncio
async def recreate():
    await drop_tables()
    await create_tables()
    print('Tables recreated')
asyncio.run(recreate())
"
```

**Option 2: Check Model Imports**
```bash
# Verify models are imported in base.py
grep -r "from app.models" app/database/base.py

# Test model import
python -c "from app.models.location import Location; print('Location model imported')"
```

**Option 3: Database File Corruption**
```bash
# Check database integrity
sqlite3 inventory.db "PRAGMA integrity_check;"

# If corrupted, recreate
rm inventory.db
python scripts/setup_test_environment.py
```

### Database Performance Issues

#### Problem: Slow Database Operations

**Symptoms:**
- Tests running very slowly
- Database operations timing out
- High CPU usage during database operations

**Diagnosis:**
```bash
# Check database file size
ls -lh inventory.db

# Check for database locks
lsof inventory.db

# Enable SQL logging
python -c "
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
from app.database.base import check_connection
import asyncio
print(asyncio.run(check_connection()))
"
```

**Solutions:**

**Option 1: Database Maintenance**
```bash
# Vacuum database
sqlite3 inventory.db "VACUUM;"

# Analyze database
sqlite3 inventory.db "ANALYZE;"
```

**Option 2: Check System Resources**
```bash
# Monitor system resources
top
df -h  # Check disk space
```

**Option 3: Reset Database**
```bash
# If database is too large or corrupted
rm inventory.db
python scripts/setup_test_environment.py
```

---

## 🧪 Testing Issues

### Test Execution Failures

#### Problem: Tests Not Running

**Symptoms:**
- `pytest: command not found`
- No tests collected
- Import errors in test files

**Diagnosis:**
```bash
# Check pytest installation
python -m pytest --version

# Check test discovery
python -m pytest --collect-only tests/

# Check test file existence
ls tests/
```

**Solutions:**

**Option 1: Use Primary Test Runner**
```bash
cd backend
python run_tests.py
```

**Option 2: Install Missing Dependencies**
```bash
pip install pytest pytest-asyncio
python -m pytest tests/ -v
```

**Option 3: Test Individual Files**
```bash
# Test specific file
PYTHONPATH=. python -m pytest tests/test_location_model.py -v

# Test with maximum verbosity
PYTHONPATH=. python -m pytest tests/ -vvv
```

#### Problem: Test Failures

**Symptoms:**
- Specific tests failing
- SQLAlchemy session errors
- Async operation failures

**Diagnosis:**
```bash
# Run tests with detailed output
PYTHONPATH=. python -m pytest tests/ -v --tb=long

# Run single failing test
PYTHONPATH=. python -m pytest tests/test_file.py::test_function -v

# Check test environment
python scripts/diagnose_environment.py
```

**Solutions:**

**Option 1: Session-Related Failures**
```bash
# Remove database and retry
rm inventory.db
python run_tests.py

# Use manual verification instead
python scripts/verify_step_1_2b.py
```

**Option 2: Async-Related Failures**
```bash
# Check pytest-asyncio installation
pip list | grep pytest-asyncio

# Verify pytest.ini configuration
cat pytest.ini | grep asyncio

# Reinstall async dependencies
pip install pytest-asyncio==0.21.1
```

**Option 3: Environment Issues**
```bash
# Complete environment reset
python scripts/setup_test_environment.py
python run_tests.py
```

### Test Environment Issues

#### Problem: Test Database Issues

**Symptoms:**
- Tests affecting each other
- Database state persistence between tests
- SQLAlchemy connection pool errors

**Diagnosis:**
```bash
# Check test isolation
PYTHONPATH=. python -m pytest tests/test_location_model.py::test_location_creation -v
PYTHONPATH=. python -m pytest tests/test_location_model.py::test_location_creation -v  # Run again

# Check database file during tests
ls -la inventory.db  # Should not be affected by tests
```

**Solutions:**

**Option 1: Test Isolation**
```bash
# Tests should use in-memory databases
# Check test helper function usage in test files

# Manual verification for real database testing
python scripts/verify_step_1_2b.py
```

**Option 2: Clean Test Environment**
```bash
# Ensure no test artifacts
rm -f test*.db
rm inventory.db
python run_tests.py
```

---

## 🎯 Code Quality Issues

### Formatting and Linting Problems

#### Problem: Black and Flake8 Conflicts

**Symptoms:**
- Black formats code that flake8 complains about
- Line length conflicts
- Import ordering issues

**Diagnosis:**
```bash
# Check black configuration
black --check .

# Check flake8 configuration
flake8 --version
cat .flake8

# Test on specific file
black app/models/location.py
flake8 app/models/location.py
```

**Solutions:**

**Option 1: Run Black First**
```bash
# Black takes precedence over flake8
black .
flake8  # Should pass after black formatting
```

**Option 2: Check Configuration**
```bash
# Verify .flake8 configuration
cat .flake8
# Should have:
# max-line-length = 88
# extend-ignore = E203, W503
```

**Option 3: Manual Fix**
```bash
# Fix specific issues
black specific_file.py
flake8 specific_file.py
# Address remaining issues manually
```

#### Problem: MyPy Type Checking Errors

**Symptoms:**
- Type annotation errors
- SQLAlchemy-related type errors
- Import-related type errors

**Diagnosis:**
```bash
# Check mypy version
mypy --version

# Check specific file
mypy app/models/location.py

# Check with error codes
mypy app/ --show-error-codes
```

**Solutions:**

**Option 1: SQLAlchemy Warnings (Acceptable)**
```bash
# Minor SQLAlchemy warnings are acceptable
# Focus on fixing critical errors only
mypy app/ | grep -E "(error|Error)"
```

**Option 2: Fix Type Annotations**
```python
# Common fixes:
from typing import Optional, List
from sqlalchemy.orm import Mapped

# Use proper SQLAlchemy 2.0 patterns
name: Mapped[str] = mapped_column(String(255))
parent: Mapped[Optional["Location"]] = relationship(...)
```

**Option 3: Configuration Issues**
```bash
# Check if mypy configuration exists
ls -la mypy.ini pyproject.toml

# Check installed packages
pip list | grep mypy
```

---

## 🚀 Application Runtime Issues

### FastAPI Server Problems

#### Problem: Server Won't Start

**Symptoms:**
- `uvicorn: command not found`
- Port already in use errors
- Import errors when starting server

**Diagnosis:**
```bash
# Check uvicorn installation
uvicorn --version

# Check port availability
lsof -i :8000  # Check if port 8000 is in use

# Test import manually
python -c "from app.main import app; print('Import successful')"
```

**Solutions:**

**Option 1: Install Missing Dependencies**
```bash
pip install uvicorn[standard]==0.24.0
uvicorn app.main:app --reload --port 8000
```

**Option 2: Use Different Port**
```bash
uvicorn app.main:app --reload --port 8001
```

**Option 3: Kill Existing Process**
```bash
# Find and kill process using port 8000
lsof -ti:8000 | xargs kill -9
uvicorn app.main:app --reload --port 8000
```

#### Problem: API Endpoints Not Working

**Symptoms:**
- 404 errors for API endpoints
- 500 internal server errors
- Database connection errors in API

**Diagnosis:**
```bash
# Test server manually
curl http://localhost:8000/
curl http://localhost:8000/health
curl http://localhost:8000/docs

# Check server logs
uvicorn app.main:app --reload --port 8000  # Check console output
```

**Solutions:**

**Option 1: Test Basic Endpoints**
```bash
# Ensure basic endpoints work first
PYTHONPATH=. python -m pytest tests/test_main.py -v
```

**Option 2: Check Database Connection**
```bash
# Verify database connectivity
python scripts/verify_step_1_2a.py
```

**Option 3: Debug Import Issues**
```bash
# Test imports
python -c "
from app.main import app
from app.database.base import check_connection
print('Imports successful')
"
```

---

## 🔄 Development Workflow Issues

### Git and Version Control Problems

#### Problem: Git Repository Issues

**Symptoms:**
- Git commands not working
- Merge conflicts
- Untracked files

**Diagnosis:**
```bash
# Check git status
git status

# Check git configuration
git config --list

# Check remote repositories
git remote -v
```

**Solutions:**

**Option 1: Initialize Repository (If Needed)**
```bash
# Only if git repository not initialized
cd /path/to/InventorySystem
git init
git add .
git commit -m "Initial commit"
```

**Option 2: Handle Merge Conflicts**
```bash
# Check conflicted files
git status
# Manually resolve conflicts in files
git add .
git commit -m "Resolve merge conflicts"
```

**Option 3: Clean Working Directory**
```bash
# Clean untracked files (be careful!)
git clean -n  # Preview what will be removed
git clean -f  # Actually remove untracked files
```

### Documentation Issues

#### Problem: Documentation Out of Date

**Symptoms:**
- Runbooks don't match current procedures
- DEVELOPMENT_LOG.md missing recent changes
- Inconsistent documentation

**Diagnosis:**
```bash
# Check documentation dates
ls -la *.md docs/*.md

# Check for TODO or FIXME in documentation
grep -r "TODO\|FIXME" *.md docs/
```

**Solutions:**

**Option 1: Update Documentation**
```bash
# Update relevant files
# DEVELOPMENT_LOG.md
# RUNBOOK.md
# docs/ files
```

**Option 2: Verify Procedures**
```bash
# Test procedures documented in runbooks
# Follow step-by-step instructions
# Update if procedures have changed
```

---

## 🚨 Emergency Recovery Procedures

### Complete System Recovery

#### When Everything Is Broken

**Symptoms:**
- Multiple systems failing
- Cannot run any scripts
- Environment completely corrupted

**Recovery Steps:**

1. **Backup Current State**
```bash
cd /path/to/InventorySystem
cp -r backend backend_backup_$(date +%Y%m%d_%H%M%S)
```

2. **Fresh Environment Setup**
```bash
cd backend
deactivate  # If virtual environment active
rm -rf venv/
rm inventory.db
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

3. **Install Dependencies**
```bash
pip install -r requirements-dev.txt
# If this fails, install core packages individually:
pip install fastapi uvicorn sqlalchemy aiosqlite pytest
```

4. **Verify Core Functionality**
```bash
python scripts/setup_test_environment.py
python scripts/diagnose_environment.py
python run_tests.py
```

5. **Restore Data (If Needed)**
```bash
# If you had important data
cp backup/inventory.db ./inventory.db
python scripts/verify_step_1_2a.py
```

### Data Recovery

#### Database Corruption Recovery

**If database is corrupted:**

1. **Backup Corrupted Database**
```bash
cp inventory.db inventory_corrupted_$(date +%Y%m%d_%H%M%S).db
```

2. **Attempt Repair**
```bash
# Try SQLite repair
sqlite3 inventory.db "PRAGMA integrity_check;"
sqlite3 inventory.db ".recover" | sqlite3 inventory_recovered.db
```

3. **Recreate from Scratch**
```bash
rm inventory.db
python scripts/setup_test_environment.py
python scripts/verify_step_1_2a.py
```

4. **Manual Data Recreation**
```bash
# Recreate important data manually
python -c "
from app.database.base import async_session
from app.models.location import Location, LocationType
import asyncio

async def recreate_data():
    # Add your data recreation code here
    pass

asyncio.run(recreate_data())
"
```

---

## 📊 Diagnostic Tools and Scripts

### Custom Diagnostic Scripts

#### Create Custom Diagnostic

**For specific issues, create targeted diagnostic scripts:**

```python
#!/usr/bin/env python3
"""
Custom diagnostic script for specific issue.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def diagnose_specific_issue():
    """Diagnose specific issue."""
    print("🔍 Custom Diagnostic Script")
    
    # Add specific diagnostic code here
    try:
        # Test specific functionality
        print("✅ PASS Custom check")
        return True
    except Exception as e:
        print(f"❌ FAIL Custom check: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(diagnose_specific_issue())
    sys.exit(0 if result else 1)
```

### Monitoring and Logging

#### Enable Detailed Logging

```python
# Add to any Python script for detailed logging
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable SQLAlchemy logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
logging.getLogger('sqlalchemy.pool').setLevel(logging.DEBUG)
```

#### Performance Monitoring

```bash
# Monitor system resources during operations
top &
python run_tests.py
kill %1  # Stop top

# Time operations
time python run_tests.py
time python scripts/verify_step_1_2b.py
```

---

## 📞 Support and Escalation

### When to Seek Help

**Seek additional help when:**
- Following this playbook doesn't resolve the issue
- System is completely unrecoverable
- Data loss has occurred
- Security concerns arise

### Information to Gather

**Before seeking help, gather:**

1. **Environment Information**
```bash
python --version
pip list
uname -a  # System information
df -h     # Disk space
```

2. **Error Details**
```bash
# Exact error messages
# Steps that led to the error
# What you've tried from this playbook
```

3. **System State**
```bash
python scripts/diagnose_environment.py > diagnostic_output.txt
python run_tests.py > test_output.txt 2>&1
```

### Recovery Documentation

**Document any custom solutions:**
- Update this troubleshooting playbook
- Add to DEVELOPMENT_LOG.md
- Share with team for future reference

---

## 📈 Prevention and Best Practices

### Preventing Common Issues

1. **Regular Environment Validation**
```bash
# Run weekly
python scripts/diagnose_environment.py
```

2. **Regular Backups**
```bash
# Backup database regularly
cp inventory.db backup/inventory_$(date +%Y%m%d).db
```

3. **Documentation Maintenance**
```bash
# Keep documentation current
# Update after any process changes
# Review monthly for accuracy
```

4. **Proactive Monitoring**
```bash
# Monitor key metrics
# Check test pass rates
# Monitor performance trends
```

### Best Practices

1. **Environment Management**
   - Always use virtual environments
   - Keep requirements files updated
   - Regular dependency updates

2. **Testing Strategy**
   - Run tests before major changes
   - Use manual verification for complex workflows
   - Test in clean environment regularly

3. **Code Quality**
   - Run quality checks before commits
   - Fix issues immediately when found
   - Maintain consistent coding standards

4. **Documentation**
   - Update documentation with changes
   - Keep troubleshooting solutions documented
   - Share knowledge with team

---

**Last Updated**: 2025-01-26  
**Next Review**: When new issues are discovered and resolved  
**Maintainer**: Development team