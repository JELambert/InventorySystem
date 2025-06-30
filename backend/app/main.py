from typing import Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.logging import LoggingConfig, get_logger
from app.api import router as api_router

# Initialize logging
LoggingConfig.setup_logging()
logger = get_logger("api")

app: FastAPI = FastAPI(
    title="Home Inventory System API",
    description="A simple home inventory management system",
    version="0.1.0",
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],  # Streamlit default
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)

logger.info("Home Inventory System API starting up")


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint returning basic API information."""
    logger.debug("Root endpoint accessed")
    return {"message": "Home Inventory System API"}


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint for monitoring."""
    from app.database.base import check_connection
    
    logger.debug("Health check endpoint accessed")
    
    # Check database connection
    db_healthy = await check_connection()
    
    if db_healthy:
        logger.debug("Health check passed")
        return {"status": "healthy", "database": "connected"}
    else:
        logger.warning("Health check failed - database connection issue")
        return {"status": "unhealthy", "database": "disconnected"}
