# Home Inventory System Architecture Guide

## Executive Summary

This comprehensive architecture guide provides **practical, implementable solutions** for building a simple home inventory system using Streamlit, FastAPI, PostgreSQL, and Weaviate. The research reveals that **starting simple with proven patterns** is the most effective approach, focusing on a narrow vertical slice that works reliably before adding complexity.

**Key architectural decisions favor simplicity**: use Streamlit-Authenticator for robust authentication, implement a service layer pattern in FastAPI for clean database integration, leverage Docker Compose for deployment simplicity, and design data models that support both structured queries and semantic search without over-engineering.

The recommended approach emphasizes **incremental development** through three phases: basic CRUD functionality first, then enhanced features, and finally production-ready capabilities. This strategy minimizes technical debt while ensuring each phase delivers working software that can be deployed and used immediately.

## Architecture Decision Records

### ADR-001: Authentication Strategy for Streamlit Frontend

**Status**: Accepted  
**Date**: 2025-01-XX  
**Context**: Home inventory system needs simple but secure authentication with session management for CRUD operations.

**Decision Drivers**:
- Single-user or small family use case
- Minimal complexity preference
- Session persistence across browser tabs
- Integration with FastAPI backend

**Considered Options**:
- Built-in Streamlit OIDC authentication
- Streamlit-Authenticator library
- Simple environment variable password protection

**Decision**: **Streamlit-Authenticator library**

**Justification**: Provides comprehensive authentication features without external dependencies, includes password hashing with bcrypt, session management with cookies, and password reset functionality. Offers the best balance of security and simplicity for small-scale deployment.

**Implementation**:
```python
# config.yaml approach with YAML-based user management
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'], 
    config['cookie']['key'],
    config['cookie']['expiry_days']
)
```

**Positive Consequences**: Complete authentication solution, secure password handling, persistent sessions, minimal external dependencies.

**Negative Consequences**: Requires YAML configuration management, user registration handled manually rather than self-service.

### ADR-002: Database Architecture for Dual PostgreSQL-Weaviate Integration

**Status**: Accepted  
**Date**: 2025-01-XX  
**Context**: System requires both structured inventory data management and semantic search capabilities.

**Decision Drivers**:
- Structured data for inventory tracking (quantities, locations, prices)
- Semantic search for item descriptions and categories
- External LXC database containers in Proxmox environment
- Data consistency requirements

**Considered Options**:
- PostgreSQL with pgvector extension only
- PostgreSQL + Weaviate with dual-write pattern
- PostgreSQL + Weaviate with event-driven synchronization

**Decision**: **PostgreSQL + Weaviate with simplified dual-write pattern**

**Justification**: PostgreSQL serves as the authoritative source for structured inventory data, while Weaviate handles semantic search. **Dual-write approach provides immediate consistency** for small-scale systems without complex event streaming infrastructure.

**Implementation**:
```python
class InventoryService:
    async def create_item(self, item_data):
        # Write to PostgreSQL first (source of truth)
        db_item = await self.create_postgres_item(item_data)
        # Sync to Weaviate for search
        await self.create_weaviate_embedding(db_item)
        return db_item
```

**Positive Consequences**: Clear data ownership, reliable structured queries, powerful semantic search, simple consistency model.

**Negative Consequences**: Potential inconsistency if Weaviate write fails, slightly increased complexity compared to single database.

### ADR-003: API Design Pattern for FastAPI Backend

**Status**: Accepted  
**Date**: 2025-01-XX  
**Context**: FastAPI backend needs clean architecture for CRUD operations with dual database integration.

**Decision Drivers**:
- Clean separation of concerns
- Testability and maintainability
- Database connection management
- Error handling for external databases

**Considered Options**:
- Direct database access in route handlers
- Repository pattern with dependency injection
- Service layer with dual database managers

**Decision**: **Service layer pattern with dependency injection**

**Justification**: **Service layer encapsulates business logic** while dependency injection enables clean testing and connection management. Pattern scales well and maintains clear boundaries between data access and business rules.

**Implementation**:
```python
# Dependency injection for dual databases
async def get_inventory_service(
    db: AsyncSession = Depends(get_postgres_session),
    weaviate_client = Depends(get_weaviate_client)
) -> InventoryService:
    return InventoryService(db, weaviate_client)

@router.post("/items/")
async def create_item(
    item: InventoryItemCreate,
    service: InventoryService = Depends(get_inventory_service)
):
    return await service.create_item(item)
```

**Positive Consequences**: Clean architecture, testable code, proper connection management, clear error boundaries.

**Negative Consequences**: Additional abstraction layers, more boilerplate code than direct database access.

### ADR-004: Containerization Strategy for Proxmox Deployment

