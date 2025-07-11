"""
Category management components for the Home Inventory System.

Reusable components for creating, editing, and managing categories.
"""

import streamlit as st
import pandas as pd
import logging
from typing import List, Dict, Any, Optional

from utils.api_client import APIClient, APIError
from utils.helpers import (
    safe_api_call, show_error, show_success, show_warning,
    handle_api_error, SessionManager, validate_hex_color,
    safe_strip, safe_string_check, safe_string_or_none
)
from components.keyboard_shortcuts import (
    create_enhanced_search_box, create_quick_filter_buttons,
    create_pagination_controls, create_bulk_selection_interface,
    create_action_buttons_row
)

logger = logging.getLogger(__name__)


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


def create_category_search_filters() -> Dict[str, Any]:
    """Create enhanced search and filter controls for categories."""
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


def handle_color_selection_outside_form(category: Optional[dict] = None, mode: str = "create") -> str:
    """Handle color selection UI outside of form context."""
    
    # Session state key for storing selected color
    color_key = f"selected_color_{mode}_{category['id'] if category else 'new'}"
    
    # Get current color value
    current_color = category.get("color", "") if category else ""
    
    # Initialize session state if not exists
    if color_key not in st.session_state:
        st.session_state[color_key] = current_color or "#007BFF"
    
    st.markdown("### 🎨 Choose Category Color")
    
    # Color presets for quick selection
    st.markdown("**Quick Color Presets:**")
    preset_colors = {
        "🔵 Electronics": "#007BFF",
        "📚 Books": "#28A745", 
        "🔧 Tools": "#FD7E14",
        "🏠 Home": "#6610F2",
        "🍳 Kitchen": "#DC3545",
        "🚗 Automotive": "#495057",
        "⚽ Sports": "#20C997",
        "💼 Office": "#6C757D"
    }
    
    # Preset color buttons (outside form - these work fine)
    preset_cols = st.columns(4)
    for i, (label, preset_color) in enumerate(preset_colors.items()):
        with preset_cols[i % 4]:
            if st.button(label, key=f"preset_{i}_{mode}"):
                st.session_state[color_key] = preset_color
                st.rerun()
    
    # Control buttons
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🚫 Clear Color", key=f"clear_color_{mode}", help="Remove category color"):
            st.session_state[color_key] = ""
            st.rerun()
    
    with col2:
        if st.button("🔄 Reset to Default", key=f"reset_color_{mode}", help="Reset to default blue"):
            st.session_state[color_key] = "#007BFF"
            st.rerun()
    
    return st.session_state[color_key]


def create_category_form(category: Optional[dict] = None, mode: str = "create") -> Dict[str, Any]:
    """Create category creation/edit form with external color selection."""
    form_title = "✏️ Edit Category" if mode == "edit" else "➕ Create New Category"
    
    # Handle color selection outside form first
    selected_color = handle_color_selection_outside_form(category, mode)
    
    # Show current selection
    if selected_color:
        st.info(f"🎨 **Selected Color:** {selected_color}")
        st.markdown(
            f"<div style='display: flex; align-items: center; margin: 10px 0;'>"
            f"<div style='width: 30px; height: 30px; background-color: {selected_color}; "
            f"border-radius: 50%; margin-right: 10px; border: 2px solid #333;'></div>"
            f"<strong>Preview: </strong><span style='color: {selected_color}'>Category Color</span></div>",
            unsafe_allow_html=True
        )
    else:
        st.info("🎨 **No color selected** - Category will appear without color")
    
    st.markdown("---")
    
    with st.form(f"cat_form_{mode}_{category['id'] if category else 'new'}"):
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
        
        # Color picker (form-compatible widget)
        col1, col2 = st.columns([2, 1])
        
        with col1:
            color = st.color_picker(
                "Fine-tune Color (Optional)",
                value=selected_color if selected_color else "#007BFF",
                help="Fine-tune the selected color or choose a custom color",
                key=f"color_picker_{mode}_{category['id'] if category else 'new'}"
            )
        
        with col2:
            # Show hex code (read-only for reference)
            st.text_input("Hex Code", value=color, disabled=True, help="Generated hex code")
        
        # Live preview of category appearance with actual name
        if color and name:
            st.markdown("**Live Preview:**")
            st.markdown(
                f"<div style='display: flex; align-items: center; padding: 15px; border: 1px solid #ddd; border-radius: 8px; background-color: #f8f9fa; margin: 10px 0;'>"
                f"<div style='width: 24px; height: 24px; background-color: {color}; "
                f"border-radius: 50%; margin-right: 15px; border: 2px solid #333;'></div>"
                f"<strong style='font-size: 16px;'>{name}</strong></div>",
                unsafe_allow_html=True
            )
        elif name:
            st.markdown("**Live Preview:**")
            st.markdown(
                f"<div style='display: flex; align-items: center; padding: 15px; border: 1px solid #ddd; border-radius: 8px; background-color: #f8f9fa; margin: 10px 0;'>"
                f"<div style='width: 24px; height: 24px; background-color: #ccc; "
                f"border-radius: 50%; margin-right: 15px; border: 2px solid #333;'></div>"
                f"<strong style='font-size: 16px;'>{name}</strong><span style='margin-left: 10px; color: #666;'>(No color)</span></div>",
                unsafe_allow_html=True
            )
        
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
            
            # Color validation (only if provided)
            if color and not validate_hex_color(color):
                errors.append("Color must be in hex format (e.g., #007BFF)")
            
            if errors:
                for error in errors:
                    st.error(error)
                return {}
            
            # Clear session state after successful submission
            color_key = f"selected_color_{mode}_{category['id'] if category else 'new'}"
            if color_key in st.session_state:
                del st.session_state[color_key]
            
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


