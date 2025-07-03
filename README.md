# Home Inventory Management System

A comprehensive, self-hosted inventory management solution designed for tracking personal belongings in a homelab environment. Built with modern Python technologies and a focus on semantic search capabilities.

## 🚀 Features

### Core Functionality
- **Hierarchical Location Management**: Organize items with flexible location structures (House → Room → Container → Shelf)
- **Rich Item Tracking**: Comprehensive metadata including value, condition, warranty, photos, and custom tags
- **Category System**: Flexible categorization with color coding and soft delete capabilities
- **AI-Powered Semantic Search**: Natural language queries like "blue electronics in garage" or "kitchen tools under $50"
- **REST API**: Complete FastAPI backend with automatic documentation
- **Web Interface**: Modern Streamlit frontend with responsive design

### Technical Features
- **Dual Database Strategy**: PostgreSQL for primary data, Weaviate for semantic search with vector embeddings
- **Async Architecture**: High-performance async/await throughout the stack
- **Type Safety**: Full type annotations with Pydantic validation
- **Database Migrations**: Alembic-powered schema versioning
- **Comprehensive Testing**: 65+ tests covering models, APIs, and integration
- **Container Ready**: Docker Compose for easy deployment

## 🛠 Technology Stack

### Backend
- **FastAPI** - Modern async web framework
- **SQLAlchemy** - Async ORM with full type support
- **PostgreSQL** - Primary database for all data
- **Weaviate** - Vector database for semantic search with sentence-transformers
- **Alembic** - Database migration management
- **Pydantic** - Data validation and serialization

### Frontend
- **Streamlit** - Rapid web application development
- **Plotly** - Interactive data visualizations
- **Pandas** - Data manipulation and display

### Development Tools
- **Poetry** - Dependency management and packaging
- **pytest** - Testing framework with async support
- **Black, Flake8, MyPy** - Code quality and type checking
- **Docker** - Containerization and deployment

## 📋 Prerequisites

- **Python 3.12+** (3.13 not supported due to AsyncPG compatibility)
- **PostgreSQL 12+** (local or remote instance)
- **Poetry** - For dependency management
- **Git** - For version control

### Optional
- **Docker & Docker Compose** - For containerized deployment
- **Weaviate** - For semantic search functionality (system works without it but falls back to basic search)

## 🚀 Quick Start

### 1. Clone Repository
```bash
git clone <repository-url>
cd InventorySystem
```

### 2. Backend Setup
```bash
cd backend

# Install dependencies
poetry install

# Configure database (see Database Setup section)
cp .env.example .env
# Edit .env with your PostgreSQL credentials

# Run migrations
poetry run alembic upgrade head

# Start backend server
poetry run uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
poetry install

# Start frontend
poetry run streamlit run app.py --server.port 8501
```

### 4. Access Applications
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Frontend**: http://localhost:8501
- **Health Check**: http://localhost:8000/health

## 🧠 Using AI-Powered Search

The system includes advanced semantic search capabilities using Weaviate:

### Natural Language Queries
- Search with everyday language: "old electronics in the basement"
- Find by characteristics: "blue items worth over 100 dollars"
- Discover related items: "things similar to my laptop"

### Using Search in the UI
1. Navigate to the **Items** page
2. Toggle **🧠 AI-Powered Search** to enable semantic search
3. Type natural language queries in the search box
4. Adjust search sensitivity (0-100%) for more or fewer results

### Search Fallback
If Weaviate is unavailable, the system automatically falls back to PostgreSQL text search, ensuring search functionality always works.

## 🔧 Development Setup

### Environment Management
This project uses **Poetry** for dependency management. Virtual environments are handled automatically.

```bash
# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
cd backend && poetry install
cd frontend && poetry install

# Activate virtual environment (optional, auto-activated by poetry run)
poetry shell
```

### Database Setup

#### Option 1: Local PostgreSQL
```bash
# Install PostgreSQL
brew install postgresql  # macOS
# or
sudo apt-get install postgresql  # Ubuntu

# Create database
createdb inventory_system

# Update .env file
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/inventory_system
```

#### Option 2: Docker PostgreSQL
```bash
# Run PostgreSQL in Docker
docker run --name inventory-postgres \
  -e POSTGRES_DB=inventory_system \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=your_password \
  -p 5432:5432 \
  -d postgres:15

# Update .env file
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/inventory_system
```

