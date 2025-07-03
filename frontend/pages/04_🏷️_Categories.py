"""
Categories page for the Home Inventory System.

Manage, organize, and browse all inventory categories.
"""

import streamlit as st
import pandas as pd
import logging
import re
from typing import List, Dict, Any, Optional

from utils.api_client import APIClient, APIError
from components.auth import is_authenticated, show_logout_button
from utils.helpers import (
    safe_api_call, show_error, show_success, show_warning,
    handle_api_error, SessionManager, validate_hex_color,
    safe_strip, safe_string_check, safe_string_or_none
)
from components.keyboard_shortcuts import (
    enable_keyboard_shortcuts, show_keyboard_shortcuts_help,
    create_enhanced_search_box, create_quick_filter_buttons,
    create_pagination_controls, create_bulk_selection_interface,
    create_action_buttons_row
)

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Categories - Home Inventory System",
    page_icon="🏷️",
    layout="wide"
)

def safe_api_call_with_success(func, success_message: str, error_message: str):
    """Safely execute an API call with success message handling."""
    try:
        result = func()
        if result is not None:
            show_success(success_message)
        return result
    except Exception as e:
        logger.error(f"{error_message}: {e}")
        show_error(error_message, str(e))
        return None

def create_search_filters() -> Dict[str, Any]:
    """Create enhanced search and filter controls."""
    st.sidebar.subheader("🔍 Advanced Search & Filters")
    
    # Enhanced search box with clear functionality
    search_text = create_enhanced_search_box(
        placeholder="Enter category name or description...",
        key="category_search",
        help_text="Search in category names and descriptions"
    )
    
    # Advanced search options
    with st.sidebar.expander("🔧 Search Options"):
        case_sensitive = st.checkbox(
            "Case sensitive search",
            help="Enable case-sensitive search"
        )
        
        search_mode = st.selectbox(
            "Search mode",
            ["Contains", "Starts with", "Ends with", "Exact match"],
            help="How to match the search text"
        )
    
    # Category status filter
    st.sidebar.subheader("📊 Status Filters")
    status_filter_options = {
        'active': '✅ Active Only',
        'inactive': '❌ Inactive Only', 
        'all': '🔍 All Categories'
    }
    
    current_status_filter = st.session_state.get('status_filter', 'active')
    selected_status_key = create_quick_filter_buttons(
        current_status_filter,
        status_filter_options,
        "status_filter"
    )
    
    # Store selected filter
    st.session_state['status_filter'] = selected_status_key
    include_inactive = selected_status_key in ['inactive', 'all']
    
    # Color filters
    st.sidebar.subheader("🎨 Color Filters")
    color_filter = st.selectbox(
        "Filter by color",
        ["All colors", "Has color", "No color"],
        help="Filter categories by color presence"
    )
    
    # Sort options
    st.sidebar.subheader("📋 Sort Options")
    sort_by = st.selectbox(
        "Sort by",
        ["Name (A-Z)", "Name (Z-A)", "Created (Newest)", "Created (Oldest)", "Updated (Recent)"],
        help="Choose how to sort the categories"
    )
    
    return {
        "search_text": search_text,
        "case_sensitive": case_sensitive,
        "search_mode": search_mode,
        "include_inactive": include_inactive,
        "color_filter": color_filter,
        "sort_by": sort_by
    }

def create_category_form(category: Optional[dict] = None, mode: str = "create") -> Dict[str, Any]:
    """Create category creation/edit form."""
    form_title = "✏️ Edit Category" if mode == "edit" else "➕ Create New Category"
    
    with st.form(f"category_form_{mode}"):
        st.subheader(form_title)
        
        # Category name (required)
        name = st.text_input(
            "Category Name *",
            value=category.get("name", "") if category else "",
            placeholder="e.g., Electronics, Books, Tools",
            help="Enter a unique name for this category"
        )
        
        # Description (optional)
        description = st.text_area(
            "Description",
            value=category.get("description", "") if category else "",
            placeholder="Describe what types of items belong in this category...",
            help="Optional description to clarify the category's purpose",
            height=100
        )
        
        # Color picker (optional)
        col1, col2 = st.columns([2, 1])
        
        with col1:
            color = st.text_input(
                "Color (Hex Code)",
                value=category.get("color", "") if category else "",
                placeholder="#007BFF",
                help="Optional color in hex format (e.g., #007BFF)",
                max_chars=7
            )
        
        with col2:
            if color and validate_hex_color(color):
                st.color_picker("Color Preview", value=color, disabled=True)
            else:
                st.color_picker("Color Preview", value="#000000", disabled=True)
        
        # Form validation and submission
        submitted = st.form_submit_button(
            "Update Category" if mode == "edit" else "Create Category",
            type="primary"
        )
        
        if submitted:
            # Validation
            errors = []
            
            stripped_name = safe_strip(name)
            if not stripped_name:
                errors.append("Category name is required")
            
            if color and not validate_hex_color(color):
                errors.append("Color must be in hex format (e.g., #007BFF)")
            
            if errors:
                for error in errors:
                    st.error(error)
                return {}
            
            # Return form data
            return {
                "name": stripped_name,
                "description": safe_string_or_none(description),
                "color": color.upper() if color else None
            }
    
    return {}

def display_category_statistics(stats: dict):
    """Display category statistics dashboard."""
    st.subheader("📊 Category Statistics")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Total Categories",
            stats.get("total_categories", 0),
            help="Number of active categories"
        )
    
    with col2:
        st.metric(
            "Inactive Categories", 
            stats.get("inactive_categories", 0),
            help="Number of inactive categories"
        )
    
    with col3:
        most_used_color = stats.get("most_used_color")
        if most_used_color:
            st.metric(
                "Most Used Color",
                most_used_color,
                help="Most commonly used category color"
            )
        else:
            st.metric("Most Used Color", "None", help="No colors in use")