def display_category_card(category: dict, api_client: APIClient, show_actions: bool = True):
    """Display a single category card with optional actions."""
    with st.container():
        # Create card layout
        if show_actions:
            col1, col2, col3 = st.columns([3, 1, 1])
        else:
            col1 = st.columns([1])[0]
            col2 = col3 = None
        
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
        
        if show_actions and col2 and col3:
            with col2:
                # Edit button
                if st.button("✏️ Edit", key=f"cat_edit_{category['id']}", help="Edit this category"):
                    SessionManager.set(f"edit_category_{category['id']}", True)
                    st.rerun()
            
            with col3:
                # Delete/Restore button
                if category.get("is_active", True):
                    if st.button("🗑️ Delete", key=f"cat_delete_{category['id']}", help="Delete this category"):
                        if safe_api_call_with_success(
                            lambda: api_client.delete_category(category['id']),
                            "Category deleted successfully",
                            f"Failed to delete category: {category['name']}"
                        ):
                            st.rerun()
                else:
                    if st.button("🔄 Restore", key=f"cat_restore_{category['id']}", help="Restore this category"):
                        if safe_api_call_with_success(
                            lambda: api_client.restore_category(category['id']),
                            "Category restored successfully",
                            f"Failed to restore category: {category['name']}"
                        ):
                            st.rerun()
        
        st.divider()


def manage_categories_section(api_client: APIClient):
    """Main category management section."""
    st.subheader("🏷️ Category Management")
    
    # Load category statistics
    stats = safe_api_call(
        api_client.get_category_stats,
        "Failed to load category statistics"
    )
    
    if stats:
        display_category_statistics(stats)
    
    st.divider()
    
    # Management mode selection
    management_tabs = st.tabs(["➕ Create Category", "📋 Browse & Edit", "🔄 Bulk Operations"])
    
    with management_tabs[0]:
        # Category creation
        st.markdown("### ➕ Create New Category")
        
        form_data = create_category_form(mode="create")
        
        if form_data:
            # Create category
            if safe_api_call_with_success(
                lambda: api_client.create_category(form_data),
                "Category created successfully",
                "Failed to create category"
            ):
                st.rerun()
    
    with management_tabs[1]:
        # Browse and edit categories
        st.markdown("### 📋 Browse & Edit Categories")
        
        # Create layout with sidebar filters and main content
        filters = create_category_search_filters()
        
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
                        if st.button("❌ Cancel Edit", key=f"cat_cancel_edit_{category['id']}"):
                            SessionManager.clear(f"edit_category_{category['id']}")
                            st.rerun()
                        
                        st.divider()
                    else:
                        display_category_card(category, api_client, show_actions=True)
                
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
    
    with management_tabs[2]:
        # Bulk operations
        st.markdown("### 🔄 Bulk Operations")
        st.info("Bulk operations for categories will be implemented in a future update.")
        
        # Placeholder for bulk operations
        st.markdown("""
        **Planned Features:**
        - Bulk category creation from CSV
        - Bulk category updates
        - Bulk category deletion/restoration
        - Category template management
        """)


def browse_categories_section(api_client: APIClient):
    """Read-only category browsing section for the Categories page."""
    st.subheader("📋 Browse Categories")
    
    # Load category statistics
    stats = safe_api_call(
        api_client.get_category_stats,
        "Failed to load category statistics"
    )
    
    if stats:
        display_category_statistics(stats)
    
    st.divider()
    
    # Create layout with sidebar filters and main content
    filters = create_category_search_filters()
    
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
            
            # Add management link
            if st.button("⚙️ Manage Categories", type="primary"):
                st.switch_page("pages/03_⚙️_Manage.py")
            
            st.divider()
            
            # Display categories (read-only)
            for category in categories:
                display_category_card(category, api_client, show_actions=False)
            
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
    
    # Navigation help
    st.markdown("---")
    st.markdown("💡 **Need to create or edit categories?** Use the [⚙️ Manage page](pages/03_⚙️_Manage.py) for all category management operations.")