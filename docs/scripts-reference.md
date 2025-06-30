# Scripts Reference - Home Inventory System

**Last Updated**: 2025-01-26  
**Version**: 1.0  
**Related**: [Main Runbook](../RUNBOOK.md) | [Testing Runbook](./testing-runbook.md)

This guide provides comprehensive documentation for all operational scripts in the Home Inventory System, including their purposes, usage patterns, and output interpretation.

---

## 📋 Scripts Overview

### Script Categories

1. **Diagnostic Scripts** - Environment validation and troubleshooting
2. **Test Runner Scripts** - Test execution with various approaches
3. **Verification Scripts** - Manual validation of specific functionality
4. **Setup Scripts** - Environment configuration and repair

### Quick Reference

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `diagnose_environment.py` | Environment diagnostics | Setup issues, test failures |
| `setup_test_environment.py` | Environment setup/repair | Initial setup, corruption |
| `run_tests_safe.py` | Safe test execution | Debugging, CI/CD |
| `verify_step_1_2a.py` | Database verification | Database troubleshooting |
| `verify_step_1_2b.py` | Location model verification | Model validation |
| `run_tests.py` | Primary test runner | Standard test execution |

---

## 🔍 Diagnostic Scripts

### `scripts/diagnose_environment.py`

**Purpose**: Comprehensive environment validation and troubleshooting

**Location**: `backend/scripts/diagnose_environment.py`

#### Usage

```bash
cd backend
python scripts/diagnose_environment.py
```

#### What It Does

Performs 8 comprehensive diagnostic checks:

1. **Working Directory Check**
   - Validates current directory location
   - Checks for required directories (`app/`, `tests/`)
   - Verifies configuration files exist

2. **Python Path and Imports**
   - Tests module import capability
   - Validates Python path configuration
   - Checks all application modules

3. **Virtual Environment Check**
   - Detects virtual environment status
   - Validates Python executable location
   - Provides activation guidance

4. **Dependencies Check**
   - Verifies all required packages installed
   - Checks package versions
   - Validates version compatibility

5. **SQLite Functionality Check**
   - Tests basic SQLite operations
   - Validates file-based database creation
   - Checks database permissions

6. **Async Functionality Check**
   - Tests async/await operations
   - Validates aiosqlite functionality
   - Checks async database operations

7. **Database Permissions Check**
   - Tests file system permissions
   - Validates read/write/delete operations
   - Checks database file management

8. **Pytest Configuration Check**
   - Validates pytest installation
   - Checks pytest-asyncio plugin
   - Tests test discovery functionality

#### Expected Output

```
🩺 Home Inventory System - Environment Diagnostics

============================================================
🔍 Working Directory Check
============================================================
✅ PASS Current Directory
✅ PASS App Directory Exists
✅ PASS Tests Directory Exists
✅ PASS Requirements File Exists

[... additional checks ...]

============================================================
🔍 Summary
============================================================
✅ Passed: 8/8 checks
🚀 Environment is ready for testing!
```

#### Output Interpretation

- **✅ PASS**: Check successful, no action needed
- **❌ FAIL**: Check failed, see recommendations section
- **Recommendations**: Specific solutions for failed checks

#### Troubleshooting

**If checks fail:**

1. **Follow provided recommendations** in script output
2. **Run setup script**: `python scripts/setup_test_environment.py`
3. **Check specific documentation** for failed areas

---

## 🔧 Setup Scripts

### `scripts/setup_test_environment.py`

**Purpose**: Automated environment setup and repair

**Location**: `backend/scripts/setup_test_environment.py`

#### Usage

```bash
cd backend
python scripts/setup_test_environment.py
```

#### What It Does

Performs 7 automated setup steps:

1. **Working Directory Setup**
   - Validates and navigates to correct directory
   - Provides guidance if backend directory not found

2. **Python Path Setup**
   - Configures Python path for imports
   - Tests module import capability

3. **Virtual Environment Check**
   - Detects virtual environment status
   - Provides activation instructions

4. **Dependencies Installation**
   - Upgrades pip to latest version
   - Installs all requirements from requirements-dev.txt
   - Handles installation failures gracefully

