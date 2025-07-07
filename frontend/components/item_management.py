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

logger = logging.getLogger(__name__)


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
    Create comprehensive item creation form.
    
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
    
    # Item creation form
    with st.form("create_item_form", clear_on_submit=True):
        st.markdown("### ➕ Create New Item")
        
        # Option to create with or without location
        if locations:
            create_with_location = st.checkbox(
                "📍 Assign to Location", 
                value=create_with_location,
                help="Check to automatically assign this item to a location and track inventory"
            )
        
        # Main form sections
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📋 Basic Information**")
            name = st.text_input("Item Name*", help="Enter the item name")
            description = st.text_area("Description", help="Optional description of the item")
            
            # Item type selection
            item_types = get_item_type_options()
            item_type = st.selectbox("Item Type*", item_types, help="Select the primary type")
            
            # Condition and status
            conditions = get_condition_options()
            condition = st.selectbox("Condition", conditions, index=2, help="Current condition")  # Default to 'good'
            
            statuses = get_status_options()
            status = st.selectbox("Status", statuses, help="Current status")
            
            # Location selection (conditional)
            selected_location_id = None
            quantity = 1
            
            if create_with_location and locations:
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
            brand = st.text_input("Brand", help="Manufacturer or brand name")
            model = st.text_input("Model", help="Model number or name")
            serial_number = st.text_input("Serial Number", help="Serial number if available")
            barcode = st.text_input("Barcode/UPC", help="Barcode or UPC if available")
            
            st.markdown("**💰 Value & Dates**")
            purchase_price = st.number_input("Purchase Price ($)", min_value=0.0, format="%.2f", help="Original purchase price")
            current_value = st.number_input("Current Value ($)", min_value=0.0, format="%.2f", help="Current estimated value")
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
            
            if create_with_location and not selected_location_id:
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
            if create_with_location and selected_location_id:
                item_data.update({
                    "location_id": selected_location_id,
                    "quantity": quantity
                })
            
            # Create item via API
            try:
                if create_with_location and selected_location_id:
                    # Create item with location assignment
                    result = api_client.create_item_with_location(item_data)
                    success_message = f"✅ Item '{name}' created and assigned to location successfully!"
                else:
                    # Create item only
                    result = api_client.create_item(item_data)
                    success_message = f"✅ Item '{name}' created successfully!"
                
                if result:
                    show_success(success_message)
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
                if st.button("👁️ View", key=f"view_{item.get('id')}"):
                    st.session_state[f"show_item_{item.get('id')}"] = True
                if st.button("✏️ Edit", key=f"edit_{item.get('id')}"):
                    st.session_state[f"edit_item_{item.get('id')}"] = True


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
        
        if items_data and items_data.get('items'):
            items = items_data['items']
            
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
        items_data = safe_api_call(
            lambda: api_client.get_items(skip=0, limit=100),
            "Failed to load items"
        )
    
    if items_data and items_data.get('items'):
        items = items_data['items']
        
        # Enhanced search and filtering
        col1, col2 = st.columns([2, 1])
        with col1:
            search_term = st.text_input("🔍 Search items", placeholder="Search by name, brand, description...")
        with col2:
            item_type_filter = st.selectbox("Filter by Type", ["All"] + get_item_type_options())
        
        # Apply filters
        filtered_items = items
        
        if search_term:
            filtered_items = [
                item for item in filtered_items
                if search_term.lower() in item.get('name', '').lower()
                or search_term.lower() in item.get('brand', '').lower()
                or search_term.lower() in item.get('description', '').lower()
            ]
        
        if item_type_filter != "All":
            filtered_items = [
                item for item in filtered_items
                if item.get('item_type') == item_type_filter
            ]
        
        # Display results
        if filtered_items:
            st.markdown(f"**{len(filtered_items)} items found**")
            
            # Display items in a more compact format for browsing
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