def display_category_card(category: dict, api_client: APIClient):
    """Display a single category card with actions."""
    with st.container():
        # Create card layout
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            # Category name with color indicator
            if category.get("color"):
                st.markdown(
                    f"<div style='display: flex; align-items: center;'>"
                    f"<div style='width: 20px; height: 20px; background-color: {category['color']}; "
                    f"border-radius: 50%; margin-right: 10px; border: 1px solid #ccc;'></div>"
                    f"<strong>{category['name']}</strong></div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(f"**{category['name']}**")
            
            if category.get("description"):
                st.caption(category["description"])
            
            # Status and metadata
            status_color = "🟢" if category.get("is_active", True) else "🔴"
            st.caption(f"{status_color} Status: {'Active' if category.get('is_active', True) else 'Inactive'}")
        
        with col2:
            # Edit button
            if st.button("✏️ Edit", key=f"edit_{category['id']}", help="Edit this category"):
                SessionManager.set(f"edit_category_{category['id']}", True)
                st.rerun()
        
        with col3:
            # Delete/Restore button
            if category.get("is_active", True):
                if st.button("🗑️ Delete", key=f"delete_{category['id']}", help="Delete this category"):
                    if safe_api_call_with_success(
                        lambda: api_client.delete_category(category['id']),
                        "Category deleted successfully",
                        f"Failed to delete category: {category['name']}"
                    ):
                        st.rerun()
            else:
                if st.button("🔄 Restore", key=f"restore_{category['id']}", help="Restore this category"):
                    if safe_api_call_with_success(
                        lambda: api_client.restore_category(category['id']),
                        "Category restored successfully",
                        f"Failed to restore category: {category['name']}"
                    ):
                        st.rerun()
        
        st.divider()

def main():
    """Main categories page function."""
    # Check authentication
    if not is_authenticated():
        st.error('🔒 Please log in to access this page')
        st.stop()
    
    # Enable keyboard shortcuts
    enable_keyboard_shortcuts()
    
    # Show logout button
    show_logout_button()
    
    # Page header
    st.title("🏷️ Categories Management")
    st.markdown("Organize your inventory with custom categories")
    
    # Initialize API client
    api_client = APIClient()
    
    # Test API connection
    if not api_client.health_check():
        st.error("❌ Cannot connect to the API. Please check if the backend server is running.")
        st.stop()
    
    # Load category statistics
    stats = safe_api_call(
        api_client.get_category_stats,
        "Failed to load category statistics"
    )
    
    if stats:
        display_category_statistics(stats)
    
    st.divider()
    
    # Create layout with sidebar filters and main content
    filters = create_search_filters()
    
    # Main content area
    tab1, tab2 = st.tabs(["📋 Browse Categories", "➕ Create Category"])
    
    with tab1:
        st.subheader("📋 Categories List")
        
        # Load categories with filters
        categories_data = safe_api_call(
            lambda: api_client.get_categories(
                page=SessionManager.get('page', 1),
                per_page=20,
                include_inactive=filters["include_inactive"],
                search=filters["search_text"] if filters["search_text"] else None
            ),
            "Failed to load categories"
        )
        
        if categories_data:
            categories = categories_data.get("categories", [])
            total = categories_data.get("total", 0)
            pages = categories_data.get("pages", 1)
            current_page = categories_data.get("page", 1)
            
            if categories:
                # Show category count
                st.info(f"📊 Found {total} categories")
                
                # Display categories
                for category in categories:
                    # Check if editing this category
                    if SessionManager.get(f"edit_category_{category['id']}", False):
                        st.subheader(f"✏️ Editing: {category['name']}")
                        
                        form_data = create_category_form(category, mode="edit")
                        
                        if form_data:
                            # Update category
                            if safe_api_call_with_success(
                                lambda: api_client.update_category(category['id'], form_data),
                                "Category updated successfully",
                                "Failed to update category"
                            ):
                                SessionManager.clear(f"edit_category_{category['id']}")
                                st.rerun()
                        
                        # Cancel edit button
                        if st.button("❌ Cancel Edit", key=f"cancel_edit_{category['id']}"):
                            SessionManager.clear(f"edit_category_{category['id']}")
                            st.rerun()
                        
                        st.divider()
                    else:
                        display_category_card(category, api_client)
                
                # Pagination
                if pages > 1:
                    col1, col2, col3 = st.columns([1, 2, 1])
                    
                    with col1:
                        if current_page > 1:
                            if st.button("⬅️ Previous"):
                                SessionManager.set('page', current_page - 1)
                                st.rerun()
                    
                    with col2:
                        st.markdown(f"<div style='text-align: center'>Page {current_page} of {pages}</div>", 
                                  unsafe_allow_html=True)
                    
                    with col3:
                        if current_page < pages:
                            if st.button("➡️ Next"):
                                SessionManager.set('page', current_page + 1)
                                st.rerun()
            else:
                if filters["search_text"]:
                    st.info("🔍 No categories found matching your search criteria")
                elif filters["include_inactive"]:
                    st.info("📭 No categories found")
                else:
                    st.info("📭 No active categories found")
    
    with tab2:
        st.subheader("➕ Create New Category")
        
        form_data = create_category_form(mode="create")
        
        if form_data:
            # Create category
            if safe_api_call_with_success(
                lambda: api_client.create_category(form_data),
                "Category created successfully",
                "Failed to create category"
            ):
                st.rerun()
    
    # Keyboard shortcuts help
    with st.sidebar:
        st.divider()
        show_keyboard_shortcuts_help()

if __name__ == "__main__":
    main()