5. **Database Environment Setup**
   - Cleans up old database files
   - Tests database creation permissions
   - Validates SQLite functionality

6. **Pytest Configuration Setup**
   - Verifies pytest configuration
   - Checks plugin installations
   - Validates test discovery

7. **Basic Functionality Test**
   - Tests module imports
   - Validates database configuration
   - Runs basic functionality checks

#### Expected Output

```
🔧 Home Inventory System - Test Environment Setup

============================================================
🔧 Working Directory Setup
============================================================
✅ SUCCESS Directory Check

[... setup steps ...]

============================================================
🔧 Setup Summary
============================================================
✅ Working Directory
✅ Python Path
✅ Virtual Environment
✅ Dependencies
✅ Database Environment
✅ Pytest Configuration
✅ Basic Functionality

Results: 7/7 steps successful
🎉 Environment setup complete! You can now run tests
```

#### When to Use

- **Initial project setup**
- **Environment corruption recovery**
- **Dependency installation issues**
- **Before running diagnostics**

#### Troubleshooting

**If setup fails:**

1. **Virtual environment issues**: Ensure virtual environment is activated
2. **Permission errors**: Check file system permissions
3. **Network issues**: Verify internet connection for pip installs
4. **Disk space**: Ensure sufficient disk space available

---

## 🧪 Test Runner Scripts

### `run_tests.py`

**Purpose**: Primary test runner with Python path handling

**Location**: `backend/run_tests.py`

#### Usage

```bash
cd backend
python run_tests.py

# With additional pytest arguments
python run_tests.py -v --tb=short
```

#### What It Does

- **Sets PYTHONPATH** automatically for proper imports
- **Executes pytest** with configured parameters
- **Handles environment setup** transparently
- **Provides clean output** formatting

#### Expected Output

```
============================= test session starts ==============================
platform darwin -- Python 3.12.7, pytest-7.4.3
collected 17 items

tests/test_database_base.py::test_database_connection PASSED             [  5%]
tests/test_database_base.py::test_session_creation PASSED                [ 11%]
[... all tests ...]
tests/test_main.py::test_health_check PASSED                             [100%]

============================== 17 passed in 0.57s ==============================
```

#### Parameters

**Accepts all pytest parameters:**

```bash
# Verbose output
python run_tests.py -v

# Specific test file
python run_tests.py tests/test_location_model.py

# Stop on first failure
python run_tests.py -x

# Show local variables on failure
python run_tests.py --tb=long
```

### `scripts/run_tests_safe.py`

**Purpose**: Enhanced test runner with error handling

**Location**: `backend/scripts/run_tests_safe.py`

#### Usage

```bash
cd backend
python scripts/run_tests_safe.py
```

#### What It Does

- **Environment validation** before test execution
- **Enhanced error handling** for common failures
- **Graceful failure recovery** procedures
- **Detailed error reporting** with solutions

#### Expected Output

```
🧪 Safe Test Runner - Home Inventory System

============================================================
🔧 Environment Validation
============================================================
✅ SUCCESS Working Directory
✅ SUCCESS Python Path
✅ SUCCESS Dependencies

============================================================
🧪 Test Execution
============================================================
Running tests with enhanced error handling...

[... test results ...]

============================================================
📊 Test Summary
============================================================
✅ All tests passed successfully
Environment: Stable
Recommendation: Continue development
```

#### When to Use

- **CI/CD environments** where stability is critical
- **Debugging test failures** with enhanced error information
- **Unreliable environments** that need error recovery
- **Automated workflows** requiring robust execution

---

## ✅ Verification Scripts

### `scripts/verify_step_1_2a.py`

**Purpose**: Database foundation verification

**Location**: `backend/scripts/verify_step_1_2a.py`

#### Usage

```bash
cd backend
python scripts/verify_step_1_2a.py
```

#### What It Verifies

Performs 6 database foundation checks:

1. **Database Connection Test**
   - Tests SQLAlchemy engine connectivity
   - Validates basic SQL execution
   - Checks connection reliability

2. **Session Creation Test**
   - Validates AsyncSession factory
   - Tests session lifecycle management
   - Checks session configuration

