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
            logger.debug(f"Building prompt for template {self.template_type} with context keys: {list(context.keys())}")
            return self.user_prompt_template.format(**context)
        except KeyError as e:
            logger.error(f"Missing context key for template {self.template_type}: {e}")
            logger.error(f"Available context keys: {list(context.keys())}")
            logger.error(f"Template content: {self.user_prompt_template[:200]}...")
            raise ValueError(f"Missing required context for {self.template_type}: {e}")


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
            ),
            "item_data_enrichment": ContentTemplate(
                template_type="item_data_enrichment",
                system_prompt=(
                    "You are an expert product analyst that enriches inventory item data. "
                    "You provide comprehensive item information including standardized names, "
                    "likely manufacturers, model identification, and realistic market value estimates. "
                    "Always respond with valid JSON format and include confidence scores for your assessments."
                ),
                user_prompt_template=(
                    "Based on the provided item information, generate comprehensive item data:\n"
                    "\n"
                    "Input Information:\n"
                    "Name: {name}\n"
                    "Category: {category}\n"
                    "Type: {item_type}\n"
                    "{brand_info}{model_info}"
                    "\n"
                    "Generate a JSON response with the following structure:\n"
                    "{{\n"
                    '  "refined_name": "Improved/standardized item name",\n'
                    '  "brand": "Likely manufacturer (null if uncertain)",\n'
                    '  "model": "Likely model number/name (null if uncertain)",\n'
                    '  "item_type": "Validated/corrected item type",\n'
                    '  "estimated_value": "Estimated current market value in USD (number or null)",\n'
                    '  "description": "Detailed description (100+ words)",\n'
                    '  "confidence_scores": {{\n'
                    '    "refined_name": 0.95,\n'
                    '    "brand": 0.85,\n'
                    '    "model": 0.70,\n'
                    '    "item_type": 0.90,\n'
                    '    "estimated_value": 0.75,\n'
                    '    "description": 0.95\n'
                    "  }}\n"
                    "}}\n"
                    "\n"
                    "Requirements:\n"
                    "- Use industry knowledge for brand/model inference\n"
                    "- Provide realistic value estimates based on current market\n"
                    "- Set confidence scores (0.0-1.0) based on certainty\n"
                    "- Return null for fields with low confidence (<0.6)\n"
                    "- Ensure refined_name is clear and standardized\n"
                    "- Include detailed description with utilities and uses\n"
                    "- Response must be valid JSON only, no additional text\n"
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
        if template_type in ["item_description", "item_data_enrichment"]:
            # Prepare item-specific context for both description and enrichment templates
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
            
            logger.debug(f"Prepared context for {template_type}: {prepared}")
            return prepared
        
        # For generic templates, pass context as-is
        logger.debug(f"Using raw context for {template_type}: {context}")
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
    
    async def generate_item_data_enrichment(
        self,
        name: str,
        category: Optional[str] = None,
        item_type: Optional[str] = None,
        brand: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate comprehensive item data enrichment including multiple fields.
        
        Args:
            name: Item name (required)
            category: Item category
            item_type: Type of item
            brand: Brand name (if known)
            model: Model name/number (if known)
            **kwargs: Additional context or preferences
            
        Returns:
            Dictionary with enriched item data and confidence scores
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
        
        try:
            result = await self.generate_content("item_data_enrichment", context, user_preferences)
            
            # Parse the JSON response
            import json
            try:
                enriched_data = json.loads(result.content)
                
                # Add metadata from the generation result
                enriched_data["_metadata"] = {
                    "model": result.model,
                    "tokens_used": result.tokens_used,
                    "generation_time": result.generation_time,
                    "timestamp": result.timestamp.isoformat()
                }
                
                return enriched_data
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response from AI: {e}")
                logger.error(f"Raw response: {result.content}")
                
                # Fallback: return basic structure with original content as description
                return {
                    "refined_name": name,
                    "brand": brand,
                    "model": model,
                    "item_type": item_type or "item",
                    "estimated_value": None,
                    "description": result.content,  # Use raw content as description
                    "confidence_scores": {
                        "refined_name": 0.5,
                        "brand": 0.3 if brand else 0.0,
                        "model": 0.3 if model else 0.0,
                        "item_type": 0.5,
                        "estimated_value": 0.0,
                        "description": 0.8
                    },
                    "_metadata": {
                        "model": result.model,
                        "tokens_used": result.tokens_used,
                        "generation_time": result.generation_time,
                        "timestamp": result.timestamp.isoformat(),
                        "parse_error": str(e)
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to generate item data enrichment: {e}")
            raise
    
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
    
    async def analyze_item_from_image(
        self,
        image_data: bytes,
        image_format: str,
        context_hints: Optional[Dict[str, Any]] = None,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze an item image using AI vision to extract comprehensive item data.
        
        Args:
            image_data: Raw image bytes
            image_format: Image MIME type (e.g., 'image/jpeg')
            context_hints: Optional context hints for better analysis
            user_preferences: Optional user preferences for generation
            
        Returns:
            Dictionary containing extracted item data with confidence scores
        """
        if not self._openai_client:
            raise RuntimeError("OpenAI client is not available")
        
        logger.info(f"Starting image analysis for {len(image_data)} bytes of {image_format}")
        start_time = datetime.now()
        
        try:
            import base64
            
            # Encode image to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Build context from hints
            context_text = ""
            if context_hints:
                location = context_hints.get("location", "")
                additional = context_hints.get("additional_context", "")
                if location:
                    context_text += f"Location context: {location}. "
                if additional:
                    context_text += f"Additional context: {additional}. "
            
            # Create vision prompt for comprehensive item analysis
            system_prompt = """You are an expert inventory analyst with extensive knowledge of consumer products, electronics, household items, tools, and collectibles. Your task is to analyze item images and extract comprehensive data for inventory management.

Analyze the provided image and extract ALL possible information in valid JSON format with the following structure:

{
    "refined_name": "Precise, standardized item name (2-4 words)",
    "brand": "Identified brand name (if visible/recognizable)",
    "model": "Model number/name (if visible/identifiable)",
    "item_type": "Specific category (e.g., smartphone, laptop, book, tool)",
    "estimated_value": "Current market value in USD (number only)",
    "description": "Detailed description including condition, features, and notable characteristics",
    "condition": "New/Excellent/Good/Fair/Poor based on visual assessment",
    "color": "Primary color(s)",
    "material": "Primary material (if identifiable)",
    "confidence_scores": {
        "refined_name": 0.0-1.0,
        "brand": 0.0-1.0,
        "model": 0.0-1.0,
        "item_type": 0.0-1.0,
        "estimated_value": 0.0-1.0,
        "description": 0.0-1.0
    }
}

IMPORTANT GUIDELINES:
- Only include fields you can reasonably identify from the image
- Set confidence scores based on visual clarity and certainty
- For estimated_value, consider condition, brand, and market knowledge
- Be conservative with confidence scores - prefer accuracy over optimism
- If text/labels are visible, use them for brand/model identification
- Include condition assessment based on visible wear, damage, or newness"""

            user_prompt = f"""Analyze this item image and extract comprehensive inventory data. 

{context_text}

Focus on:
1. Identifying the item precisely (name, brand, model)
2. Assessing market value based on condition and type
3. Providing detailed description including condition
4. Setting realistic confidence scores for each field

Return ONLY valid JSON with no additional text."""

            # Get model from user preferences - use latest vision model
            default_vision_model = "gpt-4o"  # Updated to latest vision-capable model
            model = user_preferences.get("model", default_vision_model) if user_preferences else default_vision_model
            
            logger.info(f"Using vision model: {model} for image analysis")
            
            # Create vision API call
            response = await self._openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{image_format};base64,{image_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1500,
                temperature=0.3  # Lower temperature for more consistent analysis
            )
            
            generation_time = (datetime.now() - start_time).total_seconds()
            
            # Parse JSON response
            content = response.choices[0].message.content.strip()
            
            # Clean up response (remove markdown formatting if present)
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            try:
                import json
                result_data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI response as JSON: {e}")
                logger.error(f"Response content: {content}")
                raise ValueError(f"AI returned invalid JSON: {e}")
            
            # Add metadata
            result_data["_metadata"] = {
                "model": model,
                "tokens_used": response.usage.total_tokens,
                "generation_time": generation_time,
                "image_size": len(image_data),
                "image_format": image_format,
                "analysis_type": "vision"
            }
            
            # Calculate average confidence if individual scores exist
            confidence_scores = result_data.get("confidence_scores", {})
            if confidence_scores:
                avg_confidence = sum(confidence_scores.values()) / len(confidence_scores)
                result_data["_metadata"]["avg_confidence"] = avg_confidence
            
            logger.info(f"Completed image analysis in {generation_time:.2f}s using {response.usage.total_tokens} tokens")
            return result_data
            
        except Exception as e:
            logger.error(f"Failed to analyze image with model {model}: {e}")
            logger.error(f"Image details: {len(image_data)} bytes, format: {image_format}")
            
            # Provide more specific error information
            if "model" in str(e).lower():
                raise RuntimeError(f"Vision model '{model}' not available or not supported")
            elif "rate limit" in str(e).lower():
                raise RuntimeError("OpenAI API rate limit exceeded. Please try again later")
            elif "api key" in str(e).lower() or "unauthorized" in str(e).lower():
                raise RuntimeError("OpenAI API authentication failed. Please check API key")
            else:
                raise RuntimeError(f"Image analysis failed: {str(e)}")


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