# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Home Inventory Management System** in active development. The project is designed as a simple, reliable solution for tracking personal belongings in a homelab environment.

**Current Status**: ✅ Phase 2.2 Complete - Full semantic search integration with Weaviate, AI-powered natural language search, and comprehensive API implementation (40+ endpoints)

## Technology Stack

- **Frontend**: Streamlit with Streamlit-Authenticator
- **Backend**: FastAPI with service layer pattern
- **Primary Database**: PostgreSQL 
- **Search Database**: Weaviate (vector database for semantic search)
- **Language**: Python
- **Deployment**: Docker Compose containers
- **Infrastructure**: Proxmox LXC containers for databases

## Architecture Patterns

### Service Layer Pattern
- Clean separation between API endpoints, business logic, and data access
- Dependency injection for database connections and external services
- Repository pattern for data access abstraction

### Dual Database Strategy
- PostgreSQL as source of truth for all data
- Weaviate for semantic search capabilities with embeddings
- Dual-write pattern with PostgreSQL write confirmation before Weaviate update

### Development Phases
1. **Phase 1 (Weeks 1-4)**: ✅ Core CRUD with PostgreSQL - COMPLETE
2. **Phase 2 (Weeks 5-8)**: ✅ Weaviate integration and semantic search - COMPLETE
3. **Phase 3 (Weeks 9-12)**: Production hardening, authentication, and UX polish - READY TO BEGIN

## Expected Project Structure

```
/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI route handlers
│   │   ├── services/      # Business logic layer
│   │   ├── models/        # Database models
│   │   ├── schemas/       # Pydantic schemas
│   │   └── database/      # Database configuration
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── pages/             # Streamlit pages
│   ├── components/        # Reusable UI components
│   ├── utils/             # Frontend utilities
│   └── requirements.txt
├── docker-compose.yml
└── Architecture.md        # Detailed architecture documentation
```

## Development Commands

**Prerequisites**: Python 3.12+, Poetry installed

```bash
# Backend development
cd backend
poetry install                           # Install dependencies
poetry run alembic upgrade head         # Apply database migrations
poetry run uvicorn app.main:app --reload --port 8000

# Frontend development  
cd frontend
poetry install                          # Install dependencies
poetry run streamlit run app.py --server.port 8501

# Testing
cd backend
poetry run pytest tests/               # Run all backend tests
python run_tests.py                    # Run tests with Python path fix
python run_tests.py tests/test_api_items_comprehensive.py -v  # Run specific API tests

# API Testing (comprehensive coverage)
python run_tests.py tests/test_api_items_comprehensive.py      # Items API (25+ endpoints)
python run_tests.py tests/test_api_inventory_operations.py     # Inventory API (30+ endpoints) 
python run_tests.py tests/test_api_performance_monitoring.py   # Performance API (8+ endpoints)
python run_tests.py tests/test_api_integration_workflows.py    # Integration workflows
python run_tests.py tests/test_api_error_scenarios.py          # Error handling
python run_tests.py tests/test_api_validation_business_rules.py # Business rules

cd frontend  
poetry run pytest tests/               # Run frontend tests
python run_frontend_tests.py           # Run frontend tests with path fix

# Frontend Error Boundary Testing (comprehensive error handling)
python run_frontend_tests.py --error-boundaries-only          # Run error boundary tests only
python run_frontend_tests.py --category error_boundaries      # Error boundary components
python run_frontend_tests.py --category error_handling        # Error handling infrastructure
python run_frontend_tests.py --category page_boundaries       # Page-level error recovery
python -m pytest tests/test_error_boundary_concepts.py -v     # Error handling concepts

# Database operations
cd backend
poetry run alembic current             # Check migration status
poetry run alembic upgrade head        # Apply migrations
poetry run alembic revision --autogenerate -m "description"  # Create migration

# Docker deployment
docker-compose up -d
```

**Development URLs**:
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs  
- Frontend: http://localhost:8501
- Health Check: http://localhost:8000/health

## Core Data Models

### Item
- Basic inventory item with name, description, location, tags
- Support for multiple photos and flexible metadata
- Categories: Electronics, Documents, Household, Tools, etc.

### Location  
- Hierarchical location structure (Room > Container > Shelf)
- Support for nested locations and flexible organization

### User
- Simple authentication with Streamlit-Authenticator
- Multi-user support for household members

## Key Features

### Semantic Search
- Natural language queries using Weaviate vector embeddings
- Search by description, use case, or visual similarity
- Fallback to traditional PostgreSQL text search