**Status**: Accepted  
**Date**: 2025-01-XX  
**Context**: Deploy applications in Docker containers while databases run in separate LXC containers on Proxmox.

**Decision Drivers**:
- External PostgreSQL and Weaviate in LXC containers
- Proxmox homelab environment
- Simple deployment and updates
- Resource isolation

**Considered Options**:
- Single container with embedded databases
- Docker Compose with external database connections
- Kubernetes deployment

**Decision**: **Docker Compose with external database connections**

**Justification**: **Docker Compose provides simplicity** while maintaining separation of concerns. Applications in containers for easy updates, databases in LXCs for better resource management and backup strategies.

**Implementation**:
```yaml
services:
  fastapi:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://user:pass@192.168.1.100:5432/inventory
      - WEAVIATE_URL=http://192.168.1.101:8080
  
  streamlit:
    build: ./frontend
    environment:
      - BACKEND_URL=http://fastapi:8000
    depends_on:
      - fastapi
```

**Positive Consequences**: Easy deployment, simple updates, resource isolation, database independence.

**Negative Consequences**: Network configuration complexity, external dependency management.

### ADR-005: Data Model Design for Inventory Management

**Status**: Accepted  
**Date**: 2025-01-XX  
**Context**: Design data model supporting both structured inventory management and semantic search capabilities.

**Decision Drivers**:
- Home inventory use case with items, locations, categories
- Support for semantic search on descriptions
- Insurance and warranty tracking
- Simple but extensible design

**Considered Options**:
- Flat table structure with JSON metadata
- Normalized relational model with separate tables
- Document-based model with embedded relationships

**Decision**: **Normalized relational model with hierarchical support**

