"""
AI content generation components for the Home Inventory System.

Reusable components for AI-powered content generation including buttons,
modals, and settings for generating descriptions and other content.
"""

import streamlit as st
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from utils.api_client import APIClient, APIError
from utils.helpers import (
    safe_api_call, show_error, show_success, show_warning,
    handle_api_error, safe_strip, safe_string_check
)

logger = logging.getLogger(__name__)


def ai_generation_button(
    label: str = "✨ AI Generate",
    help_text: str = "Generate content using AI",
    key: str = "ai_generate_btn",
    disabled: bool = False,
    button_type: str = "secondary"
) -> bool:
    """
    Create a reusable AI generation button.
    
    Args:
        label: Button label text
        help_text: Help text for the button
        key: Unique key for the button
        disabled: Whether the button is disabled
        button_type: Button type (primary, secondary)
        
    Returns:
        bool: True if button was clicked
    """
    return st.button(
        label,
        help=help_text,
        key=key,
        disabled=disabled,
        type=button_type
    )


def ai_generation_modal(
    api_client: APIClient,
    generation_type: str,
    context: Dict[str, Any],
    modal_key: str = "ai_modal",
    title: str = "AI Content Generation"
) -> Optional[str]:
    """
    Display AI generation modal with loading and result handling.
    
    Args:
        api_client: API client instance
        generation_type: Type of content to generate
        context: Context data for generation
        modal_key: Unique key for the modal
        title: Modal title
        
    Returns:
        Generated content if successful, None otherwise
    """
    
    # Check if modal should be shown
    show_modal_key = f"show_{modal_key}"
    if not st.session_state.get(show_modal_key, False):
        return None
    
    # Create modal container
    with st.container():
        st.markdown(f"### {title}")
        
        # Show context information
        with st.expander("📋 Generation Context", expanded=False):
            for key, value in context.items():
                if value:
                    st.write(f"**{key.replace('_', ' ').title()}:** {value}")
        
        # Generation controls
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🚀 Generate", key=f"{modal_key}_generate", type="primary"):
                return _perform_generation(api_client, generation_type, context, modal_key)
        
        with col2:
            if st.button("🔄 Regenerate", key=f"{modal_key}_regenerate"):
                return _perform_generation(api_client, generation_type, context, modal_key)
        
        with col3:
            if st.button("❌ Cancel", key=f"{modal_key}_cancel"):
                st.session_state[show_modal_key] = False
                st.rerun()
        
        # Show previous result if available
        result_key = f"{modal_key}_result"
        if result_key in st.session_state:
            result = st.session_state[result_key]
            
            st.markdown("### Generated Content")
            
            # Show metadata
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Model", result.get("model", "Unknown"))
            with col2:
                st.metric("Tokens", result.get("tokens_used", 0))
            with col3:
                st.metric("Time", f"{result.get('generation_time', 0):.1f}s")
            
            # Editable content
            edited_content = st.text_area(
                "Content (you can edit before using):",
                value=result.get("content", ""),
                height=200,
                key=f"{modal_key}_edit"
            )
            
            # Action buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Use This Content", key=f"{modal_key}_use", type="primary"):
                    st.session_state[show_modal_key] = False
                    return edited_content
            
            with col2:
                if st.button("🗑️ Clear", key=f"{modal_key}_clear"):
                    if result_key in st.session_state:
                        del st.session_state[result_key]
                    st.rerun()
    
    return None


def _perform_generation(
    api_client: APIClient,
    generation_type: str,
    context: Dict[str, Any],
    modal_key: str
) -> Optional[str]:
    """Perform the actual AI content generation."""
    
    with st.spinner("🤖 Generating content with AI..."):
        try:
            if generation_type == "item_description":
                result = safe_api_call(
                    lambda: api_client.generate_item_description(context),
                    "Failed to generate item description"
                )
            else:
                result = safe_api_call(
                    lambda: api_client.generate_ai_content(generation_type, context),
                    f"Failed to generate {generation_type} content"
                )
            
            if result:
                st.session_state[f"{modal_key}_result"] = result
                show_success("Content generated successfully!")
                st.rerun()
            else:
                show_error("Failed to generate content. Please try again.")
                
        except Exception as e:
            logger.error(f"AI generation error: {e}")
            handle_api_error(e, "generate AI content")
    
    return None


