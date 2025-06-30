"""
Management page for the Home Inventory System.

Create, edit, and delete locations in your inventory system.
"""

import streamlit as st
import logging
from typing import Dict, Any, Optional, List

from utils.api_client import APIClient, APIError
from utils.helpers import (
    safe_api_call, show_error, show_success, show_warning,
    get_location_type_options, get_location_type_display,
    validate_location_form, handle_api_error, SessionManager
)
from components.location_templates import show_bulk_operations
from components.keyboard_shortcuts import (
    enable_keyboard_shortcuts, show_keyboard_shortcuts_help,
    create_action_buttons_row
)
from components.import_export import show_import_export_interface
from components.validation import create_enhanced_form_validation, create_validation_summary_widget

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Manage - Home Inventory System",
    page_icon="⚙️",
    layout="wide"
)

def load_parent_options() -> List[Dict[str, Any]]:
    """Load available parent locations for selection."""
    if 'api_client' not in st.session_state:
        st.session_state.api_client = APIClient()
    
    api_client = st.session_state.api_client
    
    try:
        # Get all locations to use as potential parents
        locations = api_client.get_locations(skip=0, limit=1000)  # Assume reasonable limit
        
        # Filter out shelves (they can't have children)
        parent_options = [
            loc for loc in locations 
            if loc.get('location_type') != 'shelf'
        ]
        
        return parent_options
    
    except Exception as e:
        logger.error(f"Failed to load parent options: {e}")
        return []

def load_category_options() -> List[Dict[str, Any]]:
    """Load available categories for selection."""
    if 'api_client' not in st.session_state:
        st.session_state.api_client = APIClient()
    
    api_client = st.session_state.api_client
    
    try:
        # Get all categories
        categories_data = api_client.get_categories()
        return categories_data.get('categories', []) if categories_data else []
    
    except Exception as e:
        logger.error(f"Failed to load category options: {e}")
        return []

def create_location_form(
    location_data: Optional[Dict[str, Any]] = None,
    is_edit: bool = False
) -> Optional[Dict[str, Any]]:
    """Create a form for location creation/editing."""
    
    # Form title
    form_title = "✏️ Edit Location" if is_edit else "➕ Create New Location"
    st.subheader(form_title)
    
    # Load parent and category options
    parent_options = load_parent_options()
    category_options = load_category_options()
    
    # Initialize form data
    if location_data:
        default_name = location_data.get('name', '')
        default_description = location_data.get('description', '')
        default_type = location_data.get('location_type', 'house')
        default_parent_id = location_data.get('parent_id')
        default_category_id = location_data.get('category_id')
    else:
        default_name = ''
        default_description = ''
        default_type = 'house'
        default_parent_id = None
        default_category_id = None
    
    with st.form(key="location_form", clear_on_submit=not is_edit):
        # Basic information
        st.write("**Basic Information**")
        
        name = st.text_input(
            "Location Name *",
            value=default_name,
            max_chars=255,
            help="Enter a descriptive name for this location"
        )
        
        description = st.text_area(
            "Description",
            value=default_description,
            max_chars=500,
            help="Optional description providing more details about this location"
        )
        
        # Location type
        st.write("**Location Type**")
        
        location_types = get_location_type_options()
        type_displays = [get_location_type_display(t) for t in location_types]
        
        try:
            default_type_index = location_types.index(default_type)
        except ValueError:
            default_type_index = 0
        
        selected_type_display = st.selectbox(
            "Type *",
            type_displays,
            index=default_type_index,
            help="Select the type of location"
        )
        
        # Extract actual type value
        selected_type = location_types[type_displays.index(selected_type_display)]
        
        # Parent location
        st.write("**Parent Location**")
        
        parent_options_display = ["None (Root Level)"]
        parent_ids = [None]
        
        for parent in parent_options:
            if is_edit and location_data and parent['id'] == location_data.get('id'):
                continue  # Can't be parent of itself
            
            parent_options_display.append(f"{parent['name']} ({parent['full_path']})")
            parent_ids.append(parent['id'])
        
        # Find default parent index
        default_parent_index = 0
        if default_parent_id:
            try:
                default_parent_index = parent_ids.index(default_parent_id)
            except ValueError:
                pass
        
        selected_parent_index = st.selectbox(
            "Parent Location",
            range(len(parent_options_display)),
            format_func=lambda x: parent_options_display[x],
            index=default_parent_index,
            help="Select a parent location or leave as root level"
        )
        
        selected_parent_id = parent_ids[selected_parent_index]
        
        # Category selection
        st.write("**Category (Optional)**")
        
        category_options_display = ["None (No Category)"]
        category_ids = [None]
        
        for category in category_options:
            category_options_display.append(f"{category['name']} ({category['description'] or 'No description'})")
            category_ids.append(category['id'])
        
        # Find default category index
        default_category_index = 0
        if default_category_id:
            try:
                default_category_index = category_ids.index(default_category_id)
            except ValueError:
                pass
        
        selected_category_index = st.selectbox(
            "Category",
            range(len(category_options_display)),
            format_func=lambda x: category_options_display[x],
            index=default_category_index,
            help="Optionally assign this location to a category for organization"
        )
        
        selected_category_id = category_ids[selected_category_index]
        
        # Validation info
        st.info("""
        **Hierarchy Rules:**
        - 🏠 Houses: Can contain Rooms (Root level only)
        - 🚪 Rooms: Can contain Containers (Must be in a House)
        - 📦 Containers: Can contain Shelves (Must be in a Room)
        - 📚 Shelves: Cannot contain other locations (Must be in a Container)
        """)
        
        # Form buttons
        col1, col2 = st.columns(2)
        
        with col1:
            submit_button = st.form_submit_button(
                "💾 Update Location" if is_edit else "✅ Create Location",
                type="primary",
                use_container_width=True
            )
        
        with col2:
            cancel_button = st.form_submit_button(
                "❌ Cancel",
                use_container_width=True
            )
        
        if cancel_button:
            SessionManager.clear('edit_location_id')
            st.rerun()
        
        if submit_button:
            # Prepare location data
            form_data = {
                'name': name.strip(),
                'description': description.strip() if description else None,
                'location_type': selected_type,
                'parent_id': selected_parent_id,
                'category_id': selected_category_id
            }
            
            # Enhanced validation
            api_client = st.session_state.get('api_client')
            edit_location_id = location_data.get('id') if location_data else None
            
            is_valid = create_enhanced_form_validation(
                form_data, 
                api_client, 
                edit_location_id
            )
            
            if not is_valid:
                return None
            
            return form_data
    
    return None