**Implementation**:
```sql
-- Core entities with hierarchical support
CREATE TABLE locations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    parent_location_id INTEGER REFERENCES locations(id)
);

CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    parent_category_id INTEGER REFERENCES categories(id)
);

CREATE TABLE items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    sku VARCHAR(100) UNIQUE,
    category_id INTEGER REFERENCES categories(id),
    purchase_date DATE,
    purchase_price DECIMAL(10,2),
    estimated_value DECIMAL(10,2),
    warranty_expiration DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE inventory (
    id SERIAL PRIMARY KEY,
    item_id INTEGER REFERENCES items(id),
    location_id INTEGER REFERENCES locations(id),
    quantity INTEGER DEFAULT 1,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Positive Consequences**: Clear relationships, hierarchical organization, extensible design, insurance-ready tracking.

**Negative Consequences**: More complex than flat structure, requires careful foreign key management.

## Product Specification

### System Overview
**Home Inventory Management System** designed for small households to track personal belongings with natural language search capabilities. System prioritizes simplicity and reliability over advanced features.

### Core Functional Requirements

**Essential CRUD Operations**:
- **Create Items**: Add inventory items with name, description, category, location, and metadata
- **View Items**: Display items with filtering by category, location, and search terms
- **Update Items**: Modify item details, quantities, and locations
- **Delete Items**: Remove items with confirmation prompts
- **Search Items**: Natural language search using semantic similarity

**Location Management**:
- Hierarchical location structure (House → Room → Container → Shelf)
- Location-based filtering and reporting
- Support for moving items between locations

**Category Management**:
- Flexible categorization with tag-like system
- Category-based filtering and organization
- Support for multiple categories per item

### Non-Functional Requirements

**Performance**:
- Response time under 2 seconds for typical operations
- Support for 1,000+ inventory items
- Concurrent access for up to 5 users

**Security**:
- Username/password authentication with secure session management
- Data encryption in transit and at rest
- Regular security updates for dependencies

**Usability**:
- Mobile-responsive interface for smartphone access
- Intuitive filtering and search interface
- Bulk operations for efficiency

**Reliability**:
- 99.5% uptime target for homelab environment
- Automated backups with restoration procedures
- Graceful degradation if semantic search unavailable

### Technical Architecture

**Frontend**: Streamlit with session state management and responsive design
**Backend**: FastAPI with async operations and proper error handling  
**Databases**: PostgreSQL (structured data) + Weaviate (semantic search)
**Deployment**: Docker containers on Proxmox with external database LXCs
**Monitoring**: Health checks and basic metrics collection

### Deployment Requirements

**Infrastructure**:
- Proxmox host with 4GB RAM minimum for application containers
- PostgreSQL LXC container with 2GB RAM
- Weaviate LXC container with 4GB RAM  
- Network connectivity between containers on bridge network

**Configuration Management**:
- Environment variables for database connections
- Docker secrets for sensitive information
- YAML configuration for authentication settings

## Development Plan

### Phase 1: Core Foundation (Weeks 1-4)

**Objectives**: Establish basic CRUD functionality with secure authentication

**Week 1-2: Backend Development**
- Set up FastAPI project structure with service layer pattern
- Implement PostgreSQL models and basic CRUD operations
- Create API endpoints for items, categories, and locations
- Add input validation and error handling
- Implement health check endpoints

**Week 3-4: Frontend Development**  
- Set up Streamlit application with authentication
- Create item management interfaces using st.data_editor
- Implement filtering and search functionality
- Add category and location management pages
- Design responsive mobile-friendly layouts

**Deliverables**: Working CRUD application with authentication, deployable via Docker Compose

### Phase 2: Enhanced Features (Weeks 5-8)

**Objectives**: Add semantic search and production-ready features

**Week 5-6: Semantic Search Integration**
- Set up Weaviate schema for inventory items
- Implement dual-write synchronization pattern
- Create semantic search API endpoints
- Add natural language search interface to frontend
- Implement search result ranking and display

**Week 7-8: Production Features**
- Add comprehensive logging and monitoring
- Implement backup and restoration procedures
- Create Docker deployment documentation
- Add data import/export capabilities
- Optimize database queries and add connection pooling

**Deliverables**: Production-ready system with semantic search capabilities

### Phase 3: Polish and Enhancement (Weeks 9-12)

**Objectives**: Refine user experience and add convenience features

**Week 9-10: User Experience**
- Improve mobile interface responsiveness
- Add bulk operations for item management
- Implement advanced filtering combinations
- Create dashboard with inventory summaries
- Add photo upload capabilities for items

**Week 11-12: System Hardening**
- Comprehensive testing and bug fixes
- Performance optimization and caching
- Security audit and hardening
- Documentation completion
- Deployment automation scripts

**Deliverables**: Polished, well-documented system ready for long-term use

### Development Best Practices

**Code Organization**:
- Follow service layer pattern for clean architecture
- Use dependency injection for testability
- Implement proper error handling and logging
- Write unit tests for critical business logic

**Database Management**:
- Use database migrations for schema changes
- Implement proper indexing strategies
- Plan for data backup and recovery
- Monitor query performance

**Deployment Strategy**:
- Use Infrastructure as Code principles
- Implement health checks and monitoring
- Plan for zero-downtime updates
- Document deployment procedures

## Future Enhancement Ideas

### Short-term Enhancements (6 months)

**Mobile Application**:
- Native iOS/Android app using React Native
- Barcode scanning for quick item addition
- Photo capture with automatic metadata extraction
- Offline mode with synchronization

**Advanced Search Features**:
- Visual similarity search for images
- OCR for receipt processing and automatic item entry
- Integration with product databases for automatic metadata
- Smart categorization suggestions using machine learning

**Reporting and Analytics**:
- Inventory value tracking over time
- Purchase pattern analysis
- Warranty expiration notifications
- Insurance reporting exports

### Medium-term Enhancements (12 months)

**Multi-tenancy Support**:
- Support for multiple households/users
- Role-based access control
- Shared inventory management
- Privacy controls for sensitive items

**Integration Capabilities**:
- Home automation integration (IoT device tracking)
- Shopping list generation from low inventory
- Price tracking and alerts from online retailers
- Insurance company API integration

**Advanced Analytics**:
- Predictive analytics for replacement needs
- Usage pattern analysis
- Investment tracking for collectibles
- Environmental impact tracking

### Long-term Vision (18+ months)

**AI-Powered Features**:
- Computer vision for automatic item identification
- Natural language processing for voice-based inventory management
- Predictive maintenance reminders
- Smart organization suggestions

**Ecosystem Integration**:
- Smart home device integration
- E-commerce platform connections
- Financial software integration
- Social sharing capabilities for collections

**Enterprise Features**:
- Advanced backup and disaster recovery
- Audit logging and compliance features
- API for third-party integrations
- Advanced security and encryption options

## Implementation Guidelines

### Getting Started
1. **Set up development environment** with Docker and PostgreSQL/Weaviate LXCs
2. **Create project structure** following recommended patterns from research
3. **Implement authentication first** as the foundation for all other features
4. **Build incrementally** with working software at each phase
5. **Focus on core vertical slice** before adding advanced features

### Success Metrics
- **Functional**: All CRUD operations working reliably
- **Performance**: Sub-2-second response times for typical operations  
- **Usability**: Can add/find items efficiently on mobile devices
- **Reliability**: System runs without intervention for weeks
- **Maintainability**: New features can be added without major refactoring

This architecture guide provides a practical foundation for building a reliable, maintainable home inventory system that starts simple and evolves systematically. The emphasis on proven patterns, incremental development, and operational simplicity ensures success in a homelab environment while providing clear paths for future enhancement.