### Mobile-First Design
- Responsive Streamlit interface optimized for smartphones
- Quick item lookup and addition workflows
- Photo capture integration

### Data Export
- Export capabilities for backup and migration
- Support for standard formats (CSV, JSON)

## Environment Configuration

### Database Connections
- PostgreSQL: External LXC container in Proxmox
- Weaviate: External LXC container with vector capabilities
- Connection pooling and health checks required

### Authentication
- Streamlit-Authenticator with hashed password storage
- Session management and secure cookie handling

## Development Guidelines

### Code Organization
- Follow service layer pattern with clear separation of concerns
- Use dependency injection for all external dependencies
- Repository pattern for database operations
- Comprehensive error handling and logging

### Database Strategy
- PostgreSQL as single source of truth
- Weaviate updates only after successful PostgreSQL writes
- Graceful handling of Weaviate unavailability
- Regular consistency checks between databases

### Testing Strategy
- Unit tests for service layer business logic
- Integration tests for database operations
- API endpoint testing with test database
- Frontend component testing where feasible
- **Run tests with**: `python run_tests.py` (handles Python path issues automatically)

### Security Practices
- Input validation and sanitization
- SQL injection prevention through parameterized queries
- Secure session management
- Environment-based configuration for secrets

### 🚨 MANDATORY Development Process Requirements

> **CRITICAL**: Documentation AND Git commits are NOT optional. Failure to follow these requirements will result in incomplete work that cannot be considered "done".

#### **📝 IMMEDIATE Documentation & Git Requirements**

**BEFORE marking any task as complete, you MUST:**

1. **📊 Update DEVELOPMENT_LOG.md** - This is MANDATORY, not optional
   - **What was built**: Detailed description of all functionality implemented
   - **Challenges faced**: Problems encountered and specific solutions applied
   - **Architecture decisions**: Technical choices made and reasoning
   - **Current state**: What's working, what's not, verification results
   - **Technical debt**: Issues created or resolved
   - **Duration & complexity**: Time spent and difficulty level
   - **Next steps**: Clear pipeline for future work

2. **🧪 Document Testing Results**
   - Run ALL relevant tests before claiming completion
   - Document test results, pass/fail counts, and any issues
   - Include both automated (pytest) and manual verification
   - If tests fail, task is NOT complete

3. **📝 Create Git Commit with Descriptive Message** - This is MANDATORY
   - Commit ALL relevant changes with comprehensive commit message
   - Use conventional commit format: `feat:`, `fix:`, `docs:`, `refactor:`, etc.
   - Include detailed description of what was changed and why
   - Add co-authorship: `Co-Authored-By: Claude <noreply@anthropic.com>`
   - Must include emojis and structured sections for readability

4. **📋 Update TODO Tracking**
   - Use TodoWrite tool to track ALL significant work
   - Mark tasks in_progress when starting, completed when done
   - Break complex work into trackable subtasks
   - Never batch multiple completions

#### **⚠️ Process Enforcement Rules**

**UNACCEPTABLE**: Completing significant work without documentation AND git commits
- ❌ Making multiple fixes without logging each one
- ❌ "Batching" documentation at the end of a session
- ❌ Skipping DEVELOPMENT_LOG.md updates
- ❌ Claiming work is "complete" without proper verification
- ❌ Working without committing changes to git
- ❌ Making commits without descriptive messages

**REQUIRED**: Real-time documentation and git discipline
- ✅ Document each significant change as it's made
- ✅ Update DEVELOPMENT_LOG.md after every major task
- ✅ Create descriptive git commits for every significant change
- ✅ Use TodoWrite tool to track ALL work in progress
- ✅ Include timestamp, duration, and complexity assessment
- ✅ Maintain clean git history with meaningful commit messages

#### **📚 Documentation Quality Standards**

Each DEVELOPMENT_LOG.md entry MUST include:
- **Clear section header** with completion date and status
- **Comprehensive "What Was Built" section** (not just bullet points)
- **Detailed challenges and solutions** (for future reference)
- **Technical implementation details** (versions, commands, configurations)
- **Architecture decisions with reasoning** (why, not just what)
- **Current state verification** (how you know it works)
- **Technical debt assessment** (what issues remain)

#### **🔄 Git Commit Standards**

