# Development Workflow Runbook - Home Inventory System

**Last Updated**: 2025-01-26  
**Version**: 1.0  
**Related**: [Main Runbook](../RUNBOOK.md) | [Testing Runbook](./testing-runbook.md)

This guide provides comprehensive step-by-step development procedures, best practices, and workflow patterns for the Home Inventory System.

---

## 🔄 Development Overview

### Development Philosophy

The Home Inventory System follows a **small, modular, iterative approach**:

1. **Micro-Steps**: Each task broken into 30-60 minute chunks
2. **Independent Testing**: Each component testable in isolation
3. **Incremental Complexity**: Add one feature at a time
4. **Validation Gates**: All tests and quality checks must pass before proceeding

### Current Development Phase

**Phase**: Week 1 - Project Bootstrap & Database Setup  
**Active Sprint**: Step 1.2 - Database Models Foundation  
**Completed Steps**: 1.1, 1.2a, 1.2b, 1.2c  
**Next Step**: Step 1.2d - Self-Referential Relationship enhancements

---

## 🚀 Standard Development Workflow

### Pre-Development Setup

#### 1. Environment Validation

```bash
cd backend
source venv/bin/activate
python scripts/diagnose_environment.py
```

**Expected Result**: 8/8 diagnostic checks pass ✅

**If checks fail:**
```bash
python scripts/setup_test_environment.py
```

#### 2. Current State Verification

```bash
# Run all tests to confirm stable starting point
python run_tests.py

# Run manual verification
python scripts/verify_step_1_2b.py  # Or latest verification script

# Check code quality
black --check . && flake8 && mypy app/
```

**Expected Results**: 
- 17/17 tests passing ✅
- 8/8 manual verification checks passing ✅
- All code quality checks passing ✅

### Development Iteration Cycle

#### Step 1: Plan and Prepare

**Update Development Log:**
```bash
# Review current status in DEVELOPMENT_LOG.md
# Plan next micro-step (30-60 minutes)
# Update todo list if using task management
```

**Create Feature Branch (if using Git):**
```bash
git checkout -b feature/step-1-2d-enhancements
```

#### Step 2: Implement Changes

**Follow Established Patterns:**
- Use existing code structures as templates
- Follow SQLAlchemy 2.0 patterns from Location model
- Maintain async/await consistency
- Use proper type annotations

**Code Organization:**
```
app/
├── models/           # SQLAlchemy models
│   └── location.py   # Follow this pattern
├── database/         # Database configuration
├── schemas/          # Pydantic schemas (future)
├── services/         # Business logic (future)
└── api/             # FastAPI routes (future)
```

#### Step 3: Write Tests First (TDD Approach)

**Test File Naming:**
- `tests/test_{model_name}.py` for models
- `tests/test_{feature_name}.py` for features

**Test Structure Pattern:**
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

#### Step 4: Run Tests Continuously

```bash
# Run tests after each significant change
python run_tests.py

# Run specific test file during development
PYTHONPATH=. python -m pytest tests/test_new_feature.py -v

# Run single test function for debugging
PYTHONPATH=. python -m pytest tests/test_new_feature.py::test_specific_function -v
```

#### Step 5: Code Quality Checks

```bash
# Format code
black .

# Check linting
flake8

# Type checking
mypy app/

# All quality checks in sequence
black . && flake8 && mypy app/
```

#### Step 6: Manual Verification (if applicable)

**Create verification script if needed:**
```bash
# Copy existing verification script as template
cp scripts/verify_step_1_2b.py scripts/verify_step_1_2d.py
# Modify for new functionality
```

**Run verification:**
```bash
python scripts/verify_step_1_2d.py
```

#### Step 7: Integration Testing

```bash
# Run full test suite
python run_tests.py

# Run all verification scripts
python scripts/verify_step_1_2a.py
python scripts/verify_step_1_2b.py
python scripts/verify_step_1_2d.py  # If created

# Environment diagnostics
python scripts/diagnose_environment.py
```

#### Step 8: Documentation Updates

**Update Documentation:**
- Add new features to DEVELOPMENT_LOG.md
- Update runbooks if new procedures added
- Update Architecture.md if design changes
- Update this workflow if process changes

**Commit Changes (if using Git):**
```bash
git add .
git commit -m "Implement Step 1.2d: Self-referential relationship enhancements

- Add new functionality X
- Enhance existing feature Y  
- All tests passing (17/17)
- Manual verification complete

🤖 Generated with Claude Code"
```

---

## 🏗️ Feature Development Patterns

### Adding New Models

#### 1. Model Creation

**Location**: `app/models/{model_name}.py`

**Template Pattern:**
```python
from typing import List, Optional
from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from app.database.base import Base

class NewModel(Base):
    """Model description."""
    
    __tablename__ = "table_name"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Core fields
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id}, name='{self.name}')>"
```

#### 2. Database Integration

**Update `app/database/base.py`:**
```python
# Import models to ensure they are registered with the Base
from app.models import location  # existing
from app.models import new_model  # add new import
```