def ai_item_description_generator(
    api_client: APIClient,
    name: str,
    category: Optional[str] = None,
    item_type: Optional[str] = None,
    brand: Optional[str] = None,
    model: Optional[str] = None,
    key_prefix: str = "item_desc"
) -> Optional[str]:
    """
    Complete AI description generator component for items.
    
    Args:
        api_client: API client instance
        name: Item name (required)
        category: Item category
        item_type: Item type
        brand: Brand name
        model: Model name
        key_prefix: Unique key prefix for this component
        
    Returns:
        Generated description if user accepts it, None otherwise
    """
    
    # Validation
    if not safe_string_check(name):
        st.warning("⚠️ Item name is required for AI description generation")
        return None
    
    # Button to trigger generation
    col1, col2 = st.columns([1, 4])
    with col1:
        if ai_generation_button(
            label="✨ AI Generate",
            help_text="Generate description using AI based on item details",
            key=f"{key_prefix}_btn",
            disabled=not name
        ):
            st.session_state[f"show_{key_prefix}_modal"] = True
            st.rerun()
    
    with col2:
        st.caption("Generate a detailed description using AI based on the item information above")
    
    # Context for generation
    context = {
        "name": safe_strip(name),
        "category": category or "General",
        "item_type": item_type or "item",
        "brand": brand,
        "model": model
    }
    
    # Show modal and handle result
    result = ai_generation_modal(
        api_client=api_client,
        generation_type="item_description",
        context=context,
        modal_key=f"{key_prefix}_modal",
        title="🤖 Generate Item Description"
    )
    
    return result


def ai_generation_settings() -> Dict[str, Any]:
    """
    AI generation settings component for user preferences.
    
    Returns:
        Dictionary of user preferences for AI generation
    """
    
    with st.expander("🤖 AI Generation Settings"):
        st.markdown("**Model Selection**")
        model = st.selectbox(
            "AI Model",
            ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
            index=0,
            help="Choose the AI model for content generation"
        )
        
        st.markdown("**Generation Preferences**")
        col1, col2 = st.columns(2)
        
        with col1:
            creativity = st.slider(
                "Creativity Level",
                min_value=0.0,
                max_value=1.0,
                value=0.7,
                step=0.1,
                help="Higher values = more creative/varied content"
            )
        
        with col2:
            length_preference = st.selectbox(
                "Content Length",
                ["Short (50-100 words)", "Medium (100-200 words)", "Long (200+ words)"],
                index=1,
                help="Preferred length for generated content"
            )
        
        # Additional preferences
        include_utilities = st.checkbox(
            "Include utilities and uses",
            value=True,
            help="Include possible uses and utilities in descriptions"
        )
        
        professional_tone = st.checkbox(
            "Professional tone",
            value=True,
            help="Use professional language in generated content"
        )
    
    return {
        "model": model,
        "temperature": creativity,
        "length_preference": length_preference,
        "include_utilities": include_utilities,
        "professional_tone": professional_tone
    }


def ai_health_indicator(api_client: APIClient) -> None:
    """
    Display AI service health indicator.
    
    Args:
        api_client: API client instance
    """
    
    # Check AI service health
    health_data = safe_api_call(
        lambda: api_client.get_ai_health(),
        "Failed to check AI service health"
    )
    
    if health_data:
        status = health_data.get("status", "unknown")
        
        if status == "healthy":
            st.success("🤖 AI generation is available")
        elif status == "degraded":
            st.warning("⚠️ AI generation is partially available")
        else:
            st.error("❌ AI generation is unavailable")
            
        # Show additional details in expander
        with st.expander("AI Service Details"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Status:** {status}")
                st.write(f"**Model:** {health_data.get('model', 'Unknown')}")
                
            with col2:
                st.write(f"**OpenAI Client:** {'✅' if health_data.get('openai_client') else '❌'}")
                st.write(f"**API Connectivity:** {'✅' if health_data.get('api_connectivity') else '❌'}")
            
            if health_data.get("available_templates"):
                st.write("**Available Templates:**")
                for template in health_data["available_templates"]:
                    st.write(f"• {template}")
            
            if health_data.get("error"):
                st.error(f"Error: {health_data['error']}")
    else:
        st.error("❌ Cannot check AI service status")


def ai_usage_stats() -> None:
    """Display AI usage statistics for the session."""
    
    # Get usage stats from session state
    total_generations = st.session_state.get("ai_total_generations", 0)
    total_tokens = st.session_state.get("ai_total_tokens", 0)
    
    if total_generations > 0:
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("AI Generations", total_generations)
        
        with col2:
            st.metric("Total Tokens", total_tokens)
    else:
        st.info("No AI generations in this session yet")


def update_ai_usage_stats(tokens_used: int) -> None:
    """Update AI usage statistics in session state."""
    
    current_generations = st.session_state.get("ai_total_generations", 0)
    current_tokens = st.session_state.get("ai_total_tokens", 0)
    
    st.session_state.ai_total_generations = current_generations + 1
    st.session_state.ai_total_tokens = current_tokens + tokens_used