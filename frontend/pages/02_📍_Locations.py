"""
Locations page for the Home Inventory System.

Browse, search, and filter all inventory locations.
"""

import streamlit as st
import pandas as pd
import logging
from typing import List, Dict, Any, Optional

from utils.api_client import APIClient, APIError
from components.auth import is_authenticated, show_logout_button
from utils.helpers import (
    safe_api_call, show_error, show_success, show_warning,
    create_location_dataframe, get_location_type_options,
    handle_api_error, SessionManager
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
    page_title="Locations - Home Inventory System",
    page_icon="📍",
    layout="wide"
)

def create_search_filters() -> Dict[str, Any]:
    """Create enhanced search and filter controls."""
    st.sidebar.subheader("🔍 Advanced Search & Filters")
    
    # Enhanced search box with clear functionality
    search_text = create_enhanced_search_box(
        placeholder="Enter location name or description...",
        key="location_search",
        help_text="Search in location names and descriptions"
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
    
    # Quick type filters
    st.sidebar.subheader("📂 Quick Type Filters")
    type_filter_options = {
        'all': '🔍 All',
        'house': '🏠 Houses', 
        'room': '🚪 Rooms',
        'container': '📦 Containers',
        'shelf': '📚 Shelves'
    }
    
    current_type_filter = st.session_state.get('type_filter', 'all')
    selected_type_key = create_quick_filter_buttons(
        current_type_filter,
        type_filter_options,
        "type_filter"
    )
    
    # Store selected filter
    st.session_state['type_filter'] = selected_type_key
    selected_type = selected_type_key if selected_type_key != 'all' else None
    
    # Category filters
    st.sidebar.subheader("🏷️ Category Filters")
    
    # Load categories for filtering
    if 'api_client' not in st.session_state:
        st.session_state.api_client = APIClient()
    
    api_client = st.session_state.api_client
    categories_data = safe_api_call(
        lambda: api_client.get_categories(page=1, per_page=100, include_inactive=False),
        "Failed to load categories for filtering"
    )
    
    categories = categories_data.get('categories', []) if categories_data else []
    
    # Category filter options
    category_filter_options = {'all': '🔍 All Categories', 'none': '❌ No Category'}
    for category in categories:
        color = category.get('color', '#666666')
        name = category.get('name', 'Unnamed')
        category_filter_options[str(category['id'])] = f"🏷️ {name}"
    
    current_category_filter = st.session_state.get('category_filter', 'all')
    selected_category_key = create_quick_filter_buttons(
        current_category_filter,
        category_filter_options,
        "category_filter"
    )
    
    # Store selected category filter
    st.session_state['category_filter'] = selected_category_key
    selected_category_id = None if selected_category_key in ['all', 'none'] else int(selected_category_key) if selected_category_key != 'all' else None
    include_uncategorized = selected_category_key == 'none'
    
    # Parent location filter
    parent_filter = st.sidebar.selectbox(
        "Parent Location",
        ['All', 'Root Only', 'With Parent'],
        help="Filter by parent relationship"
    )
    
    # Depth filter
    with st.sidebar.expander("📏 Hierarchy Filters"):
        min_depth = st.number_input(
            "Minimum depth",
            min_value=0,
            max_value=10,
            value=0,
            help="Minimum hierarchy depth"
        )
        
        max_depth = st.number_input(
            "Maximum depth",
            min_value=0,
            max_value=10,
            value=10,
            help="Maximum hierarchy depth"
        )
        
        has_description = st.selectbox(
            "Has description",
            ["All", "With description", "Without description"],
            help="Filter by description presence"
        )
    
    # Sorting options
    with st.sidebar.expander("📊 Sorting & Display"):
        sort_by = st.selectbox(
            "Sort by",
            ["Name", "Type", "Category", "Created", "Updated", "Depth"],
            help="Sort locations by field"
        )
        
        sort_order = st.selectbox(
            "Sort order",
            ["Ascending", "Descending"],
            help="Sort order"
        )
        
        show_analytics = st.checkbox(
            "Show search analytics",
            value=True,
            help="Display analytics for search results"
        )
    
    # Pagination
    st.sidebar.subheader("📄 Pagination")
    page_size = st.sidebar.selectbox(
        "Items per page",
        [10, 20, 50, 100],
        index=1,
        help="Number of locations to display per page"
    )
    
    return {
        'search_text': search_text,
        'case_sensitive': case_sensitive,
        'search_mode': search_mode,
        'location_type': selected_type,
        'category_id': selected_category_id,
        'include_uncategorized': include_uncategorized,
        'categories': categories,  # Pass categories for display
        'parent_filter': parent_filter,
        'min_depth': min_depth,
        'max_depth': max_depth,
        'has_description': has_description,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'show_analytics': show_analytics,
        'page_size': page_size
    }

def load_locations(filters: Dict[str, Any], page: int = 0) -> Dict[str, Any]:
    """Load locations based on filters and pagination."""
    if 'api_client' not in st.session_state:
        st.session_state.api_client = APIClient()
    
    api_client = st.session_state.api_client
    
    # Check API connection
    if not api_client.health_check():
        show_error("Cannot connect to the API. Please check if the backend is running.")
        return {'locations': [], 'total': 0}
    
    try:
        # Calculate pagination
        skip = page * filters['page_size']
        limit = filters['page_size']
        
        # Prepare API parameters
        api_params = {
            'skip': skip,
            'limit': limit
        }
        
        # Add type filter
        if filters['location_type']:
            api_params['location_type'] = filters['location_type']
        
        # Add parent filter
        if filters['parent_filter'] == 'Root Only':
            api_params['parent_id'] = None
        # Note: 'With Parent' filter would need additional API logic
        
        # Get locations
        if filters['search_text']:
            # Use search API
            search_data = {
                'pattern': filters['search_text']
            }
            if filters['location_type']:
                search_data['location_type'] = filters['location_type']
            
            locations = api_client.search_locations(search_data)
            
            # Apply pagination to search results (client-side)
            total = len(locations)
            start_idx = skip
            end_idx = start_idx + limit
            locations = locations[start_idx:end_idx]
        else:
            # Use regular list API
            locations = api_client.get_locations(**api_params)
            # For simplicity, assume we get all results (would need count API for exact total)
            total = len(locations)
        
        return {
            'locations': locations,
            'total': total,
            'page': page,
            'has_more': len(locations) == filters['page_size']
        }
    
    except Exception as e:
        handle_api_error(e, "load locations")
        return {'locations': [], 'total': 0}

def display_location_actions(location: Dict[str, Any]):
    """Display action buttons for a location."""
    col1, col2, col3, col4 = st.columns(4)
    
    location_id = location['id']
    location_name = location['name']
    
    with col1:
        if st.button("👁️ View", key=f"view_{location_id}"):
            SessionManager.set('selected_location_id', location_id)
            show_location_details(location)
    
    with col2:
        if st.button("✏️ Edit", key=f"edit_{location_id}"):
            SessionManager.set('edit_location_id', location_id)
            st.switch_page("pages/03_⚙️_Manage.py")
    
    with col3:
        if st.button("👥 Children", key=f"children_{location_id}"):
            show_location_children(location_id)
    
    with col4:
        if st.button("🗑️ Delete", key=f"delete_{location_id}", type="secondary"):
            show_delete_confirmation(location_id, location_name)

def show_location_details(location: Dict[str, Any]):
    """Show detailed information about a location."""
    st.subheader(f"📍 {location['name']}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Basic Information:**")
        st.write(f"- **ID:** {location['id']}")
        st.write(f"- **Type:** {location['location_type'].title()}")
        st.write(f"- **Description:** {location.get('description', 'No description')}")
        
        # Show category information
        category_id = location.get('category_id')
        if category_id:
            # Try to get category name from API
            try:
                api_client = st.session_state.api_client
                category = api_client.get_category(category_id)
                category_name = category.get('name', 'Unknown')
                category_color = category.get('color', '#666666')
                st.markdown(f"- **Category:** 🏷️ {category_name}")
                if category_color:
                    st.markdown(f"  <div style='width: 20px; height: 20px; background-color: {category_color}; border-radius: 50%; display: inline-block; margin-left: 10px;'></div>", unsafe_allow_html=True)
            except:
                st.write(f"- **Category:** Category ID {category_id}")
        else:
            st.write("- **Category:** ❌ No Category")
        
    with col2:
        st.write("**Location Details:**")
        st.write(f"- **Full Path:** {location['full_path']}")
        st.write(f"- **Depth:** {location['depth']}")
        st.write(f"- **Parent ID:** {location.get('parent_id', 'None (Root)')}")
    
    st.write("**Timestamps:**")
    st.write(f"- **Created:** {location['created_at']}")
    st.write(f"- **Updated:** {location['updated_at']}")

def show_location_children(location_id: int):
    """Show children of a location."""
    api_client = st.session_state.api_client
    
    try:
        children = api_client.get_location_children(location_id)
        
        if children:
            st.subheader(f"👥 Child Locations ({len(children)})")
            children_df = create_location_dataframe(children)
            st.dataframe(children_df, use_container_width=True, hide_index=True)
        else:
            st.info("This location has no child locations.")
            
    except Exception as e:
        handle_api_error(e, "load child locations")

def show_delete_confirmation(location_id: int, location_name: str):
    """Show delete confirmation dialog using session state."""
    # Set session state to show confirmation dialog
    SessionManager.set('show_delete_confirmation', True)
    SessionManager.set('delete_location_id', location_id)
    SessionManager.set('delete_location_name', location_name)
    st.rerun()

def delete_location(location_id: int, location_name: str):
    """Delete a location."""
    api_client = st.session_state.api_client
    
    try:
        with st.spinner(f"Deleting {location_name}..."):
            success = api_client.delete_location(location_id)
        
        if success:
            show_success(f"Location '{location_name}' deleted successfully")
            # Clear session state
            SessionManager.clear('show_delete_confirmation')
            SessionManager.clear('delete_location_id')
            SessionManager.clear('delete_location_name')
            st.rerun()
        else:
            show_error("Failed to delete location")
            
    except Exception as e:
        handle_api_error(e, f"delete location '{location_name}'")

def render_delete_confirmation_dialog():
    """Render the delete confirmation dialog when needed."""
    if not SessionManager.get('show_delete_confirmation', False):
        return
    
    location_id = SessionManager.get('delete_location_id')
    location_name = SessionManager.get('delete_location_name')
    
    if not location_id or not location_name:
        # Clear invalid state
        SessionManager.clear('show_delete_confirmation')
        SessionManager.clear('delete_location_id')
        SessionManager.clear('delete_location_name')
        return
    
    # Display confirmation dialog
    st.markdown("---")
    st.error(f"⚠️ **Delete Confirmation Required**")
    st.warning(f"Are you sure you want to delete location '{location_name}'?")
    st.write("⚠️ **This action cannot be undone and will also delete all child locations and their inventory entries.**")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🗑️ Delete", key="confirm_location_delete", type="primary"):
            delete_location(location_id, location_name)
    
    with col2:
        if st.button("❌ Cancel", key="cancel_location_delete"):
            # Clear session state
            SessionManager.clear('show_delete_confirmation')
            SessionManager.clear('delete_location_id')
            SessionManager.clear('delete_location_name')
            st.rerun()

def main():
    """Main locations page function."""
    # Check authentication
    if not is_authenticated():
        st.error('🔒 Please log in to access this page')
        st.stop()
    
    st.title("📍 Locations")
    st.markdown("Browse and manage all locations in your inventory system")
    
    # Show logout button
    show_logout_button()
    
    # Enable keyboard shortcuts
    enable_keyboard_shortcuts()
    show_keyboard_shortcuts_help()
    
    # Get search filters
    filters = create_search_filters()
    
    # Pagination state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 0
    
    # Load data
    with st.spinner("Loading locations..."):
        data = load_locations(filters, st.session_state.current_page)
    
    locations = data.get('locations', [])
    total = data.get('total', 0)
    page = data.get('page', 0)
    has_more = data.get('has_more', False)
    
    if not locations:
        st.info("No locations found matching your criteria.")
        
        if st.button("➕ Create Your First Location"):
            st.switch_page("pages/03_⚙️_Manage.py")
        return
    
    # Show search analytics if enabled
    if filters.get('show_analytics', True):
        from components.visualizations import create_advanced_search_metrics
        create_advanced_search_metrics(locations, total)
    
    # Display results summary
    start_idx = page * filters['page_size'] + 1
    end_idx = start_idx + len(locations) - 1
    st.write(f"Showing {start_idx}-{end_idx} of {total} locations")
    
    # Display locations table with category support
    df = create_location_dataframe(locations, filters.get('categories', []))
    
    # Apply sorting based on filters
    if filters.get('sort_by') == 'Category':
        # Sort by category name instead of display string
        sort_column = 'Category_Name'
    else:
        sort_column = filters.get('sort_by', 'Name')
    
    if sort_column in df.columns:
        ascending = filters.get('sort_order', 'Ascending') == 'Ascending'
        df = df.sort_values(by=sort_column, ascending=ascending)
    
    # Remove the Category_Name column from display (it's just for sorting)
    display_df = df.drop(columns=['Category_Name']) if 'Category_Name' in df.columns else df
    
    # Use data editor for interactive table
    edited_df = st.data_editor(
        display_df,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        disabled=["ID", "Category", "Full Path", "Depth", "Created", "Updated"],
        column_config={
            "Category": st.column_config.TextColumn(
                "Category",
                help="Location category with visual indicator",
                width="medium"
            )
        }
    )
    
    # Action buttons for each location
    st.subheader("🔧 Location Actions")
    
    for i, location in enumerate(locations):
        with st.expander(f"Actions for {location['name']}"):
            display_location_actions(location)
    
    # Enhanced pagination controls
    if total > filters['page_size']:
        new_page = create_pagination_controls(
            current_page=page,
            total_items=total,
            items_per_page=filters['page_size'],
            key_prefix="locations"
        )
        
        if new_page != page:
            st.session_state.current_page = new_page
            st.rerun()
    
    # Render delete confirmation dialog if needed
    render_delete_confirmation_dialog()
    
    # Enhanced quick actions
    st.markdown("---")
    st.subheader("⚡ Quick Actions")
    
    quick_actions = {
        'add_location': {
            'label': '➕ Add New Location',
            'callback': lambda: st.switch_page("pages/03_⚙️_Manage.py"),
            'type': 'primary',
            'help': 'Create a new location (Alt+N)'
        },
        'refresh': {
            'label': '🔄 Refresh',
            'callback': lambda: st.rerun(),
            'help': 'Refresh locations list (Alt+R)'
        },
        'dashboard': {
            'label': '📊 View Dashboard',
            'callback': lambda: st.switch_page("pages/01_📊_Dashboard.py"),
            'help': 'Go to dashboard (Alt+D)'
        }
    }
    
    create_action_buttons_row(quick_actions, "locations_actions")

if __name__ == "__main__":
    main()