#### 3. Test Creation

**Location**: `tests/test_{model_name}.py`

**Follow Location model test patterns:**
- Model creation and validation
- Relationship testing (if applicable)
- String representation testing
- Business logic testing

#### 4. Manual Verification

**Create verification script:**
```bash
cp scripts/verify_step_1_2b.py scripts/verify_{model_name}.py
# Modify for new model functionality
```

### Adding API Endpoints

#### 1. Schema Definition (Future)

**Location**: `app/schemas/{model_name}.py`

**Pydantic schema pattern:**
```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ModelBase(BaseModel):
    name: str
    description: Optional[str] = None

class ModelCreate(ModelBase):
    pass

class ModelUpdate(ModelBase):
    name: Optional[str] = None

class ModelResponse(ModelBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

#### 2. Service Layer (Future)

**Location**: `app/services/{model_name}_service.py`

**Service pattern:**
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.new_model import NewModel
from app.schemas.new_model import ModelCreate, ModelUpdate

class NewModelService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, model_data: ModelCreate) -> NewModel:
        model = NewModel(**model_data.dict())
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return model
    
    async def get_by_id(self, model_id: int) -> Optional[NewModel]:
        result = await self.session.execute(
            select(NewModel).where(NewModel.id == model_id)
        )
        return result.scalar_one_or_none()
```

#### 3. API Routes (Future)

**Location**: `app/api/v1/{model_name}.py`

**FastAPI route pattern:**
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.base import get_session
from app.services.new_model_service import NewModelService
from app.schemas.new_model import ModelCreate, ModelResponse

router = APIRouter()

@router.post("/", response_model=ModelResponse)
async def create_model(
    model_data: ModelCreate,
    session: AsyncSession = Depends(get_session)
):
    service = NewModelService(session)
    return await service.create(model_data)
```

---

## 🧪 Testing Workflow

### Test-Driven Development (TDD)

#### 1. Write Failing Tests

```bash
# Create test file
touch tests/test_new_feature.py

# Write minimal failing test
# Run test to confirm it fails
PYTHONPATH=. python -m pytest tests/test_new_feature.py -v
```

#### 2. Implement Minimum Code

- Write minimal code to make test pass
- Focus on functionality, not optimization

#### 3. Refactor and Improve

- Clean up code while keeping tests passing
- Add error handling and edge cases
- Optimize if necessary

#### 4. Repeat Cycle

- Add new test for next piece of functionality
- Implement code to make it pass
- Continue iterating

### Test Categories

#### Unit Tests

**Purpose**: Test individual components in isolation

**Examples**:
- Model field validation
- Method functionality
- Property calculations

#### Integration Tests

**Purpose**: Test component interactions

**Examples**:
- Database operations
- Model relationships
- Service layer operations

#### Manual Verification

**Purpose**: End-to-end validation

**Examples**:
- Complete workflow testing
- Cross-component validation
- Human-readable output

---

## 🔧 Code Quality Workflow

### Automated Quality Checks

#### Pre-Commit Workflow

```bash
# Before committing any changes
black .              # Format code
flake8              # Check linting
mypy app/           # Type checking
python run_tests.py # Run all tests
```

#### Quality Check Automation

**Create quality check script:**
```bash
#!/bin/bash
# scripts/quality_check.sh

echo "Running code quality checks..."

echo "1. Code formatting..."
black .
if [ $? -ne 0 ]; then
    echo "❌ Code formatting failed"
    exit 1
fi

echo "2. Linting..."
flake8
if [ $? -ne 0 ]; then
    echo "❌ Linting failed"
    exit 1
fi

echo "3. Type checking..."
mypy app/
if [ $? -ne 0 ]; then
    echo "❌ Type checking failed"
    exit 1
fi

echo "4. Running tests..."
python run_tests.py
if [ $? -ne 0 ]; then
    echo "❌ Tests failed"
    exit 1
fi