3. **Table Operations Test**
   - Tests table creation from models
   - Validates table dropping functionality
   - Checks schema operations

4. **Database Configuration Test**
   - Validates database URL generation
   - Tests configuration management
   - Checks environment variables

5. **Base Functionality Test**
   - Tests SQLAlchemy Base operations
   - Validates model registration
   - Checks metadata consistency

6. **Async Operations Test**
   - Tests async/await functionality
   - Validates aiosqlite operations
   - Checks async session management

#### Expected Output

```
🗄️ Database Foundation Verification - Step 1.2a

============================================================
🗄️ Database Setup
============================================================
✅ PASS Create Tables

============================================================
🗄️ Database Connection Test
============================================================
✅ PASS Basic Connection
✅ PASS SQL Execution
✅ PASS Connection Reliability

[... additional tests ...]

============================================================
📊 Verification Summary
============================================================
✅ Database Connection
✅ Session Creation
✅ Table Operations
✅ Database Configuration
✅ Base Functionality
✅ Async Operations

Results: 6/6 tests passed
🎉 Database foundation is working correctly!
```

#### When to Use

- **After database setup changes**
- **Troubleshooting database connectivity**
- **Validating Step 1.2a completion**
- **Before proceeding to model development**

### `scripts/verify_step_1_2b.py`

**Purpose**: Location model functionality verification

**Location**: `backend/scripts/verify_step_1_2b.py`

#### Usage

```bash
cd backend
python scripts/verify_step_1_2b.py
```

#### What It Verifies

Performs 8 Location model checks:

1. **Location Creation Test**
   - Tests basic model instantiation
   - Validates field assignment
   - Checks database persistence
   - Verifies timestamp generation

2. **Location Types Test**
   - Tests all enum values (HOUSE, ROOM, CONTAINER, SHELF)
   - Validates enum assignment
   - Checks database enum storage

3. **String Representations Test**
   - Tests `__str__()` method
   - Validates `__repr__()` method
   - Checks formatting consistency

4. **Hierarchical Relationships Test**
   - Tests parent/child assignments
   - Validates bidirectional relationships
   - Checks relationship loading

5. **Full Path Generation Test**
   - Tests path string generation
   - Validates hierarchy traversal
   - Checks delimiter usage

6. **Depth Calculation Test**
   - Tests hierarchy depth tracking
   - Validates root node handling
   - Checks multi-level calculations

7. **Ancestor/Descendant Methods Test**
   - Tests relationship query methods
   - Validates traversal algorithms
   - Checks edge case handling

8. **Get Root Method Test**
   - Tests root location identification
   - Validates hierarchy traversal
   - Checks consistency across levels

#### Expected Output

```
🏠 Location Model Verification - Step 1.2b

============================================================
🏠 Database Setup
============================================================
✅ PASS Create Tables

============================================================
🏠 Location Creation Test
============================================================
✅ PASS ID Generated
✅ PASS Name Set
✅ PASS Description Set
✅ PASS Location Type Set
✅ PASS No Parent
✅ PASS Created At Set
✅ PASS Updated At Set

[... additional tests ...]

============================================================
🏠 Verification Summary
============================================================
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

#### When to Use

- **After Location model changes**
- **Validating Step 1.2b completion**
- **Troubleshooting model functionality**
- **Manual validation of hierarchical features**

---

## 🔧 Script Development Guidelines

### Adding New Scripts

When creating new scripts, follow these patterns:

#### Script Template

```python
#!/usr/bin/env python3
"""
Brief description of script purpose.

Usage details and when to run this script.
"""

import asyncio
import sys
import os

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"🔧 {title}")
    print(f"{'='*60}")

