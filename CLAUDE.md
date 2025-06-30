# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Home Inventory Management System** currently in the planning/architecture phase. The project is designed as a simple, reliable solution for tracking personal belongings in a homelab environment.

**Current Status**: Architecture documentation complete, implementation not yet started.

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
1. **Phase 1 (Weeks 1-4)**: Core CRUD with PostgreSQL and authentication
2. **Phase 2 (Weeks 5-8)**: Weaviate integration and semantic search
3. **Phase 3 (Weeks 9-12)**: Production hardening and UX polish

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

Since implementation hasn't started, these are the expected commands based on the planned stack:

```bash
# Backend development
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend development  
cd frontend
pip install -r requirements.txt
streamlit run app.py --server.port 8501

# Testing
pytest backend/tests/
pytest frontend/tests/

# Docker deployment
docker-compose up -d
```

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

### Development Process Requirements

**After Each Step Completion:**
1. **Update DEVELOPMENT_LOG.md** with step completion details including:
   - What was built and implemented
   - Challenges faced and solutions applied
   - Architecture decisions made
   - Current state and verification results
   - Technical debt and next steps
2. Run all relevant tests and document results
3. Create/update manual verification scripts if needed
4. Update current status and next steps in the log
5. Document any deviations from the original plan

**Testing Requirements:**
- All tests must pass before marking a step complete
- Use `python run_tests.py` for reliable test execution
- Include both automated tests (pytest) and manual verification scripts
- Document test results in DEVELOPMENT_LOG.md

## Architecture Reference

Refer to `Architecture.md` for comprehensive technical details including:
- Database schemas and relationships
- API endpoint specifications
- Deployment architecture diagrams
- Security considerations and threat model
- Future enhancement roadmap

## Current Development Priority

The project is ready to begin Phase 1 implementation:
1. Set up FastAPI backend with PostgreSQL integration
2. Implement core Item and Location models
3. Create basic CRUD operations
4. Add Streamlit frontend with authentication
5. Establish testing framework and CI/CD pipeline