echo "✅ All quality checks passed!"
```

### Code Review Checklist

#### Before Submitting Changes

- [ ] All tests pass (17/17 or updated count)
- [ ] Manual verification passes (if applicable)
- [ ] Code formatted with black
- [ ] No flake8 linting errors
- [ ] MyPy type checking passes (no critical errors)
- [ ] Documentation updated (if needed)
- [ ] DEVELOPMENT_LOG.md updated

#### Code Quality Standards

**Type Annotations:**
- All functions have return type annotations
- All parameters have type annotations
- Use `Optional[Type]` for nullable fields
- Use `List[Type]` for collections

**Error Handling:**
- Handle expected exceptions gracefully
- Provide meaningful error messages
- Log errors appropriately

**Documentation:**
- Docstrings for all classes and public methods
- Complex logic has inline comments
- README and runbooks updated for new features

---

## 📋 Step Completion Criteria

### Definition of Done

For each development step to be considered complete:

#### Technical Requirements

1. **All Tests Pass**: Current test suite passes completely
2. **Manual Verification**: Manual verification scripts pass (if applicable)
3. **Code Quality**: All quality checks pass (black, flake8, mypy)
4. **Integration**: New functionality integrates with existing system

#### Documentation Requirements

1. **Code Documentation**: Proper docstrings and comments
2. **Runbook Updates**: Relevant runbooks updated
3. **Development Log**: DEVELOPMENT_LOG.md updated with step completion
4. **Architecture Updates**: Architecture.md updated if design changes

#### Validation Requirements

1. **Environment Stability**: Environment diagnostics pass
2. **Performance**: No significant performance degradation
3. **Backward Compatibility**: Existing functionality unaffected
4. **Error Handling**: Appropriate error handling implemented

### Step Completion Checklist

```bash
# Technical validation
python run_tests.py                    # Should pass 100%
python scripts/diagnose_environment.py # Should pass 8/8
python scripts/verify_step_X.py        # Should pass all checks
black . && flake8 && mypy app/         # Should pass all checks

# Documentation validation
# ✓ DEVELOPMENT_LOG.md updated
# ✓ Relevant runbooks updated
# ✓ Code properly documented
# ✓ Architecture.md updated (if needed)

# Integration validation
# ✓ All existing functionality works
# ✓ New functionality integrates properly
# ✓ No breaking changes introduced
# ✓ Performance acceptable
```

---

## 🚨 Common Development Issues

### Environment Problems

#### Virtual Environment Not Active

**Symptom**: Import errors, wrong Python version

**Solution**:
```bash
cd backend
source venv/bin/activate
which python  # Should point to venv/bin/python
```

#### Dependency Issues

**Symptom**: Module not found errors

**Solution**:
```bash
pip install -r requirements-dev.txt
python scripts/diagnose_environment.py
```

### Testing Problems

#### Import Errors in Tests

**Symptom**: `ModuleNotFoundError: No module named 'app'`

**Solution**:
```bash
# Use primary test runner
python run_tests.py

# Or set Python path explicitly
PYTHONPATH=. python -m pytest tests/ -v
```

#### Database Issues in Tests

**Symptom**: SQLAlchemy or session errors

**Solution**:
```bash
# Remove database file
rm inventory.db

# Run database verification
python scripts/verify_step_1_2a.py

# Re-run tests
python run_tests.py
```

### Code Quality Issues

#### Formatting Conflicts

**Symptom**: Black and flake8 disagree

**Solution**:
```bash
# Black takes precedence, run first
black .
flake8

# Check .flake8 configuration for compatibility
```

#### Type Checking Errors

**Symptom**: MyPy errors on SQLAlchemy code

**Solution**:
```bash
# Minor SQLAlchemy warnings are acceptable
# Focus on fixing critical errors
mypy app/ --show-error-codes

# Check if error is in known acceptable list
```

---

## 📈 Development Process Evolution

### Process Improvement

#### Metrics to Track

- **Development Velocity**: Time per micro-step
- **Quality Metrics**: Test pass rate, code coverage
- **Error Rate**: Failed builds, debugging time
- **Documentation Currency**: How up-to-date documentation is

#### Regular Process Review

**Weekly Review Questions:**
- Are micro-steps appropriately sized (30-60 minutes)?
- Are quality gates effective at catching issues?
- Is documentation keeping pace with development?
- Are there recurring issues that need process fixes?

### Scaling the Process

#### Team Development (Future)

**When multiple developers join:**
- Implement branch protection rules
- Add code review requirements
- Implement CI/CD pipeline
- Add automated quality gates

**CI/CD Pipeline (Future):**
```yaml
# .github/workflows/ci.yml (example)
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.12
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements-dev.txt
      - name: Run quality checks
        run: |
          cd backend
          black --check .
          flake8
          mypy app/
      - name: Run tests
        run: |
          cd backend
          python run_tests.py
```

---

## 📞 Support and References

### Related Documentation

- **[Main Runbook](../RUNBOOK.md)** - Complete operational guide
- **[Testing Runbook](./testing-runbook.md)** - Comprehensive testing procedures
- **[Database Operations](./database-operations.md)** - Database management
- **[Scripts Reference](./scripts-reference.md)** - Available scripts and tools

### Development Resources

- **Architecture Reference**: `../Architecture.md`
- **Development Log**: `../DEVELOPMENT_LOG.md`
- **Code Examples**: Existing models in `app/models/`
- **Test Examples**: Existing tests in `tests/`

### External References

- **FastAPI Best Practices**: https://fastapi.tiangolo.com/tutorial/
- **SQLAlchemy 2.0 Guide**: https://docs.sqlalchemy.org/en/20/
- **Pytest Best Practices**: https://docs.pytest.org/en/stable/goodpractices.html
- **Python Type Checking**: https://mypy.readthedocs.io/en/stable/

---

**Last Updated**: 2025-01-26  
**Next Review**: When development process changes  
**Maintainer**: Development team