def print_result(check: str, success: bool, details: str = "") -> None:
    """Print a check result with colored output."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {check}")
    if details:
        print(f"    {details}")

async def main() -> None:
    """Main script execution."""
    print("🔧 Script Name - Purpose")
    print("Brief description of what this script does.")
    
    # Script implementation here
    
    print_section("Summary")
    print("Script execution complete.")

if __name__ == "__main__":
    asyncio.run(main())
```

#### Script Naming Convention

- **Diagnostic scripts**: `diagnose_*.py`
- **Setup scripts**: `setup_*.py`
- **Verification scripts**: `verify_*.py`
- **Utility scripts**: `util_*.py`

#### Documentation Requirements

Each script should include:

1. **Docstring** with purpose and usage
2. **Section headers** for clear output organization
3. **Result formatting** with consistent pass/fail indicators
4. **Error handling** with helpful error messages
5. **Summary section** with results and recommendations

### Script Integration

**Add new scripts to:**

1. **This reference guide** with complete documentation
2. **Main runbook** with usage examples
3. **Testing runbook** if test-related
4. **DEVELOPMENT_LOG.md** when completing development steps

---

## 🚨 Troubleshooting Script Issues

### Common Script Problems

#### Import Errors

**Symptom**: `ModuleNotFoundError: No module named 'app'`

**Solutions:**
```bash
# 1. Verify working directory
pwd  # Should end with /backend

# 2. Check script Python path setup
head -10 scripts/script_name.py  # Should have sys.path.insert

# 3. Run from correct directory
cd backend
python scripts/script_name.py
```

#### Permission Errors

**Symptom**: `Permission denied` when running scripts

**Solutions:**
```bash
# 1. Make script executable
chmod +x scripts/script_name.py

# 2. Run with python explicitly
python scripts/script_name.py

# 3. Check file ownership
ls -la scripts/script_name.py
```

#### Environment Issues

**Symptom**: Scripts fail with environment-related errors

**Solutions:**
```bash
# 1. Run environment diagnostics first
python scripts/diagnose_environment.py

# 2. Run environment setup
python scripts/setup_test_environment.py

# 3. Verify virtual environment
which python  # Should point to venv
```

### Script Output Interpretation

#### Success Indicators

- **✅ PASS** - Check completed successfully
- **🎉** - All checks completed successfully  
- **Results: X/X passed** - Perfect score achieved

#### Failure Indicators

- **❌ FAIL** - Check failed, see details
- **⚠️** - Warning, attention needed
- **💡 TIP** - Helpful guidance provided

#### Action Items

- **Recommendations section** - Specific solutions for failures
- **Next steps** - What to do after script completion
- **Error details** - Specific error information for debugging

---

## 📊 Script Performance

### Expected Execution Times

| Script | Expected Duration | Performance Notes |
|--------|------------------|-------------------|
| `diagnose_environment.py` | 2-5 seconds | Database I/O dependent |
| `setup_test_environment.py` | 10-30 seconds | Network dependent |
| `run_tests_safe.py` | 1-2 seconds | Test execution time |
| `verify_step_1_2a.py` | 1-3 seconds | Database operations |
| `verify_step_1_2b.py` | 2-5 seconds | Complex model operations |

### Performance Monitoring

```bash
# Time script execution
time python scripts/diagnose_environment.py

# Monitor resource usage
top  # While running resource-intensive scripts
```

### Performance Optimization

**If scripts are slow:**

1. **Check database file size**: `ls -la inventory.db`
2. **Verify virtual environment**: `which python`
3. **Monitor system resources**: `top`
4. **Reset environment**: `rm inventory.db && python scripts/setup_test_environment.py`

---

## 📞 Support and References

### Related Documentation

- **[Main Runbook](../RUNBOOK.md)** - Complete operational guide
- **[Testing Runbook](./testing-runbook.md)** - Comprehensive testing procedures
- **[Database Operations](./database-operations.md)** - Database management
- **[Development Workflow](./development-workflow.md)** - Development procedures

### Script Dependencies

**All scripts require:**
- Python 3.7+ with async support
- Virtual environment with requirements-dev.txt installed
- Backend directory as working directory
- Proper Python path configuration

### Getting Help

1. **Script-specific issues**: Check script output recommendations
2. **Environment problems**: Run `python scripts/diagnose_environment.py`
3. **Setup issues**: Run `python scripts/setup_test_environment.py`
4. **General questions**: Refer to main runbook troubleshooting section

---

**Last Updated**: 2025-01-26  
**Next Review**: When new scripts are added  
**Maintainer**: Development team