def create_location(location_data: Dict[str, Any]):
    """Create a new location."""
    api_client = st.session_state.api_client
    
    try:
        with st.spinner("Creating location..."):
            result = api_client.create_location(location_data)
        
        show_success(f"Location '{result['name']}' created successfully!")
        
        # Optionally show created location details
        if st.checkbox("Show created location details"):
            st.json(result)
        
        # Reset form
        st.rerun()
        
    except Exception as e:
        handle_api_error(e, "create location")

def update_location(location_id: int, location_data: Dict[str, Any]):
    """Update an existing location."""
    api_client = st.session_state.api_client
    
    try:
        with st.spinner("Updating location..."):
            result = api_client.update_location(location_id, location_data)
        
        show_success(f"Location '{result['name']}' updated successfully!")
        
        # Clear edit mode
        SessionManager.clear('edit_location_id')
        
        # Optionally show updated location details
        if st.checkbox("Show updated location details"):
            st.json(result)
        
        st.rerun()
        
    except Exception as e:
        handle_api_error(e, "update location")

def load_location_for_edit(location_id: int) -> Optional[Dict[str, Any]]:
    """Load location data for editing."""
    api_client = st.session_state.api_client
    
    try:
        return api_client.get_location(location_id)
    except Exception as e:
        handle_api_error(e, f"load location {location_id}")
        return None

def reset_form_callback():
    """Reset form callback function."""
    SessionManager.clear('edit_location_id')
    st.rerun()

def show_quick_actions():
    """Show enhanced quick action buttons."""
    st.subheader("⚡ Quick Actions")
    
    quick_actions = {
        'view_locations': {
            'label': '📍 View All Locations',
            'callback': lambda: st.switch_page("pages/02_📍_Locations.py"),
            'help': 'Browse all locations (Alt+L)'
        },
        'dashboard': {
            'label': '📊 View Dashboard',
            'callback': lambda: st.switch_page("pages/01_📊_Dashboard.py"),
            'help': 'Go to dashboard (Alt+D)'
        },
        'reset_form': {
            'label': '🔄 Reset Form',
            'callback': lambda: reset_form_callback(),
            'help': 'Clear current form and reset'
        }
    }
    
    create_action_buttons_row(quick_actions, "manage_actions")

def main():
    """Main manage page function."""
    st.title("⚙️ Manage Locations")
    st.markdown("Create new locations and manage your inventory hierarchy")
    
    # Enable keyboard shortcuts
    enable_keyboard_shortcuts()
    show_keyboard_shortcuts_help()
    
    # Management mode selection
    management_tabs = st.tabs(["➕ Individual", "🔄 Bulk Operations", "📂 Import/Export"])
    
    with management_tabs[0]:
        # Individual location management
        # Check for edit mode
        edit_location_id = SessionManager.get('edit_location_id')
        
        if edit_location_id:
            st.markdown(f"**Editing Location ID: {edit_location_id}**")
            
            # Load location for editing
            with st.spinner("Loading location data..."):
                location_data = load_location_for_edit(edit_location_id)
            
            if not location_data:
                show_error("Could not load location data for editing")
                SessionManager.clear('edit_location_id')
                st.rerun()
                return
            
            # Show edit form
            form_data = create_location_form(location_data, is_edit=True)
            
            if form_data:
                update_location(edit_location_id, form_data)
        
        else:
            # Show create form
            form_data = create_location_form()
            
            if form_data:
                create_location(form_data)
    
    with management_tabs[1]:
        # Bulk operations using templates
        show_bulk_operations()
    
    with management_tabs[2]:
        # Import/Export functionality
        show_import_export_interface()
    
    # Data validation summary
    st.markdown("---")
    create_validation_summary_widget(st.session_state.get('api_client'))
    
    # Quick actions
    st.markdown("---")
    show_quick_actions()
    
    # Help section
    with st.expander("❓ Need Help?"):
        st.markdown("""
        ### Location Management Guide
        
        **Creating Locations:**
        1. Enter a descriptive name for your location
        2. Add an optional description for more details
        3. Select the appropriate location type
        4. Choose a parent location if applicable
        5. Click 'Create Location' to save
        
        **Editing Locations:**
        - Click 'Edit' next to any location in the Locations page
        - Modify the fields as needed
        - Click 'Update Location' to save changes
        
        **Location Hierarchy:**
        - Houses are top-level containers
        - Rooms go inside houses
        - Containers go inside rooms
        - Shelves go inside containers
        
        **Tips:**
        - Use clear, descriptive names
        - Add descriptions for better organization
        - Follow the hierarchy rules for best results
        """)

if __name__ == "__main__":
    main()