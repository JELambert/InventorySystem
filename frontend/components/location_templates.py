"""
Location templates and bulk operations for the Home Inventory System.

This module provides predefined location templates and bulk operation
capabilities to streamline location management.
"""

import streamlit as st
from typing import List, Dict, Any, Optional
from utils.api_client import APIClient, APIError
from utils.helpers import show_success, show_error, handle_api_error


class LocationTemplate:
    """Represents a location template with predefined structure."""
    
    def __init__(self, name: str, description: str, locations: List[Dict[str, Any]]):
        self.name = name
        self.description = description
        self.locations = locations
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'locations': self.locations
        }


# Predefined location templates
LOCATION_TEMPLATES = {
    'basic_house': LocationTemplate(
        name="Basic House",
        description="Simple house structure with common rooms",
        locations=[
            {'name': 'My House', 'type': 'house', 'description': 'Main residence'},
            {'name': 'Living Room', 'type': 'room', 'parent': 'My House', 'description': 'Main living area'},
            {'name': 'Kitchen', 'type': 'room', 'parent': 'My House', 'description': 'Cooking and dining area'},
            {'name': 'Bedroom', 'type': 'room', 'parent': 'My House', 'description': 'Master bedroom'},
            {'name': 'Bathroom', 'type': 'room', 'parent': 'My House', 'description': 'Main bathroom'}
        ]
    ),
    
    'office_setup': LocationTemplate(
        name="Home Office",
        description="Complete home office organization structure",
        locations=[
            {'name': 'Home Office', 'type': 'room', 'description': 'Work area'},
            {'name': 'Desk', 'type': 'container', 'parent': 'Home Office', 'description': 'Main work desk'},
            {'name': 'Top Drawer', 'type': 'shelf', 'parent': 'Desk', 'description': 'Upper desk drawer'},
            {'name': 'Bottom Drawer', 'type': 'shelf', 'parent': 'Desk', 'description': 'Lower desk drawer'},
            {'name': 'Bookshelf', 'type': 'container', 'parent': 'Home Office', 'description': 'Office bookshelf'},
            {'name': 'Top Shelf', 'type': 'shelf', 'parent': 'Bookshelf', 'description': 'Upper bookshelf'},
            {'name': 'Middle Shelf', 'type': 'shelf', 'parent': 'Bookshelf', 'description': 'Middle bookshelf'},
            {'name': 'Bottom Shelf', 'type': 'shelf', 'parent': 'Bookshelf', 'description': 'Lower bookshelf'}
        ]
    ),
    
    'kitchen_storage': LocationTemplate(
        name="Kitchen Storage",
        description="Detailed kitchen organization with cabinets and pantry",
        locations=[
            {'name': 'Kitchen', 'type': 'room', 'description': 'Main kitchen area'},
            {'name': 'Upper Cabinets', 'type': 'container', 'parent': 'Kitchen', 'description': 'Wall-mounted cabinets'},
            {'name': 'Lower Cabinets', 'type': 'container', 'parent': 'Kitchen', 'description': 'Base cabinets'},
            {'name': 'Pantry', 'type': 'container', 'parent': 'Kitchen', 'description': 'Food storage pantry'},
            {'name': 'Refrigerator', 'type': 'container', 'parent': 'Kitchen', 'description': 'Main refrigerator'},
            {'name': 'Top Shelf', 'type': 'shelf', 'parent': 'Upper Cabinets', 'description': 'Upper cabinet shelf'},
            {'name': 'Bottom Shelf', 'type': 'shelf', 'parent': 'Lower Cabinets', 'description': 'Lower cabinet shelf'},
            {'name': 'Pantry Shelf 1', 'type': 'shelf', 'parent': 'Pantry', 'description': 'Top pantry shelf'},
            {'name': 'Pantry Shelf 2', 'type': 'shelf', 'parent': 'Pantry', 'description': 'Middle pantry shelf'},
            {'name': 'Pantry Shelf 3', 'type': 'shelf', 'parent': 'Pantry', 'description': 'Bottom pantry shelf'}
        ]
    ),
    
    'garage_workshop': LocationTemplate(
        name="Garage Workshop",
        description="Workshop and storage organization for garage",
        locations=[
            {'name': 'Garage', 'type': 'room', 'description': 'Garage and workshop area'},
            {'name': 'Workbench', 'type': 'container', 'parent': 'Garage', 'description': 'Main workbench'},
            {'name': 'Tool Cabinet', 'type': 'container', 'parent': 'Garage', 'description': 'Tool storage cabinet'},
            {'name': 'Storage Shelves', 'type': 'container', 'parent': 'Garage', 'description': 'Wall storage shelves'},
            {'name': 'Pegboard', 'type': 'container', 'parent': 'Garage', 'description': 'Tool pegboard'},
            {'name': 'Top Drawer', 'type': 'shelf', 'parent': 'Workbench', 'description': 'Upper workbench drawer'},
            {'name': 'Bottom Drawer', 'type': 'shelf', 'parent': 'Workbench', 'description': 'Lower workbench drawer'},
            {'name': 'Hand Tools', 'type': 'shelf', 'parent': 'Tool Cabinet', 'description': 'Hand tool storage'},
            {'name': 'Power Tools', 'type': 'shelf', 'parent': 'Tool Cabinet', 'description': 'Power tool storage'},
            {'name': 'Hardware', 'type': 'shelf', 'parent': 'Storage Shelves', 'description': 'Screws, bolts, etc.'}
        ]
    )
}