Every commit message MUST follow this format:
```
<type>: <concise description>

🚀 <emoji> Brief summary of changes

## <Section headers as needed>
- Bullet point details
- Specific changes made
- Impact and reasoning

## Current Status
✅ What's working
⏳ What's pending
❌ What's broken (if any)

## Testing Verified
- Manual testing performed
- Automated tests run
- Verification steps taken

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Commit Types:**
- `feat:` New features or functionality
- `fix:` Bug fixes and issue resolution  
- `docs:` Documentation updates
- `refactor:` Code reorganization without behavior change
- `test:` Test additions or modifications
- `chore:` Maintenance tasks, dependency updates

#### **🔄 Real-Time Process Flow**

1. **Start Task**: Use TodoWrite to mark task as in_progress
2. **Work in Small Chunks**: Max 30-60 minutes before documentation
3. **Document Progress**: Update DEVELOPMENT_LOG.md after each chunk
4. **Test & Verify**: Run tests and document results
5. **Mark Complete**: Only after full documentation and verification
6. **Update Status**: Reflect current state accurately in all files

#### **📖 Additional Documentation Requirements**

- **README.md**: Keep current with any new setup requirements
- **Architecture.md**: Update for any architectural changes
- **CLAUDE.md**: Update development status and priorities
- **Code Comments**: Document complex logic inline
- **Git Commits**: Meaningful commit messages with context

#### **🚫 Consequences of Poor Documentation**

Work that lacks proper documentation will be considered:
- **Incomplete**: Not ready for production or handoff
- **Technical Debt**: Creating maintenance burden
- **Process Failure**: Violating development standards
- **Non-Professional**: Below acceptable quality standards

**Remember**: Good documentation is not overhead - it's an essential part of professional software development.

## Architecture Reference

Refer to `Architecture.md` for comprehensive technical details including:
- Database schemas and relationships
- API endpoint specifications
- Deployment architecture diagrams
- Security considerations and threat model
- Future enhancement roadmap

## Current Development Priority

**✅ Phase 1 COMPLETE** - Core CRUD functionality implemented:
1. ✅ FastAPI backend with PostgreSQL integration (Proxmox LXC)
2. ✅ Core Location, Category, and Item models with relationships
3. ✅ Complete REST API with 25+ endpoints 
4. ✅ Streamlit frontend with multi-page navigation
5. ✅ Comprehensive testing framework (65+ tests)
6. ✅ Poetry package management and Docker configuration
7. ✅ Database migrations with Alembic

**✅ Phase 2 COMPLETE** - Semantic Search Integration:
1. ✅ Weaviate vector database integration with v4 client
2. ✅ Item embedding generation using sentence-transformers (all-MiniLM-L6-v2)
3. ✅ Semantic search endpoints added to API (/api/v1/search/*)
4. ✅ Advanced search UI with AI-powered toggle in frontend
5. ✅ Dual-write pattern implemented with graceful fallback

**✅ Phase 1.5 COMPLETE** - Frontend Issue Resolution & Enhancement:
1. ✅ Dashboard ValueError fixes with safe numeric conversion helpers
2. ✅ Backend API numeric type corrections (Decimal to float serialization) 
3. ✅ Items page critical bug fixes (undefined variables, incorrect API calls)
4. ✅ Complete item creation functionality directly in items page
5. ✅ Comprehensive error handling and user feedback improvements
6. ✅ Frontend robustness enhancements with fallback strategies
7. ✅ Schema-model architecture fixes (location_id mismatch resolution)
8. ✅ Currency formatting safety throughout frontend

**✅ Phase 2.2 COMPLETE** - Semantic Search Full Implementation:
1. ✅ Backend API Integration with ItemService dual-write pattern
2. ✅ Data Migration infrastructure with batch embedding creation
3. ✅ Frontend API Client Extensions with 6 new search methods
4. ✅ Enhanced Items Page UI with natural language search
5. ✅ Similar items discovery and AI-powered search sensitivity controls
6. ✅ Comprehensive null-safety fixes for search result processing

**Current System Status**: Fully functional inventory management system with:
- Robust PostgreSQL backend (40+ API endpoints)
- AI-powered semantic search with Weaviate integration
- Natural language queries ("blue electronics in garage", "kitchen tools under $50")
- Complete CRUD operations for all entities
- Comprehensive error handling and graceful degradation
- Production-ready architecture with clean separation of concerns

**🎯 Phase 3 READY** - Production Deployment & Advanced Features:
1. **Authentication & Security**: Streamlit-Authenticator integration, JWT tokens, role-based access
2. **Image Support**: Photo upload, thumbnail generation, image-based search
3. **Production Hardening**: Environment configuration, secrets management, monitoring
4. **Advanced UI Features**: Dashboard customization, data visualization, reporting
5. **Mobile Enhancements**: Camera integration, barcode scanning, offline support
6. **Documentation**: Complete API reference, deployment guides, user manuals