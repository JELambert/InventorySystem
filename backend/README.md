# Home Inventory System - Backend

## Quick Start (Development)

### Option 1: Local Development (Recommended)

1. **Install dependencies (minimal set):**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements-dev.txt
   ```

2. **Run the application:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

3. **Test the application:**
   - Visit: http://localhost:8000
   - API docs: http://localhost:8000/docs
   - Health check: http://localhost:8000/health

4. **Run tests and code quality:**
   ```bash
   # Recommended way to run tests (handles Python path automatically)
   python run_tests.py
   
   # Alternative ways:
   PYTHONPATH=. python -m pytest tests/test_database_base.py -v
   python scripts/verify_step_1_2a.py  # Manual verification
   
   # Code quality checks
   black --check .
   flake8
   mypy app/
   ```

### Option 2: Docker Development

If you encounter installation issues, use Docker:

```bash
# Build and run development container
docker-compose -f docker-compose.dev.yml up --build

# Or run individual commands
docker-compose -f docker-compose.dev.yml run backend-dev pytest
docker-compose -f docker-compose.dev.yml run backend-dev black --check .
```

## Requirements Files

- `requirements-dev.txt`: Minimal working dependencies for development
- `requirements.txt`: Full production dependencies (may need system packages)

## Development Database

Currently configured to use SQLite for development:
- No external database required
- Database file: `inventory.db` (auto-created)
- Easy to reset: just delete the file

## Troubleshooting

### Installation Issues

If `pip install -r requirements-dev.txt` fails:

1. **Try upgrading pip:**
   ```bash
   pip install --upgrade pip
   ```

2. **Use Docker instead:**
   ```bash
   docker-compose -f docker-compose.dev.yml up --build
   ```

3. **Install one package at a time to identify the problem:**
   ```bash
   pip install fastapi
   pip install uvicorn[standard]
   # etc.
   ```

### Common Issues

- **Import errors**: Make sure you're in the backend directory and virtual environment is activated
- **Port conflicts**: Change port in uvicorn command: `--port 8001`
- **Permission errors**: Check file permissions and user ownership

## Next Steps

Once basic development is working:
1. Move to Step 1.2: Database Models Foundation
2. Add PostgreSQL for production (requires system dependencies)
3. Add Weaviate integration for semantic search