class BulkLocationCreator:
    """Handles bulk creation of locations from templates or CSV."""
    
    def __init__(self, api_client: APIClient):
        self.api_client = api_client
    
    def create_from_template(self, template: LocationTemplate, parent_location_id: Optional[int] = None) -> Dict[str, Any]:
        """Create locations from a template."""
        results = {
            'created': [],
            'errors': [],
            'location_map': {}  # Maps template names to created IDs
        }
        
        try:
            # Sort locations by hierarchy (house first, then rooms, etc.)
            sorted_locations = self._sort_by_hierarchy(template.locations)
            
            for loc_data in sorted_locations:
                try:
                    # Resolve parent ID
                    parent_id = parent_location_id
                    if 'parent' in loc_data and loc_data['parent'] in results['location_map']:
                        parent_id = results['location_map'][loc_data['parent']]
                    
                    # Create location data
                    location_request = {
                        'name': loc_data['name'],
                        'description': loc_data.get('description', ''),
                        'location_type': loc_data['type'],
                        'parent_id': parent_id
                    }
                    
                    # Create location
                    created_location = self.api_client.create_location(location_request)
                    results['created'].append(created_location)
                    results['location_map'][loc_data['name']] = created_location['id']
                    
                except Exception as e:
                    error_msg = f"Failed to create '{loc_data['name']}': {str(e)}"
                    results['errors'].append(error_msg)
            
            return results
            
        except Exception as e:
            results['errors'].append(f"Template creation failed: {str(e)}")
            return results
    
    def _sort_by_hierarchy(self, locations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort locations by hierarchy level for proper creation order."""
        type_order = {'house': 0, 'room': 1, 'container': 2, 'shelf': 3}
        
        return sorted(locations, key=lambda x: (
            type_order.get(x['type'], 999),
            0 if 'parent' not in x else 1  # Parents first within same type
        ))


def show_template_selector() -> Optional[LocationTemplate]:
    """Display template selection interface."""
    st.subheader("📋 Location Templates")
    st.markdown("Choose from predefined location structures to quickly set up common areas.")
    
    # Template selection
    template_options = ['None'] + list(LOCATION_TEMPLATES.keys())
    template_displays = ['None'] + [LOCATION_TEMPLATES[key].name for key in LOCATION_TEMPLATES.keys()]
    
    selected_display = st.selectbox(
        "Choose a template",
        template_displays,
        key="template_selector",
        help="Select a predefined template to create multiple locations at once"
    )
    
    if selected_display == 'None':
        return None
    
    # Find selected template
    selected_key = template_options[template_displays.index(selected_display)]
    template = LOCATION_TEMPLATES[selected_key]
    
    # Show template preview
    with st.expander(f"📋 Preview: {template.name}"):
        st.markdown(f"**Description:** {template.description}")
        st.markdown("**Locations to be created:**")
        
        for i, loc in enumerate(template.locations, 1):
            parent_text = f" (under {loc['parent']})" if 'parent' in loc else " (root level)"
            type_icon = {'house': '🏠', 'room': '🚪', 'container': '📦', 'shelf': '📚'}.get(loc['type'], '📍')
            
            st.write(f"{i}. {type_icon} **{loc['name']}** ({loc['type']}) {parent_text}")
            if loc.get('description'):
                st.write(f"   ↳ {loc['description']}")
    
    return template


def show_bulk_operations():
    """Display bulk operation interface."""
    st.subheader("🔄 Bulk Operations")
    
    bulk_tabs = st.tabs(["📋 Templates", "📄 CSV Import", "🗑️ Bulk Delete"])
    
    with bulk_tabs[0]:
        show_template_creation_interface()
    
    with bulk_tabs[1]:
        show_csv_import_interface()
    
    with bulk_tabs[2]:
        show_bulk_delete_interface()


def show_template_creation_interface():
    """Interface for creating locations from templates."""
    st.markdown("Create multiple related locations from predefined templates.")
    
    # Template selection
    template = show_template_selector()
    
    if template:
        # Parent location selection (optional)
        st.markdown("**Optional: Select Parent Location**")
        
        # Load available parent locations
        api_client = st.session_state.get('api_client')
        if api_client:
            try:
                parent_locations = api_client.get_locations(limit=100)
                parent_options = {"None (Create at root level)": None}
                
                for loc in parent_locations:
                    if loc.get('location_type') != 'shelf':  # Shelves can't have children
                        parent_options[f"{loc['name']} ({loc['full_path']})"] = loc['id']
                
                selected_parent_display = st.selectbox(
                    "Parent location",
                    list(parent_options.keys()),
                    help="Choose where to create the template structure"
                )
                
                selected_parent_id = parent_options[selected_parent_display]
                
                # Create button
                if st.button(f"✅ Create {template.name} Structure", type="primary"):
                    with st.spinner(f"Creating {template.name} structure..."):
                        creator = BulkLocationCreator(api_client)
                        results = creator.create_from_template(template, selected_parent_id)
                        
                        # Show results
                        if results['created']:
                            show_success(f"Successfully created {len(results['created'])} locations!")
                            
                            with st.expander("📋 Created Locations"):
                                for loc in results['created']:
                                    st.write(f"✅ {loc['name']} (ID: {loc['id']})")
                        
                        if results['errors']:
                            show_error(f"{len(results['errors'])} errors occurred during creation")
                            for error in results['errors']:
                                st.error(error)
                        
                        # Refresh page data
                        if results['created'] and not results['errors']:
                            st.rerun()
                
            except Exception as e:
                show_error("Failed to load parent locations", str(e))


def show_csv_import_interface():
    """Interface for CSV import of locations."""
    st.markdown("Import locations from a CSV file.")
    
    # CSV format help
    with st.expander("📄 CSV Format Requirements"):
        st.markdown("""
        **Required columns:**
        - `name`: Location name (required)
        - `type`: Location type (house, room, container, shelf)
        
        **Optional columns:**
        - `description`: Location description
        - `parent_name`: Name of parent location (must exist or be in same file)
        
        **Example CSV:**
        ```
        name,type,description,parent_name
        My House,house,Main residence,
        Living Room,room,Main living area,My House
        Coffee Table,container,Center table,Living Room
        Drawer,shelf,Table drawer,Coffee Table
        ```
        """)
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose CSV file",
        type=['csv'],
        key="bulk_csv_uploader",
        help="Upload a CSV file with location data"
    )
    
    if uploaded_file:
        try:
            import pandas as pd
            df = pd.read_csv(uploaded_file)
            
            # Validate CSV
            required_columns = ['name', 'type']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                show_error(f"Missing required columns: {missing_columns}")
                return
            
            # Show preview
            st.markdown("**Preview:**")
            st.dataframe(df.head(10), use_container_width=True)
            
            if len(df) > 10:
                st.info(f"Showing first 10 rows of {len(df)} total rows")
            
            # Import button (disabled until implementation)
            st.button("📥 Import Locations", type="primary", disabled=True, 
                     help="CSV import functionality will be available in a future update")
            st.info("💡 CSV import functionality coming soon! Use the Import/Export tab for current import options.")
        
        except Exception as e:
            show_error("Failed to read CSV file", str(e))


def show_bulk_delete_interface():
    """Interface for bulk deletion of locations."""
    st.markdown("⚠️ **Danger Zone:** Bulk delete operations")
    
    st.warning("Bulk deletion is a destructive operation that cannot be undone. Use with caution.")
    
    # Delete options
    delete_option = st.selectbox(
        "Delete option",
        [
            "Select specific locations",
            "Delete by type",
            "Delete by parent",
            "Delete by search pattern"
        ],
        key="bulk_delete_option",
        help="Choose how to select locations for deletion"
    )
    
    if delete_option == "Select specific locations":
        st.info("Individual location deletion is available on the main Locations page")
    
    elif delete_option == "Delete by type":
        location_type = st.selectbox(
            "Location type to delete",
            ['house', 'room', 'container', 'shelf'],
            key="delete_by_type_selector",
            help="All locations of this type will be deleted"
        )
        
        if st.button(f"🗑️ Delete All {location_type.title()} Locations", type="secondary"):
            st.error("Bulk delete functionality requires additional confirmation - coming soon!")
    
    else:
        st.info(f"Bulk delete by {delete_option.lower()} coming soon!")


def validate_template_compatibility(template: LocationTemplate, existing_locations: List[Dict[str, Any]]) -> List[str]:
    """Validate if template can be applied without conflicts."""
    warnings = []
    
    existing_names = {loc['name'] for loc in existing_locations}
    template_names = {loc['name'] for loc in template.locations}
    
    # Check for name conflicts
    conflicts = existing_names.intersection(template_names)
    if conflicts:
        warnings.append(f"Name conflicts detected: {', '.join(conflicts)}")
    
    # Check hierarchy consistency
    for loc in template.locations:
        if 'parent' in loc and loc['parent'] not in template_names:
            warnings.append(f"Parent '{loc['parent']}' for '{loc['name']}' not found in template")
    
    return warnings