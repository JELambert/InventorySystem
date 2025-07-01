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
    validate_location_form, handle_api_error, SessionManager,
    safe_strip, safe_string_check, safe_string_or_none
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
                'name': safe_strip(name),
                'description': safe_string_or_none(description),
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
    st.title("⚙️ Manage Inventory")
    st.markdown("Create and manage your locations and items")
    
    # Enable keyboard shortcuts
    enable_keyboard_shortcuts()
    show_keyboard_shortcuts_help()
    
    # Main entity selection
    entity_tabs = st.tabs(["📍 Locations", "📦 Items"])
    
    with entity_tabs[0]:
        manage_locations()
    
    with entity_tabs[1]:
        manage_items()

def manage_locations():
    """Location management section."""
    st.subheader("📍 Location Management")
    
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

def manage_items():
    """Item management section."""
    st.subheader("📦 Item Management")
    
    # Management mode selection
    item_tabs = st.tabs(["➕ Add Item", "📝 Edit Items"])
    
    with item_tabs[0]:
        show_item_creation_form()
    
    with item_tabs[1]:
        show_item_editing_interface()

def show_item_creation_form():
    """Display item creation form."""
    st.markdown("### ➕ Create New Item")
    
    # Initialize API client
    if 'api_client' not in st.session_state:
        st.session_state.api_client = APIClient()
    
    api_client = st.session_state.api_client
    
    # Load available locations and categories
    with st.spinner("Loading locations and categories..."):
        locations = safe_api_call(
            lambda: api_client.get_locations(skip=0, limit=1000),
            "Failed to load locations"
        )
        categories = safe_api_call(
            lambda: api_client.get_categories(page=1, per_page=100, include_inactive=False),
            "Failed to load categories"
        )
    
    if not locations:
        st.warning("⚠️ No locations available. Please create locations first.")
        if st.button("Go to Location Management"):
            st.switch_page("pages/03_⚙️_Manage.py")
        return
    
    # Item creation form
    with st.form("create_item_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            # Basic information
            st.markdown("**Basic Information**")
            name = st.text_input("Item Name*", help="Enter the item name")
            description = st.text_area("Description", help="Optional description of the item")
            
            # Item type selection
            item_types = [
                "electronics", "furniture", "clothing", "books", "documents",
                "tools", "kitchen", "decor", "collectibles", "hobby",
                "office", "personal", "seasonal", "storage", "other"
            ]
            item_type = st.selectbox("Item Type*", item_types, help="Select the primary type")
            
            # Condition and status
            conditions = ["excellent", "very_good", "good", "fair", "poor", "for_repair", "not_working"]
            condition = st.selectbox("Condition", conditions, index=2, help="Current condition")
            
            statuses = ["available", "in_use", "reserved", "maintenance", "lost", "disposed"]
            status = st.selectbox("Status", statuses, help="Current availability status")
        
        with col2:
            # Location and category
            st.markdown("**Location & Organization**")
            
            # Location selection
            location_options = {loc['id']: f"{loc['name']} ({loc['location_type']})" for loc in locations}
            selected_location_id = st.selectbox(
                "Location*",
                options=list(location_options.keys()),
                format_func=lambda x: location_options[x],
                help="Where is this item stored?"
            )
            
            # Category selection (optional)
            if categories and categories.get('categories'):
                cat_options = {0: "No Category"}
                cat_options.update({
                    cat['id']: cat['name'] 
                    for cat in categories['categories'] 
                    if cat.get('is_active', True)
                })
                selected_category_id = st.selectbox(
                    "Category",
                    options=list(cat_options.keys()),
                    format_func=lambda x: cat_options[x],
                    help="Optional category for organization"
                )
                if selected_category_id == 0:
                    selected_category_id = None
            else:
                selected_category_id = None
                st.info("No categories available")
        
        # Additional details in expander
        with st.expander("📋 Additional Details"):
            col3, col4 = st.columns(2)
            
            with col3:
                st.markdown("**Product Information**")
                brand = st.text_input("Brand", help="Manufacturer or brand name")
                model = st.text_input("Model", help="Model number or name")
                serial_number = st.text_input("Serial Number", help="Serial number if applicable")
                barcode = st.text_input("Barcode/UPC", help="Barcode or UPC if applicable")
            
            with col4:
                st.markdown("**Value & Dates**")
                purchase_price = st.number_input("Purchase Price ($)", min_value=0.0, format="%.2f", help="Original purchase price")
                current_value = st.number_input("Current Value ($)", min_value=0.0, format="%.2f", help="Current estimated value")
                purchase_date = st.date_input("Purchase Date", value=None, help="Date of purchase")
                warranty_expiry = st.date_input("Warranty Expiry", value=None, help="Warranty expiration date")
            
            # Physical properties
            st.markdown("**Physical Properties**")
            col5, col6 = st.columns(2)
            with col5:
                weight = st.number_input("Weight (kg)", min_value=0.0, format="%.3f", help="Weight in kilograms")
                color = st.text_input("Color", help="Primary color")
            with col6:
                dimensions = st.text_input("Dimensions", help="e.g., '10x20x5 cm'")
                tags = st.text_input("Tags", help="Comma-separated tags for search")
            
            # Notes
            notes = st.text_area("Notes", help="Additional notes or observations")
        
        # Form submission
        submitted = st.form_submit_button("✅ Create Item", type="primary", use_container_width=True)
        
        if submitted:
            stripped_name = safe_strip(name)
            if not stripped_name:
                st.error("Item name is required")
                return
            
            # Prepare item data (location_id will be handled via inventory)
            item_data = {
                "name": stripped_name,
                "item_type": item_type,
                "condition": condition,
                "status": status
            }
            
            # Add optional fields if provided using safe string helpers
            description_clean = safe_string_or_none(description)
            if description_clean:
                item_data["description"] = description_clean
            if selected_category_id:
                item_data["category_id"] = selected_category_id
            
            brand_clean = safe_string_or_none(brand)
            if brand_clean:
                item_data["brand"] = brand_clean
            
            model_clean = safe_string_or_none(model)
            if model_clean:
                item_data["model"] = model_clean
            
            serial_number_clean = safe_string_or_none(serial_number)
            if serial_number_clean:
                item_data["serial_number"] = serial_number_clean
            
            barcode_clean = safe_string_or_none(barcode)
            if barcode_clean:
                item_data["barcode"] = barcode_clean
            
            if purchase_price > 0:
                item_data["purchase_price"] = purchase_price
            if current_value > 0:
                item_data["current_value"] = current_value
            if purchase_date:
                item_data["purchase_date"] = purchase_date.isoformat()
            if warranty_expiry:
                item_data["warranty_expiry"] = warranty_expiry.isoformat()
            if weight > 0:
                item_data["weight"] = weight
            
            color_clean = safe_string_or_none(color)
            if color_clean:
                item_data["color"] = color_clean
            
            dimensions_clean = safe_string_or_none(dimensions)
            if dimensions_clean:
                item_data["dimensions"] = dimensions_clean
            
            tags_clean = safe_string_or_none(tags)
            if tags_clean:
                item_data["tags"] = tags_clean
            
            notes_clean = safe_string_or_none(notes)
            if notes_clean:
                item_data["notes"] = notes_clean
            
            # Create the item
            with st.spinner("Creating item..."):
                result = safe_api_call(
                    lambda: api_client.create_item(item_data),
                    "Failed to create item"
                )
            
            if result:
                show_success(f"Item '{name}' created successfully!")
                st.balloons()
                # Clear form by rerunning
                st.rerun()

def show_item_editing_interface():
    """Display interface for editing existing items."""
    st.markdown("### 📝 Edit Existing Items")
    
    # Initialize API client
    if 'api_client' not in st.session_state:
        st.session_state.api_client = APIClient()
    
    api_client = st.session_state.api_client
    
    # Load existing items
    with st.spinner("Loading items..."):
        items = safe_api_call(
            lambda: api_client.get_items(skip=0, limit=100),
            "Failed to load items"
        )
    
    if not items:
        st.info("📦 No items found. Create some items first!")
        return
    
    # Item selection
    item_options = {item['id']: f"{item['name']} ({item.get('item_type', '').replace('_', ' ').title()})" for item in items}
    selected_item_id = st.selectbox(
        "Select Item to Edit",
        options=list(item_options.keys()),
        format_func=lambda x: item_options[x]
    )
    
    if selected_item_id:
        selected_item = next(item for item in items if item['id'] == selected_item_id)
        
        # Display item details
        st.markdown(f"**Editing: {selected_item['name']}**")
        
        # Quick action buttons
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📝 Full Edit"):
                st.session_state.edit_item_id = selected_item_id
                st.switch_page("pages/05_📦_Items.py")
        
        with col2:
            if st.button("📍 Change Location"):
                st.session_state.show_move_item = True
        
        with col3:
            if st.button("🔄 Update Status"):
                st.session_state.show_status_update = True
        
        with col4:
            if st.button("🗑️ Delete Item"):
                st.session_state.show_delete_confirm = True
        
        # Show current item details
        with st.expander("📋 Current Item Details", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Type:** {selected_item.get('item_type', '').replace('_', ' ').title()}")
                st.write(f"**Condition:** {selected_item.get('condition', '').replace('_', ' ').title()}")
                st.write(f"**Status:** {selected_item.get('status', '').replace('_', ' ').title()}")
                if selected_item.get('brand'):
                    st.write(f"**Brand:** {selected_item['brand']}")
                if selected_item.get('model'):
                    st.write(f"**Model:** {selected_item['model']}")
            
            with col2:
                if selected_item.get('current_value'):
                    st.write(f"**Current Value:** ${selected_item['current_value']:.2f}")
                if selected_item.get('purchase_price'):
                    st.write(f"**Purchase Price:** ${selected_item['purchase_price']:.2f}")
                st.write(f"**Created:** {selected_item.get('created_at', '').split('T')[0]}")
                if selected_item.get('updated_at'):
                    st.write(f"**Updated:** {selected_item['updated_at'].split('T')[0]}")
        
        # Handle modal actions
        if st.session_state.get('show_delete_confirm'):
            st.error("⚠️ Are you sure you want to delete this item? This action cannot be undone.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Yes, Delete", type="primary"):
                    with st.spinner("Deleting item..."):
                        success = safe_api_call(
                            lambda: api_client.delete_item(selected_item_id),
                            "Failed to delete item"
                        )
                    if success:
                        show_success("Item deleted successfully!")
                        st.session_state.show_delete_confirm = False
                        st.rerun()
            with col2:
                if st.button("❌ Cancel"):
                    st.session_state.show_delete_confirm = False
                    st.rerun()

if __name__ == "__main__":
    main()