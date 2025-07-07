"""
AI generation endpoints for the Home Inventory System API.

Provides endpoints for AI-powered content generation including item descriptions
and other content types using OpenAI language models.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from app.services.ai_service import get_ai_service, AIGenerationResult

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/ai", tags=["ai-generation"])


class ContentGenerationRequest(BaseModel):
    """Request model for generic content generation."""
    template_type: str = Field(..., description="Type of content template to use")
    context: Dict[str, Any] = Field(..., description="Context data for content generation")
    user_preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences for generation")


class ItemDescriptionRequest(BaseModel):
    """Request model for item description generation."""
    name: str = Field(..., description="Item name", min_length=1, max_length=255)
    category: Optional[str] = Field(None, description="Item category")
    item_type: Optional[str] = Field(None, description="Type of item")
    brand: Optional[str] = Field(None, description="Brand name")
    model: Optional[str] = Field(None, description="Model name/number")
    user_preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences for generation")


class AIGenerationResponse(BaseModel):
    """Response model for AI content generation."""
    content: str = Field(..., description="Generated content")
    template_type: str = Field(..., description="Template type used")
    model: str = Field(..., description="AI model used")
    tokens_used: int = Field(..., description="Number of tokens consumed")
    generation_time: float = Field(..., description="Generation time in seconds")
    timestamp: str = Field(..., description="Generation timestamp")


class AIHealthResponse(BaseModel):
    """Response model for AI service health check."""
    service: str = Field(..., description="Service name")
    status: str = Field(..., description="Service status")
    openai_client: bool = Field(..., description="OpenAI client availability")
    available_templates: list[str] = Field(..., description="Available content templates")
    model: str = Field(..., description="Default AI model")
    api_connectivity: Optional[bool] = Field(None, description="API connectivity status")
    error: Optional[str] = Field(None, description="Error message if any")


@router.post("/generate", response_model=AIGenerationResponse)
async def generate_content(request: ContentGenerationRequest) -> AIGenerationResponse:
    """
    Generate content using AI based on template and context.
    
    This is a generic endpoint that can be used for any type of content generation
    by specifying the appropriate template type and context.
    """
    try:
        ai_service = await get_ai_service()
        
        result = await ai_service.generate_content(
            template_type=request.template_type,
            context=request.context,
            user_preferences=request.user_preferences
        )
        
        return AIGenerationResponse(
            content=result.content,
            template_type=result.template_type,
            model=result.model,
            tokens_used=result.tokens_used,
            generation_time=result.generation_time,
            timestamp=result.timestamp.isoformat()
        )
        
    except ValueError as e:
        logger.warning(f"Invalid request for content generation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.error(f"AI service not available: {e}")
        raise HTTPException(status_code=503, detail="AI service is not available")
    except Exception as e:
        logger.error(f"Failed to generate content: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate content")


@router.post("/generate-item-description", response_model=AIGenerationResponse)
async def generate_item_description(request: ItemDescriptionRequest) -> AIGenerationResponse:
    """
    Generate a detailed description for an inventory item.
    
    This endpoint is specifically designed for creating item descriptions
    based on basic item information like name, category, type, brand, and model.
    """
    try:
        ai_service = await get_ai_service()
        
        result = await ai_service.generate_item_description(
            name=request.name,
            category=request.category,
            item_type=request.item_type,
            brand=request.brand,
            model=request.model,
            user_preferences=request.user_preferences
        )
        
        return AIGenerationResponse(
            content=result.content,
            template_type=result.template_type,
            model=result.model,
            tokens_used=result.tokens_used,
            generation_time=result.generation_time,
            timestamp=result.timestamp.isoformat()
        )
        
    except ValueError as e:
        logger.warning(f"Invalid request for item description generation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.error(f"AI service not available: {e}")
        raise HTTPException(status_code=503, detail="AI service is not available")
    except Exception as e:
        logger.error(f"Failed to generate item description: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate item description")


@router.get("/templates", response_model=list[str])
async def get_available_templates() -> list[str]:
    """
    Get list of available content generation templates.
    
    Returns a list of template types that can be used with the generic
    content generation endpoint.
    """
    try:
        ai_service = await get_ai_service()
        return ai_service.get_available_templates()
    except Exception as e:
        logger.error(f"Failed to get available templates: {e}")
        raise HTTPException(status_code=500, detail="Failed to get available templates")


@router.get("/health", response_model=AIHealthResponse)
async def get_ai_health() -> AIHealthResponse:
    """
    Check the health and status of the AI generation service.
    
    Returns information about service availability, API connectivity,
    available templates, and any errors.
    """
    try:
        ai_service = await get_ai_service()
        health_data = await ai_service.health_check()
        
        return AIHealthResponse(**health_data)
        
    except Exception as e:
        logger.error(f"Failed to check AI service health: {e}")
        # Return basic error response
        return AIHealthResponse(
            service="AI Generation",
            status="error",
            openai_client=False,
            available_templates=[],
            model="unknown",
            error=str(e)
        )


@router.post("/test", response_model=AIGenerationResponse)
async def test_ai_generation() -> AIGenerationResponse:
    """
    Test endpoint for AI generation functionality.
    
    Generates a simple test item description to verify that the AI service
    is working correctly. Useful for debugging and health checks.
    """
    try:
        ai_service = await get_ai_service()
        
        # Test with a simple item
        result = await ai_service.generate_item_description(
            name="Test Item",
            category="Electronics",
            item_type="device",
            brand="TestBrand",
            model="Model123"
        )
        
        return AIGenerationResponse(
            content=result.content,
            template_type=result.template_type,
            model=result.model,
            tokens_used=result.tokens_used,
            generation_time=result.generation_time,
            timestamp=result.timestamp.isoformat()
        )
        
    except Exception as e:
        logger.error(f"AI generation test failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI generation test failed: {str(e)}")