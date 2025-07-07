"""
AI content generation service for the Home Inventory System.

This service provides generic AI-powered content generation capabilities
using OpenAI's language models. Designed to be reusable across different
content types and contexts.
"""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass

from openai import AsyncOpenAI
from app.services.weaviate_service import get_weaviate_service

logger = logging.getLogger(__name__)


@dataclass
class AIGenerationResult:
    """Result of AI content generation."""
    content: str
    template_type: str
    context: Dict[str, Any]
    model: str
    tokens_used: int
    generation_time: float
    timestamp: datetime


class ContentTemplate:
    """Template for AI content generation."""
    
    def __init__(self, template_type: str, system_prompt: str, user_prompt_template: str):
        self.template_type = template_type
        self.system_prompt = system_prompt
        self.user_prompt_template = user_prompt_template
    
    def build_prompt(self, context: Dict[str, Any]) -> str:
        """Build the user prompt from context data."""
        try:
            return self.user_prompt_template.format(**context)
        except KeyError as e:
            logger.error(f"Missing context key for template {self.template_type}: {e}")
            raise ValueError(f"Missing required context: {e}")


class AIService:
    """Service for AI-powered content generation."""
    
    def __init__(self):
        self._openai_client: Optional[AsyncOpenAI] = None
        self._model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        self._templates = self._initialize_templates()
        
    async def initialize(self) -> bool:
        """Initialize the AI service with OpenAI client."""
        try:
            # Get OpenAI client from WeaviateService
            weaviate_service = await get_weaviate_service()
            if weaviate_service and hasattr(weaviate_service, '_openai_client'):
                self._openai_client = weaviate_service._openai_client
                logger.info("AI service initialized using existing OpenAI client")
                return True
            else:
                # Fallback: create our own client
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    logger.error("OpenAI API key not found")
                    return False
                
                self._openai_client = AsyncOpenAI(api_key=api_key)
                logger.info("AI service initialized with new OpenAI client")
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize AI service: {e}")
            return False
    
    def _initialize_templates(self) -> Dict[str, ContentTemplate]:
        """Initialize content generation templates."""
        return {
            "item_description": ContentTemplate(
                template_type="item_description",
                system_prompt=(
                    "You are a helpful assistant that creates detailed, informative descriptions "
                    "for inventory items. Your descriptions should be comprehensive, practical, "
                    "and help users understand both what the item is and how it might be used."
                ),
                user_prompt_template=(
                    "Create a detailed description for an inventory item with the following details:\n"
                    "Name: {name}\n"
                    "Category: {category}\n"
                    "Type: {item_type}\n"
                    "{brand_info}{model_info}"
                    "\n"
                    "Requirements:\n"
                    "- Write at least 100 words\n"
                    "- Include a clear description of what the item is\n"
                    "- Describe possible uses and utilities\n"
                    "- Be informative and practical\n"
                    "- Write in a professional but accessible tone\n"
                    "- Do not include pricing information\n"
                    "\n"
                    "Please write the description now:"
                )
            ),
            "generic_description": ContentTemplate(
                template_type="generic_description",
                system_prompt=(
                    "You are a helpful assistant that creates detailed, informative descriptions "
                    "based on the provided context and requirements."
                ),
                user_prompt_template=(
                    "Create a description based on the following context:\n"
                    "{context}\n"
                    "\n"
                    "Requirements:\n"
                    "{requirements}\n"
                    "\n"
                    "Please write the description now:"
                )
            )
        }
    
    async def generate_content(
        self,
        template_type: str,
        context: Dict[str, Any],
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> AIGenerationResult:
        """
        Generate content using AI based on template and context.
        
        Args:
            template_type: Type of content template to use
            context: Context data for content generation
            user_preferences: Optional user preferences (model, length, etc.)
            
        Returns:
            AIGenerationResult with generated content and metadata
        """
        if not self._openai_client:
            raise RuntimeError("AI service not initialized")
        
        if template_type not in self._templates:
            raise ValueError(f"Unknown template type: {template_type}")
        
        template = self._templates[template_type]
        
        start_time = datetime.now()
        
        try:
            # Prepare context for template
            formatted_context = self._prepare_context(context, template_type)
            
            # Build prompts
            user_prompt = template.build_prompt(formatted_context)
            
            # Apply user preferences
            model = user_preferences.get("model", self._model) if user_preferences else self._model
            
            # Generate content
            response = await self._openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": template.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1000,  # Adjust based on needs
                temperature=0.7,  # Balanced creativity
            )
            
            generation_time = (datetime.now() - start_time).total_seconds()
            
            result = AIGenerationResult(
                content=response.choices[0].message.content.strip(),
                template_type=template_type,
                context=context,
                model=model,
                tokens_used=response.usage.total_tokens,
                generation_time=generation_time,
                timestamp=datetime.now()
            )
            
            logger.info(f"Generated {template_type} content in {generation_time:.2f}s using {result.tokens_used} tokens")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate content: {e}")
            raise
    
    def _prepare_context(self, context: Dict[str, Any], template_type: str) -> Dict[str, Any]:
        """Prepare context data for template formatting."""
        if template_type == "item_description":
            # Prepare item-specific context
            prepared = {
                "name": context.get("name", "Unknown Item"),
                "category": context.get("category", "General"),
                "item_type": context.get("item_type", "item").replace("_", " ").title(),
            }
            
            # Add optional brand and model info
            brand = context.get("brand")
            model = context.get("model") 
            
            prepared["brand_info"] = f"Brand: {brand}\n" if brand else ""
            prepared["model_info"] = f"Model: {model}\n" if model else ""
            
            return prepared
        
        # For generic templates, pass context as-is
        return context
    
    async def generate_item_description(
        self,
        name: str,
        category: Optional[str] = None,
        item_type: Optional[str] = None,
        brand: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> AIGenerationResult:
        """
        Convenience method for generating item descriptions.
        
        Args:
            name: Item name (required)
            category: Item category
            item_type: Type of item
            brand: Brand name
            model: Model name/number
            **kwargs: Additional context or preferences
            
        Returns:
            AIGenerationResult with generated description
        """
        context = {
            "name": name,
            "category": category or "General",
            "item_type": item_type or "item",
            "brand": brand,
            "model": model
        }
        
        # Extract user preferences from kwargs
        user_preferences = kwargs.get("user_preferences", {})
        
        return await self.generate_content("item_description", context, user_preferences)
    
    def get_available_templates(self) -> List[str]:
        """Get list of available content templates."""
        return list(self._templates.keys())
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of AI service."""
        status = {
            "service": "AI Generation",
            "status": "healthy" if self._openai_client else "unavailable",
            "openai_client": self._openai_client is not None,
            "available_templates": self.get_available_templates(),
            "model": self._model
        }
        
        if self._openai_client:
            try:
                # Test basic API connectivity
                await self._openai_client.chat.completions.create(
                    model=self._model,
                    messages=[{"role": "user", "content": "Test"}],
                    max_tokens=1
                )
                status["api_connectivity"] = True
            except Exception as e:
                status["status"] = "degraded"
                status["api_connectivity"] = False
                status["error"] = str(e)
        
        return status


# Global service instance
_ai_service: Optional[AIService] = None


async def get_ai_service() -> AIService:
    """Get the global AI service instance."""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
        await _ai_service.initialize()
    return _ai_service


async def close_ai_service():
    """Clean up AI service resources."""
    global _ai_service
    if _ai_service:
        logger.info("AI service closed")
        _ai_service = None