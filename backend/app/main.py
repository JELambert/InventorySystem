from typing import Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from app.core.logging import LoggingConfig, get_logger
from app.api import router as api_router
from app.services.weaviate_service import get_weaviate_service, close_weaviate_service

# Initialize logging
LoggingConfig.setup_logging()
logger = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    logger.info("Initializing Weaviate service...")
    try:
        weaviate_service = await get_weaviate_service()
        if await weaviate_service.health_check():
            logger.info("Weaviate service initialized successfully")
        else:
            logger.warning("Weaviate service initialized but not healthy")
    except Exception as e:
        logger.error(f"Failed to initialize Weaviate service: {e}")
        logger.info("Application will continue with traditional search only")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Weaviate service...")
    await close_weaviate_service()
    logger.info("Application shutdown complete")


app: FastAPI = FastAPI(
    title="Home Inventory System API",
    description="A simple home inventory management system with semantic search",
    version="0.1.0",
    lifespan=lifespan
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
    
    # Check Weaviate connection
    weaviate_healthy = False
    try:
        weaviate_service = await get_weaviate_service()
        weaviate_healthy = await weaviate_service.health_check()
    except Exception as e:
        logger.debug(f"Weaviate health check failed: {e}")
    
    if db_healthy:
        status = "healthy" if weaviate_healthy else "partial"
        logger.debug(f"Health check: {status}")
        return {
            "status": status,
            "database": "connected",
            "weaviate": "connected" if weaviate_healthy else "disconnected",
            "semantic_search": "available" if weaviate_healthy else "unavailable"
        }
    else:
        logger.warning("Health check failed - database connection issue")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "weaviate": "connected" if weaviate_healthy else "disconnected",
            "semantic_search": "unavailable"
        }
