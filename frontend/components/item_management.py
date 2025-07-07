"""
Item management components for the Home Inventory System.

Reusable components for creating, editing, and managing items with comprehensive
field support and flexible location assignment options.
"""

import streamlit as st
import pandas as pd
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from utils.api_client import APIClient, APIError
from utils.helpers import (
    safe_api_call, show_error, show_success, show_warning,
    handle_api_error, SessionManager, safe_currency_format,
    safe_strip, safe_string_check, safe_string_or_none
)
from components.keyboard_shortcuts import (
    create_enhanced_search_box, create_quick_filter_buttons,
    create_pagination_controls, create_bulk_selection_interface,
    create_action_buttons_row
)
from components.photo_capture import (
    show_photo_capture_interface, display_photo_analysis_results,
    show_photo_analysis_progress
)

logger = logging.getLogger(__name__)


def show_ai_generation_interface(api_client: APIClient) -> Dict[str, str]:
    """
    Show AI generation interface outside of form context with multi-field support.
    
    Args:
        api_client: API client instance
        
    Returns:
        Dictionary with generated field values (description, refined_name, brand, model, item_type, estimated_value)
    """
    
    st.markdown("#### 🤖 AI Content Generator")
    
    # Basic inputs for AI generation
    col1, col2 = st.columns(2)
    
    with col1:
        ai_name = st.text_input("Item Name for AI", help="Name to use for AI content generation", key="ai_name_input")
        ai_category = st.text_input("Category", help="Category for better AI context", key="ai_category_input")
    
    with col2:
        ai_type = st.selectbox("Item Type", get_item_type_options(), help="Type for AI context", key="ai_type_input")
        ai_brand = st.text_input("Brand (optional)", help="Brand for more specific generation", key="ai_brand_input")
    
    # Generation mode selection
    st.markdown("**Generation Mode**")
    col_mode1, col_mode2 = st.columns(2)
    
    with col_mode1:
        generation_mode = st.radio(
            "What to generate:",
            ["📝 Description Only", "🧠 All Fields (Smart)", "📸 Photo Analysis"],
            help="Choose your AI generation method",
            key="ai_generation_mode"
        )
    
    with col_mode2:
        if generation_mode == "🧠 All Fields (Smart)":
            st.info("🧠 Smart mode will auto-populate: Name, Brand, Model, Type, Value, and Description with confidence scores")
        elif generation_mode == "📸 Photo Analysis":
            st.info("📸 Photo mode analyzes item images to automatically extract all fields using AI vision")
        else:
            st.info("📝 Simple mode generates description only")
    
    # Handle photo analysis mode
    if generation_mode == "📸 Photo Analysis":
        st.markdown("---")
        
        # Photo capture interface
        photo_data = show_photo_capture_interface("ai_photo")
        
        if photo_data:
            # Analyze photo button
            if st.button("🤖 Analyze Photo with AI", type="primary", key="ai_analyze_photo_btn"):
                with st.spinner("📸 Analyzing photo with AI..."):
                    try:
                        # Call photo analysis API endpoint
                        result = safe_api_call(
                            lambda: api_client.analyze_item_image(
                                image_data=photo_data["data"],
                                image_format=f"image/{photo_data['format'].lower()}",
                                context_hints=photo_data.get("context_hints", {})
                            ),
                            "Failed to analyze photo"
                        )
                        
                        if result:
                            st.session_state.ai_enriched_data = result
                            st.session_state.ai_generation_metadata = result.get("metadata", {})
                            st.session_state.ai_photo_data = photo_data
                            st.rerun()
                        else:
                            show_error("Failed to analyze photo. Please try again.")
                            
                    except Exception as e:
                        handle_api_error(e, "analyze photo")
        
        # Clear button for photo mode
        if st.button("🗑️ Clear Photo Analysis", key="ai_clear_photo_btn"):
            for key in ["ai_enriched_data", "ai_generation_metadata", "ai_photo_data"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    else:
        # Generation controls for text-based modes
        col_gen1, col_gen2 = st.columns([1, 3])
        
        with col_gen1:
            if generation_mode == "🧠 All Fields (Smart)":
                generate_button_text = "🚀 Generate All Fields"
            else:
                generate_button_text = "🚀 Generate Description"
                
            if st.button(generate_button_text, type="primary", key="ai_generate_btn"):
                if ai_name:
                    with st.spinner("🤖 Generating content with AI..."):
                        context = {
                            "name": ai_name,
                            "category": ai_category or "General",
                            "item_type": ai_type,
                            "brand": ai_brand,
                            "model": None
                        }
                        
                        try:
                            if generation_mode == "🧠 All Fields (Smart)":
                                # Use the new multi-field enrichment endpoint
                                result = safe_api_call(
                                    lambda: api_client.enrich_item_data(context),
                                    "Failed to generate enriched data"
                                )
                                
                                if result:
                                    st.session_state.ai_enriched_data = result
                                    st.session_state.ai_generation_metadata = result.get("metadata", {})
                                    st.rerun()
                                else:
                                    show_error("Failed to generate enriched data. Please try again.")
                            else:
                                # Use the simple description generation
                                result = safe_api_call(
                                    lambda: api_client.generate_item_description(context),
                                    "Failed to generate description"
                                )
                                
                                if result and result.get("content"):
                                    st.session_state.ai_generated_content = result["content"]
                                    st.session_state.ai_generation_metadata = {
                                        "model": result.get("model", "unknown"),
                                        "tokens": result.get("tokens_used", 0),
                                        "time": result.get("generation_time", 0)
                                    }
                                    st.rerun()
                                else:
                                    show_error("Failed to generate description. Please try again.")
                                    
                        except Exception as e:
                            handle_api_error(e, "generate AI content")
                else:
                    st.warning("Please enter an item name for AI generation")
        
        with col_gen2:
            if st.button("🗑️ Clear Generated Content", key="ai_clear_btn"):
                for key in ["ai_generated_content", "ai_enriched_data", "ai_generation_metadata", "ai_photo_data"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
    
    # Show generated content if available
    generated_fields = {}
    
    # Photo analysis results display
    if "ai_photo_data" in st.session_state and "ai_enriched_data" in st.session_state:
        photo_data = st.session_state.ai_photo_data
        enriched_data = st.session_state.ai_enriched_data
        
        st.markdown("---")
        display_photo_analysis_results(enriched_data, photo_data)
        st.markdown("---")
    
    # Multi-field enrichment display
    if "ai_enriched_data" in st.session_state:
        enriched_data = st.session_state.ai_enriched_data
        
        # Different title based on source
        if "ai_photo_data" in st.session_state:
            st.markdown("#### 📸 Edit AI Photo Analysis Results")
        else:
            st.markdown("#### 🧠 AI Generated Fields")
        
        # Show metadata
        if "ai_generation_metadata" in st.session_state:
            metadata = st.session_state.ai_generation_metadata
            col_meta1, col_meta2, col_meta3 = st.columns(3)
            with col_meta1:
                st.metric("Model", metadata.get("model", "Unknown"))
            with col_meta2:
                st.metric("Tokens", metadata.get("tokens_used", 0))
            with col_meta3:
                st.metric("Time", f"{metadata.get('generation_time', 0):.1f}s")
        
        # Display enriched fields with confidence scores and editing
        confidence_scores = enriched_data.get("confidence_scores", {})
        
        col_field1, col_field2 = st.columns(2)
        
        with col_field1:
            st.markdown("**📝 Content Fields**")
            
            # Refined name
            refined_name = enriched_data.get("refined_name", "")
            if refined_name:
                confidence = confidence_scores.get("refined_name", 0.0)
                st.markdown(f"**Item Name** (confidence: {confidence:.1%})")
                generated_fields["refined_name"] = st.text_input(
                    "Refined Name:",
                    value=refined_name,
                    help="AI-improved item name",
                    key="ai_refined_name_editor"
                )
            
            # Brand
            brand = enriched_data.get("brand", "")
            if brand:
                confidence = confidence_scores.get("brand", 0.0)
                st.markdown(f"**Brand** (confidence: {confidence:.1%})")
                generated_fields["brand"] = st.text_input(
                    "Brand:",
                    value=brand,
                    help="AI-identified brand",
                    key="ai_brand_editor"
                )
            
            # Model
            model = enriched_data.get("model", "")
            if model:
                confidence = confidence_scores.get("model", 0.0)
                st.markdown(f"**Model** (confidence: {confidence:.1%})")
                generated_fields["model"] = st.text_input(
                    "Model:",
                    value=model,
                    help="AI-identified model",
                    key="ai_model_editor"
                )
        
        with col_field2:
            st.markdown("**🏷️ Classification & Value**")
            
            # Item type
            item_type = enriched_data.get("item_type", "")
            if item_type:
                confidence = confidence_scores.get("item_type", 0.0)
                st.markdown(f"**Item Type** (confidence: {confidence:.1%})")
                item_type_options = get_item_type_options()
                try:
                    default_index = item_type_options.index(item_type) if item_type in item_type_options else 0
                except:
                    default_index = 0
                generated_fields["item_type"] = st.selectbox(
                    "Item Type:",
                    item_type_options,
                    index=default_index,
                    help="AI-classified item type",
                    key="ai_item_type_editor"
                )
            
            # Estimated value
            estimated_value = enriched_data.get("estimated_value")
            if estimated_value is not None:
                confidence = confidence_scores.get("estimated_value", 0.0)
                st.markdown(f"**Estimated Value** (confidence: {confidence:.1%})")
                generated_fields["estimated_value"] = st.number_input(
                    "Estimated Value ($):",
                    value=float(estimated_value),
                    min_value=0.0,
                    format="%.2f",
                    help="AI-estimated current market value",
                    key="ai_estimated_value_editor"
                )
        
        # Description (full width)
        description = enriched_data.get("description", "")
        if description:
            confidence = confidence_scores.get("description", 0.0)
            st.markdown(f"**📄 Description** (confidence: {confidence:.1%})")
            generated_fields["description"] = st.text_area(
                "Description:",
                value=description,
                height=120,
                help="AI-generated detailed description",
                key="ai_description_editor"
            )
        
        st.success("✅ Multi-field content generated! Values will be used in the form below.")
    
    # Simple description display (backward compatibility)
    elif "ai_generated_content" in st.session_state:
        st.markdown("#### Generated Description")
        
        # Show metadata
        if "ai_generation_metadata" in st.session_state:
            metadata = st.session_state.ai_generation_metadata
            col_meta1, col_meta2, col_meta3 = st.columns(3)
            with col_meta1:
                st.metric("Model", metadata.get("model", "Unknown"))
            with col_meta2:
                st.metric("Tokens", metadata.get("tokens", 0))
            with col_meta3:
                st.metric("Time", f"{metadata.get('time', 0):.1f}s")
        
        # Editable content
        generated_fields["description"] = st.text_area(
            "Generated Description (you can edit):",
            value=st.session_state.ai_generated_content,
            height=150,
            key="ai_content_editor"
        )
        
        st.success("✅ Description generated! This will be used in the form below.")
    
    return generated_fields


def create_item_dataframe(items: List[Dict], show_inventory: bool = True) -> pd.DataFrame:
    """Create a pandas DataFrame from items data with inventory information."""
    if not items:
        return pd.DataFrame()
    
    # Extract basic item data
    df_data = []
    for item in items:
        row = {
            "ID": item.get("id"),
            "Name": item.get("name", ""),
            "Type": item.get("item_type", "").replace("_", " ").title(),
            "Brand": item.get("brand", ""),
            "Model": item.get("model", ""),
            "Condition": item.get("condition", "").replace("_", " ").title(),
            "Status": item.get("status", "").replace("_", " ").title(),
            "Current Value": safe_currency_format(item.get('current_value')) if item.get('current_value') else "",
            "Purchase Price": safe_currency_format(item.get('purchase_price')) if item.get('purchase_price') else "",
            "Purchase Date": item.get("purchase_date", "").split("T")[0] if item.get("purchase_date") else "",
            "Category": item.get("category", {}).get("name", "") if item.get("category") else "",
            "Tags": item.get("tags", ""),
            "Serial Number": item.get("serial_number", ""),
            "Description": (item.get("description") or "")[:100] + "..." if len(item.get("description") or "") > 100 else (item.get("description") or ""),
        }
        
        # Add inventory information if requested
        if show_inventory:
            inventory_entries = item.get("inventory_entries", [])
            if inventory_entries:
                locations = []
                total_quantity = 0
                for entry in inventory_entries:
                    if entry.get("location"):
                        locations.append(f"{entry['location']['name']} ({entry.get('quantity', 1)})")
                        total_quantity += entry.get('quantity', 1)
                
                row["Locations"] = ", ".join(locations)
                row["Total Quantity"] = total_quantity
            else:
                row["Locations"] = "Not in inventory"
                row["Total Quantity"] = 0
        
        df_data.append(row)
    
    df = pd.DataFrame(df_data)
    
    # Ensure consistent column order
    base_columns = ["ID", "Name", "Type", "Brand", "Model", "Condition", "Status"]
    if show_inventory:
        base_columns.extend(["Locations", "Total Quantity"])
    base_columns.extend(["Current Value", "Purchase Price", "Purchase Date", "Category", "Tags", "Serial Number", "Description"])
    
    # Reorder columns
    existing_columns = [col for col in base_columns if col in df.columns]
    df = df[existing_columns]
    
    return df


def get_item_type_options() -> List[str]:
    """Get available item type options."""
    return [
        "electronics", "furniture", "clothing", "books", "documents", 
        "tools", "kitchen", "decor", "collectibles", "hobby", 
        "office", "personal", "seasonal", "storage", "other"
    ]


def get_condition_options() -> List[str]:
    """Get available condition options."""
    return [
        "excellent", "very_good", "good", "fair", "poor", "for_repair", "not_working"
    ]


def get_status_options() -> List[str]:
    """Get available status options."""
    return [
        "available", "in_use", "reserved", "loaned", "missing", "disposed", "sold"
    ]


def safe_api_call_with_success(func, success_message: str, error_message: str):
    """Safely execute an API call with success message handling."""
    try:
        result = func()
        if result:
            show_success(success_message)
        return result
    except Exception as e:
        handle_api_error(e, error_message)
        return None


def create_item_form(api_client: APIClient, create_with_location: bool = True) -> bool:
    """
    Create comprehensive item creation form with optional AI generation.
    
    Args:
        api_client: API client instance
        create_with_location: If True, automatically assign item to location
        
    Returns:
        bool: True if item was created successfully
    """
    
    # Load required data
    with st.spinner("Loading locations and categories..."):
        locations = safe_api_call(
            lambda: api_client.get_locations(skip=0, limit=1000),
            "Failed to load locations"
        ) or []
        
        categories_data = safe_api_call(
            lambda: api_client.get_categories(page=1, per_page=100, include_inactive=False),
            "Failed to load categories"
        )
        categories = categories_data.get('categories', []) if categories_data else []
    
    # Check if locations are available for location-based creation
    if create_with_location and not locations:
        st.error("⚠️ No locations available. Please create at least one location before adding items with location assignment.")
        if st.button("Go to Location Management", key="goto_locations"):
            st.rerun()
        return False
    
    # Phase 1: AI Generation Options (outside form)
    st.markdown("### ➕ Create New Item")
    
    # Creation workflow options
    col_option1, col_option2 = st.columns(2)
    
    with col_option1:
        enable_location_assignment = st.checkbox(
            "📍 Assign to Location", 
            value=create_with_location,
            help="Check to automatically assign this item to a location and track inventory",
            key="enable_location_assignment"
        )
    
    with col_option2:
        # Use session state to persist AI generation mode across reruns
        if "ai_generation_enabled" not in st.session_state:
            st.session_state.ai_generation_enabled = False
            
        enable_ai_generation = st.checkbox(
            "🤖 Enable AI Description",
            value=st.session_state.ai_generation_enabled,
            help="Generate description using AI before filling out the form",
            key="enable_ai_generation"
        )
        
        # Update session state when checkbox changes
        if enable_ai_generation != st.session_state.ai_generation_enabled:
            st.session_state.ai_generation_enabled = enable_ai_generation
    
    # AI Generation Interface (outside form)
    ai_generated_fields = {}
    if st.session_state.ai_generation_enabled:
        ai_generated_fields = show_ai_generation_interface(api_client)
    
    # Phase 2: Item Creation Form (form-only elements)
    with st.form("create_item_form", clear_on_submit=True):
        # Main form sections
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📋 Basic Information**")
            
            # Use AI-generated refined name if available, otherwise empty
            default_name = ai_generated_fields.get("refined_name", "")
            name = st.text_input("Item Name*", value=default_name, help="Enter the item name")
            
            # Item type selection (use AI-generated if available)
            item_types = get_item_type_options()
            default_type_index = 0
            if ai_generated_fields.get("item_type"):
                try:
                    default_type_index = item_types.index(ai_generated_fields["item_type"])
                except ValueError:
                    default_type_index = 0
            item_type = st.selectbox("Item Type*", item_types, index=default_type_index, help="Select the primary type")
            
            # Description field (with AI-generated content if available)
            st.markdown("**Description**")
            default_description = ai_generated_fields.get("description", "")
            description = st.text_area(
                "Description", 
                value=default_description,
                help="Optional description of the item",
                key="item_description_field"
            )
            
            if enable_ai_generation and not ai_generated_fields:
                st.caption("💡 Use the AI generation interface above to auto-populate fields")
            
            # Condition and status
            conditions = get_condition_options()
            condition = st.selectbox("Condition", conditions, index=2, help="Current condition")  # Default to 'good'
            
            statuses = get_status_options()
            status = st.selectbox("Status", statuses, help="Current status")
            
            # Location selection (conditional)
            selected_location_id = None
            quantity = 1
            
            if enable_location_assignment and locations:
                st.markdown("**📍 Location & Inventory**")
                location_options = {loc['id']: f"{loc['name']} ({loc.get('location_type', '').title()})" for loc in locations}
                selected_location_id = st.selectbox(
                    "Location*",
                    options=list(location_options.keys()),
                    format_func=lambda x: location_options[x],
                    help="Required: Select where this item will be stored"
                )
                
                # Quantity input
                quantity = st.number_input(
                    "Quantity",
                    min_value=1,
                    value=1,
                    help="Number of items to add to this location"
                )
            
            # Category selection
            st.markdown("**🏷️ Organization**")
            selected_category_id = None
            if categories:
                category_options = {None: "No Category"}
                category_options.update({cat['id']: cat['name'] for cat in categories if cat.get('is_active', True)})
                selected_category_id = st.selectbox(
                    "Category",
                    options=list(category_options.keys()),
                    format_func=lambda x: category_options[x],
                    help="Optional category for organization"
                )
        
        with col2:
            st.markdown("**🏭 Product Information**")
            
            # Use AI-generated values if available
            default_brand = ai_generated_fields.get("brand", "")
            brand = st.text_input("Brand", value=default_brand, help="Manufacturer or brand name")
            
            default_model = ai_generated_fields.get("model", "")
            model = st.text_input("Model", value=default_model, help="Model number or name")
            
            serial_number = st.text_input("Serial Number", help="Serial number if available")
            barcode = st.text_input("Barcode/UPC", help="Barcode or UPC if available")
            
            st.markdown("**💰 Value & Dates**")
            purchase_price = st.number_input("Purchase Price ($)", min_value=0.0, format="%.2f", help="Original purchase price")
            
            # Use AI-generated estimated value if available
            default_current_value = ai_generated_fields.get("estimated_value", 0.0)
            current_value = st.number_input("Current Value ($)", value=default_current_value, min_value=0.0, format="%.2f", help="Current estimated value")
            
            purchase_date = st.date_input("Purchase Date", value=None, help="When was this item purchased?")
            warranty_expiry = st.date_input("Warranty Expiry", value=None, help="When does the warranty expire?")
        
        # Additional details in expander
        with st.expander("📐 Physical Properties & Additional Details"):
            col3, col4 = st.columns(2)
            
            with col3:
                st.markdown("**Physical Properties**")
                weight = st.number_input("Weight (kg)", min_value=0.0, format="%.3f", help="Weight of the item")
                color = st.text_input("Color", help="Primary color")
                dimensions = st.text_input("Dimensions", help="e.g., '10x20x5 cm'")
            
            with col4:
                st.markdown("**Additional Information**")
                tags = st.text_input("Tags", help="Comma-separated tags (e.g., 'important, fragile')")
                notes = st.text_area("Notes", help="Additional notes or observations")
        
        # Submit button
        col_submit1, col_submit2, col_submit3 = st.columns([2, 1, 2])
        with col_submit2:
            submitted = st.form_submit_button("✅ Create Item", use_container_width=True)
        
        # Form processing
        if submitted:
            # Validation
            if not safe_string_check(name):
                show_error("Item name is required.")
                return False
            
            if enable_location_assignment and not selected_location_id:
                show_error("Location is required when creating with location assignment.")
                return False
            
            # Prepare item data
            item_data = {
                "name": safe_strip(name),
                "description": safe_string_or_none(description),
                "item_type": item_type,
                "condition": condition,
                "status": status,
                "brand": safe_string_or_none(brand),
                "model": safe_string_or_none(model),
                "serial_number": safe_string_or_none(serial_number),
                "barcode": safe_string_or_none(barcode),
                "purchase_price": purchase_price if purchase_price > 0 else None,
                "current_value": current_value if current_value > 0 else None,
                "purchase_date": purchase_date.isoformat() if purchase_date else None,
                "warranty_expiry": warranty_expiry.isoformat() if warranty_expiry else None,
                "weight": weight if weight > 0 else None,
                "color": safe_string_or_none(color),
                "dimensions": safe_string_or_none(dimensions),
                "tags": safe_string_or_none(tags),
                "notes": safe_string_or_none(notes),
                "category_id": selected_category_id
            }
            
            # Add location data if creating with location
            if enable_location_assignment and selected_location_id:
                item_data.update({
                    "location_id": selected_location_id,
                    "quantity": quantity
                })
            
            # Create item via API
            try:
                if enable_location_assignment and selected_location_id:
                    # Create item with location assignment
                    result = api_client.create_item_with_location(item_data)
                    success_message = f"✅ Item '{name}' created and assigned to location successfully!"
                else:
                    # Create item only
                    result = api_client.create_item(item_data)
                    success_message = f"✅ Item '{name}' created successfully!"
                
                if result:
                    show_success(success_message)
                    
                    # Clean up AI generation session state
                    ai_keys_to_clear = [
                        "ai_generated_content", "ai_enriched_data", "ai_generation_metadata", 
                        "ai_photo_data", "ai_generation_enabled"
                    ]
                    for key in ai_keys_to_clear:
                        if key in st.session_state:
                            del st.session_state[key]
                    
                    st.balloons()
                    return True
                else:
                    show_error("Failed to create item. Please try again.")
                    return False
                    
            except APIError as e:
                handle_api_error(e, "Failed to create item")
                return False
            except Exception as e:
                logger.error(f"Unexpected error creating item: {e}")
                show_error(f"An unexpected error occurred: {str(e)}")
                return False
    
    return False


def display_item_card(item: Dict[str, Any], show_actions: bool = True) -> None:
    """
    Display an item card with key information.
    
    Args:
        item: Item data dictionary
        show_actions: Whether to show action buttons
    """
    with st.container():
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            st.markdown(f"**{item.get('name', 'Unknown Item')}**")
            if item.get('description'):
                st.caption(item['description'])
            
            # Item details
            item_type = item.get('item_type', '').replace('_', ' ').title()
            condition = item.get('condition', '').replace('_', ' ').title()
            st.text(f"Type: {item_type} | Condition: {condition}")
            
        with col2:
            # Value information
            if item.get('current_value'):
                st.metric("Current Value", safe_currency_format(item['current_value']))
            elif item.get('purchase_price'):
                st.metric("Purchase Price", safe_currency_format(item['purchase_price']))
            
            # Category
            if item.get('category_id'):
                st.text(f"📂 Category: {item.get('category_name', 'Unknown')}")
        
        with col3:
            if show_actions:
                if st.button("👁️ View", key=f"item_view_{item.get('id')}"):
                    st.session_state[f"show_item_{item.get('id')}"] = True
                if st.button("✏️ Edit", key=f"item_edit_{item.get('id')}"):
                    st.session_state[f"edit_item_{item.get('id')}"] = True
                if st.button("🗑️ Delete", key=f"item_delete_{item.get('id')}", type="secondary"):
                    st.session_state[f"confirm_delete_item_{item.get('id')}"] = True


def show_item_delete_confirmation(item: Dict[str, Any], api_client: APIClient) -> None:
    """
    Show delete confirmation dialog for an item.
    
    Args:
        item: Item data dictionary
        api_client: API client instance
    """
    item_id = item.get('id')
    item_name = item.get('name', 'Unknown Item')
    
    st.warning(f"⚠️ Are you sure you want to delete '{item_name}'?")
    
    # Show item details for confirmation
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Type:** {item.get('item_type', '').replace('_', ' ').title()}")
        st.write(f"**Condition:** {item.get('condition', '').replace('_', ' ').title()}")
    with col2:
        if item.get('current_value'):
            st.write(f"**Value:** {safe_currency_format(item['current_value'])}")
        elif item.get('purchase_price'):
            st.write(f"**Purchase Price:** {safe_currency_format(item['purchase_price'])}")
    
    # Delete options
    st.markdown("**Delete Options:**")
    permanent_delete = st.checkbox(
        "Permanent Delete (cannot be undone)", 
        key=f"permanent_delete_{item_id}",
        help="Check this to permanently delete the item. Otherwise, it will be soft deleted and can be restored."
    )
    
    if permanent_delete:
        st.error("⚠️ **Warning**: This will permanently remove the item and cannot be undone!")
    else:
        st.info("ℹ️ Item will be soft deleted and can be restored later if needed.")
    
    # Action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("✅ Yes, Delete", key=f"confirm_delete_action_{item_id}", type="primary"):
            delete_item_action(item_id, item_name, permanent_delete, api_client)
    
    with col2:
        if st.button("❌ Cancel", key=f"cancel_delete_{item_id}"):
            # Clear the confirmation state
            if f"confirm_delete_item_{item_id}" in st.session_state:
                del st.session_state[f"confirm_delete_item_{item_id}"]
            st.rerun()
    
    with col3:
        st.caption("Choose wisely!")


def delete_item_action(item_id: int, item_name: str, permanent: bool, api_client: APIClient) -> None:
    """
    Perform the actual item deletion.
    
    Args:
        item_id: ID of the item to delete
        item_name: Name of the item for display
        permanent: Whether to permanently delete the item
        api_client: API client instance
    """
    try:
        with st.spinner(f"Deleting {item_name}..."):
            # Use the consistent delete_item method for both soft and permanent delete
            success = safe_api_call(
                lambda: api_client.delete_item(item_id, permanent=permanent),
                f"Failed to {'permanently ' if permanent else ''}delete item: {item_name}"
            )
            
            if success:
                delete_type = "permanently deleted" if permanent else "deleted"
                show_success(f"✅ Item '{item_name}' has been {delete_type} successfully!")
                
                # Clear any session state related to this item
                cleanup_item_session_state(item_id)
                
                # Force a rerun to refresh the item list
                st.rerun()
            else:
                show_error(f"Failed to delete item '{item_name}'. Please try again.")
                
    except Exception as e:
        handle_api_error(e, f"delete item '{item_name}'")


def cleanup_item_session_state(item_id: int) -> None:
    """
    Clean up session state variables related to a deleted item.
    
    Args:
        item_id: ID of the deleted item
    """
    # List of session state keys that might exist for this item
    keys_to_clean = [
        f"show_item_{item_id}",
        f"edit_item_{item_id}",
        f"confirm_delete_item_{item_id}",
        f"permanent_delete_{item_id}",
        f"confirm_delete_action_{item_id}",
        f"cancel_delete_{item_id}",
        f"item_view_{item_id}",
        f"item_edit_{item_id}",
        f"item_delete_{item_id}"
    ]
    
    # Remove any existing keys
    for key in keys_to_clean:
        if key in st.session_state:
            del st.session_state[key]


def manage_items_section(api_client: APIClient) -> None:
    """
    Complete item management section with creation, listing, and actions.
    
    Args:
        api_client: API client instance
    """
    
    st.markdown("## 📦 Item Management")
    
    # Tabs for different item management functions
    tab1, tab2 = st.tabs(["➕ Create Item", "📋 Browse Items"])
    
    with tab1:
        # Item creation form
        create_item_form(api_client, create_with_location=True)
    
    with tab2:
        # Item listing and management
        st.markdown("### 📋 All Items")
        
        # Load and display items
        with st.spinner("Loading items..."):
            items_data = safe_api_call(
                lambda: api_client.get_items(skip=0, limit=50),
                "Failed to load items"
            )
        
        if items_data:
            # Handle both direct list and wrapped response formats
            if isinstance(items_data, dict) and 'items' in items_data:
                items = items_data['items']
            elif isinstance(items_data, list):
                items = items_data
            else:
                items = []
            
            # Search and filter
            search_term = st.text_input("🔍 Search items", placeholder="Search by name, brand, or description...")
            
            # Filter items if search term provided
            if search_term:
                filtered_items = [
                    item for item in items
                    if search_term.lower() in item.get('name', '').lower()
                    or search_term.lower() in item.get('brand', '').lower()
                    or search_term.lower() in item.get('description', '').lower()
                ]
            else:
                filtered_items = items
            
            # Display items
            if filtered_items:
                st.markdown(f"**{len(filtered_items)} items found**")
                
                for item in filtered_items:
                    # Check if delete confirmation is requested for this item
                    item_id = item.get('id')
                    if st.session_state.get(f"confirm_delete_item_{item_id}", False):
                        # Show delete confirmation dialog
                        show_item_delete_confirmation(item, api_client)
                        st.divider()
                    else:
                        # Show normal item card
                        display_item_card(item, show_actions=True)
                        st.divider()
            else:
                st.info("No items found matching your search criteria.")
        else:
            st.info("No items found. Create your first item using the form above!")


def browse_items_section(api_client: APIClient) -> None:
    """
    Browse-only items section for the Items page.
    
    Args:
        api_client: API client instance
    """
    
    st.markdown("## 📦 Browse Items")
    st.info("💡 **Note**: To create new items, visit the **Manage** page using the sidebar navigation.")
    
    # Add prominent button to navigate to manage page
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("➕ Create New Item", use_container_width=True, type="primary"):
            st.switch_page("pages/03_⚙️_Manage.py")
    
    st.divider()
    
    # Load and display items for browsing
    with st.spinner("Loading items..."):
        items = safe_api_call(
            lambda: api_client.get_items(skip=0, limit=100),
            "Failed to load items"
        )
    
    if items:
        # Handle both direct list and wrapped response formats
        if isinstance(items, dict) and 'items' in items:
            items_list = items['items']
        elif isinstance(items, list):
            items_list = items
        else:
            items_list = []
        
        # Enhanced search and filtering
        col1, col2 = st.columns([2, 1])
        with col1:
            search_term = st.text_input("🔍 Search items", placeholder="Search by name, brand, description...")
        with col2:
            item_type_filter = st.selectbox("Filter by Type", ["All"] + get_item_type_options())
        
        # Apply filters
        filtered_items = items_list
        
        if search_term:
            filtered_items = [
                item for item in filtered_items
                if search_term.lower() in (item.get('name') or '').lower()
                or search_term.lower() in (item.get('brand') or '').lower()
                or search_term.lower() in (item.get('description') or '').lower()
            ]
        
        if item_type_filter != "All":
            filtered_items = [
                item for item in filtered_items
                if item.get('item_type') == item_type_filter
            ]
        
        # Display results
        if filtered_items:
            st.markdown(f"**{len(filtered_items)} items found**")
            
            # Display view toggle
            col1, col2 = st.columns([3, 1])
            with col2:
                view_mode = st.selectbox("View", ["Table", "Details"], key="items_view_mode")
            
            if view_mode == "Table":
                # Create and display table view
                df = create_item_dataframe(filtered_items, show_inventory=True)
                if not df.empty:
                    st.dataframe(
                        df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "ID": st.column_config.NumberColumn("ID", width="small"),
                            "Name": st.column_config.TextColumn("Name", width="medium"),
                            "Type": st.column_config.TextColumn("Type", width="small"),
                            "Brand": st.column_config.TextColumn("Brand", width="small"),
                            "Model": st.column_config.TextColumn("Model", width="small"),
                            "Condition": st.column_config.TextColumn("Condition", width="small"),
                            "Status": st.column_config.TextColumn("Status", width="small"),
                            "Current Value": st.column_config.TextColumn("Current Value", width="small"),
                            "Purchase Price": st.column_config.TextColumn("Purchase Price", width="small"),
                            "Locations": st.column_config.TextColumn("Locations", width="medium"),
                            "Total Quantity": st.column_config.NumberColumn("Total Qty", width="small"),
                            "Description": st.column_config.TextColumn("Description", width="large")
                        }
                    )
                else:
                    st.info("No items to display in table format.")
            else:
                # Display items in detailed expander format
                for item in filtered_items:
                    with st.expander(f"📦 {item.get('name', 'Unknown Item')}", expanded=False):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Type:** {item.get('item_type', '').replace('_', ' ').title()}")
                            st.write(f"**Condition:** {item.get('condition', '').replace('_', ' ').title()}")
                            st.write(f"**Status:** {item.get('status', '').replace('_', ' ').title()}")
                            if item.get('brand'):
                                st.write(f"**Brand:** {item['brand']}")
                            if item.get('model'):
                                st.write(f"**Model:** {item['model']}")
                        
                        with col2:
                            if item.get('current_value'):
                                st.metric("Current Value", safe_currency_format(item['current_value']))
                            elif item.get('purchase_price'):
                                st.metric("Purchase Price", safe_currency_format(item['purchase_price']))
                            
                            if item.get('description'):
                                st.write(f"**Description:** {item['description']}")
        else:
            st.info("No items found matching your criteria.")
    else:
        st.info("No items found. Create your first item on the **Manage** page!")