#### Option 3: Remote PostgreSQL
```bash
# Update .env file with remote credentials
DATABASE_URL=postgresql+asyncpg://username:password@your-host:5432/inventory_system
```

### Environment Variables
Create a `.env` file in the `backend/` directory:

```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://username:password@host:port/database
# or for Proxmox instance
POSTGRES_HOST=192.168.68.88
POSTGRES_PORT=5432
POSTGRES_DB=inventory_system
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

# Application Settings
ENVIRONMENT=development
LOG_LEVEL=INFO

# Security (for production)
SECRET_KEY=your-secret-key-here
```

## 🧪 Testing

### Backend Tests
```bash
cd backend

# Run all tests
poetry run pytest

# Run specific test categories
poetry run pytest tests/test_models/     # Model tests
poetry run pytest tests/test_api/        # API tests
poetry run pytest -v                     # Verbose output
poetry run pytest --cov                  # Coverage report
```

### Frontend Tests
```bash
cd frontend

# Run frontend tests
poetry run pytest
```

### Manual Testing
```bash
# Backend API health check
curl http://localhost:8000/health

# Test API endpoints
curl http://localhost:8000/api/v1/locations/
curl http://localhost:8000/api/v1/categories/
curl http://localhost:8000/api/v1/items/
```

## 📊 API Documentation

### Automatic Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Spec**: http://localhost:8000/openapi.json

### Core Endpoints

#### Locations
- `GET /api/v1/locations/` - List all locations
- `POST /api/v1/locations/` - Create new location
- `GET /api/v1/locations/{id}` - Get location details
- `PUT /api/v1/locations/{id}` - Update location
- `DELETE /api/v1/locations/{id}` - Delete location

#### Categories
- `GET /api/v1/categories/` - List all categories
- `POST /api/v1/categories/` - Create new category
- `GET /api/v1/categories/{id}` - Get category details
- `PUT /api/v1/categories/{id}` - Update category
- `DELETE /api/v1/categories/{id}` - Soft delete category

#### Items
- `GET /api/v1/items/` - List all items
- `POST /api/v1/items/` - Create new item
- `GET /api/v1/items/{id}` - Get item details
- `PUT /api/v1/items/{id}` - Update item
- `DELETE /api/v1/items/{id}` - Delete item

#### Semantic Search (NEW)
- `POST /api/v1/search/semantic` - Natural language search using AI
- `POST /api/v1/search/hybrid` - Combined semantic and filter search
- `GET /api/v1/search/similar/{id}` - Find similar items using AI
- `GET /api/v1/search/health` - Check search service status

## 📁 Project Structure

```
InventorySystem/
├── README.md                 # This file
├── CLAUDE.md                 # AI assistant guidelines
├── DEVELOPMENT_LOG.md        # Development progress log
├── Architecture.md           # Technical architecture
├── .gitignore               # Git ignore rules
├── docker-compose.yml       # Container orchestration
│
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API route handlers
│   │   │   └── v1/         # API version 1
│   │   ├── core/           # Core utilities (logging, etc.)
│   │   ├── database/       # Database configuration
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   └── services/       # Business logic layer
│   ├── tests/              # Test suite
│   ├── scripts/            # Utility scripts
│   ├── alembic/            # Database migrations
│   ├── data/               # Database files (SQLite)
│   ├── pyproject.toml      # Poetry configuration
│   └── .env                # Environment variables
│
├── frontend/               # Streamlit frontend
│   ├── app.py             # Main application entry
│   ├── pages/             # Streamlit pages
│   ├── components/        # Reusable UI components
│   ├── utils/             # Frontend utilities
│   ├── tests/             # Frontend tests
│   └── pyproject.toml     # Poetry configuration
│
└── docs/                  # Additional documentation
    ├── database-operations.md
    ├── development-workflow.md
    ├── testing-runbook.md
    └── troubleshooting-playbook.md
```

## 🔍 Common Issues & Troubleshooting

### Python Version Issues
**Problem**: AsyncPG compilation errors on Python 3.13
```bash
# Solution: Use Python 3.12
poetry env remove --all
poetry env use python3.12
poetry install
```

