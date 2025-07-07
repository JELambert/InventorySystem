"""
AI generation endpoints for the Home Inventory System API.

Provides endpoints for AI-powered content generation including item descriptions
and other content types using OpenAI language models.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from pydantic import BaseModel, Field
import json

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


class ItemDataEnrichmentRequest(BaseModel):
    """Request model for comprehensive item data enrichment."""
    name: str = Field(..., description="Item name", min_length=1, max_length=255)
    category: Optional[str] = Field(None, description="Item category")
    item_type: Optional[str] = Field(None, description="Type of item")
    brand: Optional[str] = Field(None, description="Known brand name")
    model: Optional[str] = Field(None, description="Known model name/number")
    user_preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences for generation")


class AIGenerationResponse(BaseModel):
    """Response model for AI content generation."""
    content: str = Field(..., description="Generated content")
    template_type: str = Field(..., description="Template type used")
    model: str = Field(..., description="AI model used")
    tokens_used: int = Field(..., description="Number of tokens consumed")
    generation_time: float = Field(..., description="Generation time in seconds")
    timestamp: str = Field(..., description="Generation timestamp")


class ItemDataEnrichmentResponse(BaseModel):
    """Response model for comprehensive item data enrichment."""
    refined_name: Optional[str] = Field(None, description="Improved/standardized item name")
    brand: Optional[str] = Field(None, description="Identified or likely brand")
    model: Optional[str] = Field(None, description="Identified or likely model")
    item_type: Optional[str] = Field(None, description="Validated/corrected item type")
    estimated_value: Optional[float] = Field(None, description="Estimated current market value in USD")
    description: Optional[str] = Field(None, description="Detailed item description")
    confidence_scores: Dict[str, float] = Field(..., description="Confidence scores for each field (0.0-1.0)")
    metadata: Dict[str, Any] = Field(..., description="Generation metadata (model, tokens, time, etc.)")


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


@router.post("/enrich-item-data", response_model=ItemDataEnrichmentResponse)
async def enrich_item_data(request: ItemDataEnrichmentRequest) -> ItemDataEnrichmentResponse:
    """
    Generate comprehensive item data enrichment including multiple fields.
    
    This endpoint analyzes basic item information and generates enriched data
    including refined name, brand/model identification, estimated value, and description.
    Each field includes confidence scores to help users make informed decisions.
    """
    try:
        ai_service = await get_ai_service()
        
        enriched_data = await ai_service.generate_item_data_enrichment(
            name=request.name,
            category=request.category,
            item_type=request.item_type,
            brand=request.brand,
            model=request.model,
            user_preferences=request.user_preferences
        )
        
        # Extract metadata
        metadata = enriched_data.pop("_metadata", {})
        
        return ItemDataEnrichmentResponse(
            refined_name=enriched_data.get("refined_name"),
            brand=enriched_data.get("brand"),
            model=enriched_data.get("model"),
            item_type=enriched_data.get("item_type"),
            estimated_value=enriched_data.get("estimated_value"),
            description=enriched_data.get("description"),
            confidence_scores=enriched_data.get("confidence_scores", {}),
            metadata=metadata
        )
        
    except ValueError as e:
        logger.warning(f"Invalid request for item data enrichment: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.error(f"AI service not available: {e}")
        raise HTTPException(status_code=503, detail="AI service is not available")
    except Exception as e:
        logger.error(f"Failed to enrich item data: {e}")
        raise HTTPException(status_code=500, detail="Failed to enrich item data")


@router.post("/analyze-item-image", response_model=ItemDataEnrichmentResponse)
async def analyze_item_image(
    image: UploadFile = File(..., description="Item image file (JPEG, PNG, WEBP)"),
    context_hints: str = Form(None, description="Optional context hints as JSON string"),
    user_preferences: str = Form(None, description="Optional user preferences as JSON string")
) -> ItemDataEnrichmentResponse:
    """
    Analyze an item image using AI vision to extract comprehensive item data.
    
    This endpoint accepts an image file and uses AI vision capabilities to identify
    and extract item information including name, brand, model, estimated value, 
    condition, and detailed description.
    """
    try:
        # Validate image file
        if not image.content_type or not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Check file size (10MB limit)
        if hasattr(image, 'size') and image.size > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Image file too large (max 10MB)")
        
        # Read image data
        image_data = await image.read()
        if len(image_data) == 0:
            raise HTTPException(status_code=400, detail="Empty image file")
        
        # Parse context hints if provided
        context_data = {}
        if context_hints:
            try:
                context_data = json.loads(context_hints)
            except json.JSONDecodeError:
                logger.warning(f"Invalid context hints JSON: {context_hints}")
        
        # Parse user preferences if provided
        preferences_data = {}
        if user_preferences:
            try:
                preferences_data = json.loads(user_preferences)
            except json.JSONDecodeError:
                logger.warning(f"Invalid user preferences JSON: {user_preferences}")
        
        # Get AI service and analyze image
        ai_service = await get_ai_service()
        
        enriched_data = await ai_service.analyze_item_from_image(
            image_data=image_data,
            image_format=image.content_type,
            context_hints=context_data,
            user_preferences=preferences_data
        )
        
        # Extract metadata
        metadata = enriched_data.pop("_metadata", {})
        
        return ItemDataEnrichmentResponse(
            refined_name=enriched_data.get("refined_name"),
            brand=enriched_data.get("brand"),
            model=enriched_data.get("model"),
            item_type=enriched_data.get("item_type"),
            estimated_value=enriched_data.get("estimated_value"),
            description=enriched_data.get("description"),
            confidence_scores=enriched_data.get("confidence_scores", {}),
            metadata=metadata
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        logger.warning(f"Invalid request for image analysis: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        logger.error(f"AI service not available: {e}")
        raise HTTPException(status_code=503, detail="AI service is not available")
    except Exception as e:
        logger.error(f"Failed to analyze image: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze image")


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