### Database Connection Issues
**Problem**: Cannot connect to PostgreSQL
```bash
# Check PostgreSQL status
pg_ctl status

# Verify connection settings
poetry run python -c "from app.database.config import DatabaseConfig; print(DatabaseConfig.get_database_url())"

# Test connection manually
poetry run python -c "
import asyncio
from app.database.base import engine
async def test():
    async with engine.begin() as conn:
        result = await conn.execute('SELECT 1')
        print('Connection successful:', result.scalar())
asyncio.run(test())
"
```

### Migration Issues
**Problem**: Alembic migration errors
```bash
# Check current migration status
poetry run alembic current

# Reset migrations (destructive)
poetry run alembic downgrade base
poetry run alembic upgrade head

# Generate new migration
poetry run alembic revision --autogenerate -m "description"
```

### Port Conflicts
**Problem**: Ports 8000 or 8501 already in use
```bash
# Find process using port
lsof -i :8000
lsof -i :8501

# Kill process
kill -9 <PID>

# Use alternative ports
poetry run uvicorn app.main:app --port 8001
poetry run streamlit run app.py --server.port 8502
```

## 🚢 Deployment

### Docker Compose (Recommended)
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Manual Deployment
```bash
# Backend (production)
cd backend
poetry install --no-dev
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend (production)
cd frontend
poetry install --no-dev
poetry run streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow the development process in `CLAUDE.md`
4. Update `DEVELOPMENT_LOG.md` with your changes
5. Run all tests (`poetry run pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Code Standards
- **Type Hints**: All functions must have type annotations
- **Docstrings**: All public functions and classes must have docstrings
- **Testing**: New features must include tests
- **Code Quality**: All code must pass Black, Flake8, and MyPy checks

### Documentation
- Update `DEVELOPMENT_LOG.md` for significant changes
- Update API documentation for new endpoints
- Add examples for new features

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/) for the backend
- UI powered by [Streamlit](https://streamlit.io/)
- Database management with [SQLAlchemy](https://www.sqlalchemy.org/)
- Dependency management by [Poetry](https://python-poetry.org/)

## 📞 Support

- **Documentation**: Check the `docs/` directory for detailed guides
- **Issues**: Report bugs via GitHub Issues
- **Development**: See `DEVELOPMENT_LOG.md` for current status
- **Architecture**: Refer to `Architecture.md` for technical details

---

**Project Status**: ✅ Phase 1.5 Complete - Core CRUD functionality with PostgreSQL + Frontend Robustness  
**Latest Updates**: All frontend issues resolved, complete item management functional  
**Next Phase**: Inventory system integration and advanced features

### Recent Improvements (Latest Release - July 2025)
- **✅ Items Page Fully Functional**: Complete end-to-end item creation and management
- **✅ Schema Architecture Fix**: Resolved backend schema-model mismatch for items
- **✅ Currency Formatting Safety**: Eliminated all frontend formatting errors
- **✅ API Robustness**: Backend APIs handle edge cases and invalid data gracefully
- **✅ Git & Documentation Standards**: Established comprehensive development standards

**Current Capabilities**: 
- **Full CRUD Operations**: Complete management of locations, categories, and items
- **Robust Frontend**: Error-free user interface with safe data handling
- **Advanced Search & Filtering**: Multiple criteria search with intuitive UI
- **Data Visualization**: Comprehensive analytics and reporting dashboards  
- **Production-Ready Backend**: PostgreSQL with 40+ API endpoints including AI-powered search
- **Professional Development Process**: Comprehensive documentation and git standards

### Phase 2 Complete ✅
- **✅ Semantic Search**: Full Weaviate integration with natural language queries
- **✅ Similar Items**: AI-powered item recommendations
- **✅ Dual Database**: PostgreSQL + Weaviate with graceful fallback
- **✅ 40+ API Endpoints**: Comprehensive REST API with search capabilities

### Phase 3 Roadmap (Ready to Begin)
- **🔐 Authentication**: Streamlit-Authenticator integration with secure sessions
- **📸 Image Support**: Photo upload and thumbnail generation for items
- **🏭 Production Hardening**: Environment configs, monitoring, and deployment
- **📱 Mobile Features**: Camera integration and barcode scanning