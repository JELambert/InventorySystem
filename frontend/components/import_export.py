"""
Import/Export functionality for the Home Inventory System.

This module provides comprehensive data import and export capabilities
for location data, including CSV, JSON, and backup functionality.
"""

import streamlit as st
import pandas as pd
import json
import csv
import io
import zipfile
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import logging

from utils.api_client import APIClient, APIError
from utils.helpers import show_error, show_success, show_warning, handle_api_error

logger = logging.getLogger(__name__)

class DataValidator:
    """Validate imported data for consistency and correctness."""
    
    REQUIRED_FIELDS = ['name', 'location_type']
    OPTIONAL_FIELDS = ['description', 'parent_name', 'parent_id']
    VALID_TYPES = ['house', 'room', 'container', 'shelf']
    
    @classmethod
    def validate_csv_data(cls, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Validate CSV data structure and content."""
        errors = []
        
        # Check required columns
        missing_columns = [col for col in cls.REQUIRED_FIELDS if col not in df.columns]
        if missing_columns:
            errors.append(f"Missing required columns: {', '.join(missing_columns)}")
        
        # Check for empty names
        if 'name' in df.columns:
            empty_names = df[df['name'].isna() | (df['name'] == '')].index.tolist()
            if empty_names:
                errors.append(f"Empty names found in rows: {', '.join(map(str, empty_names))}")
        
        # Validate location types
        if 'location_type' in df.columns:
            invalid_types = df[~df['location_type'].isin(cls.VALID_TYPES)]['location_type'].unique()
            if len(invalid_types) > 0:
                errors.append(f"Invalid location types: {', '.join(invalid_types)}. Valid types: {', '.join(cls.VALID_TYPES)}")
        
        # Check for duplicate names
        if 'name' in df.columns:
            duplicates = df[df.duplicated(['name'], keep=False)]['name'].unique()
            if len(duplicates) > 0:
                errors.append(f"Duplicate location names: {', '.join(duplicates)}")
        
        # Validate hierarchy relationships
        if 'parent_name' in df.columns:
            parent_names = df['parent_name'].dropna().unique()
            all_names = df['name'].unique()
            missing_parents = [p for p in parent_names if p not in all_names and p != '']
            if missing_parents:
                errors.append(f"Parent locations not found in data: {', '.join(missing_parents)}")
        
        return len(errors) == 0, errors
    
    @classmethod
    def validate_json_data(cls, data: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """Validate JSON data structure and content."""
        errors = []
        
        if not isinstance(data, list):
            errors.append("JSON data must be a list of location objects")
            return False, errors
        
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                errors.append(f"Item {i} is not a valid object")
                continue
            
            # Check required fields
            for field in cls.REQUIRED_FIELDS:
                if field not in item or not item[field]:
                    errors.append(f"Item {i}: Missing or empty required field '{field}'")
            
            # Validate location type
            if 'location_type' in item and item['location_type'] not in cls.VALID_TYPES:
                errors.append(f"Item {i}: Invalid location type '{item['location_type']}'")
        
        return len(errors) == 0, errors

class LocationExporter:
    """Export location data in various formats."""
    
    def __init__(self, api_client: APIClient):
        self.api_client = api_client
    
    def export_to_csv(self, locations: List[Dict[str, Any]]) -> str:
        """Export locations to CSV format."""
        if not locations:
            return ""
        
        # Prepare data for CSV
        csv_data = []
        for loc in locations:
            csv_data.append({
                'id': loc.get('id'),
                'name': loc.get('name'),
                'description': loc.get('description', ''),
                'location_type': loc.get('location_type'),
                'parent_id': loc.get('parent_id'),
                'full_path': loc.get('full_path'),
                'depth': loc.get('depth'),
                'created_at': loc.get('created_at'),
                'updated_at': loc.get('updated_at')
            })
        
        df = pd.DataFrame(csv_data)
        
        # Convert to CSV string
        output = io.StringIO()
        df.to_csv(output, index=False)
        return output.getvalue()
    
    def export_to_json(self, locations: List[Dict[str, Any]]) -> str:
        """Export locations to JSON format."""
        export_data = {
            'export_metadata': {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'version': '1.0',
                'total_locations': len(locations)
            },
            'locations': locations
        }
        
        return json.dumps(export_data, indent=2, default=str)
    
    def create_backup_archive(self, locations: List[Dict[str, Any]]) -> bytes:
        """Create a complete backup archive with multiple formats."""
        
        # Create ZIP archive
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add CSV export
            csv_data = self.export_to_csv(locations)
            zip_file.writestr('locations.csv', csv_data)
            
            # Add JSON export
            json_data = self.export_to_json(locations)
            zip_file.writestr('locations.json', json_data)
            
            # Add metadata
            metadata = {
                'backup_created': datetime.now(timezone.utc).isoformat(),
                'total_locations': len(locations),
                'formats_included': ['csv', 'json'],
                'system_info': {
                    'version': '1.0',
                    'export_source': 'Home Inventory System Frontend'
                }
            }
            zip_file.writestr('backup_metadata.json', json.dumps(metadata, indent=2))
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()

class LocationImporter:
    """Import location data from various formats."""
    
    def __init__(self, api_client: APIClient):
        self.api_client = api_client
    
    def import_from_csv(self, csv_content: str) -> Dict[str, Any]:
        """Import locations from CSV content."""
        try:
            # Parse CSV
            csv_io = io.StringIO(csv_content)
            df = pd.read_csv(csv_io)
            
            # Validate data
            is_valid, errors = DataValidator.validate_csv_data(df)
            if not is_valid:
                return {'success': False, 'errors': errors}
            
            # Convert to location objects
            locations = []
            for _, row in df.iterrows():
                location = {
                    'name': row['name'],
                    'location_type': row['location_type'],
                    'description': row.get('description', ''),
                }
                
                # Handle parent reference
                if 'parent_id' in row and pd.notna(row['parent_id']):
                    location['parent_id'] = int(row['parent_id'])
                elif 'parent_name' in row and pd.notna(row['parent_name']) and row['parent_name']:
                    # We'll resolve parent names later
                    location['parent_name'] = row['parent_name']
                
                locations.append(location)
            
            # Import the locations
            return self._import_locations(locations)
            
        except Exception as e:
            logger.error(f"CSV import failed: {e}")
            return {'success': False, 'errors': [f"CSV parsing failed: {str(e)}"]}
    
    def import_from_json(self, json_content: str) -> Dict[str, Any]:
        """Import locations from JSON content."""
        try:
            # Parse JSON
            data = json.loads(json_content)
            
            # Handle backup format
            if 'locations' in data:
                locations = data['locations']
            else:
                locations = data
            
            # Validate data
            is_valid, errors = DataValidator.validate_json_data(locations)
            if not is_valid:
                return {'success': False, 'errors': errors}
            
            # Import the locations
            return self._import_locations(locations)
            
        except json.JSONDecodeError as e:
            return {'success': False, 'errors': [f"Invalid JSON format: {str(e)}"]}
        except Exception as e:
            logger.error(f"JSON import failed: {e}")
            return {'success': False, 'errors': [f"JSON import failed: {str(e)}"]}
    
    def _import_locations(self, locations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Import a list of validated location objects."""
        results = {
            'success': True,
            'created': [],
            'errors': [],
            'name_map': {}  # Maps imported names to created IDs
        }
        
        try:
            # Sort by hierarchy (houses first, then rooms, etc.)
            sorted_locations = self._sort_by_hierarchy(locations)
            
            for loc_data in sorted_locations:
                try:
                    # Resolve parent ID if parent_name is specified
                    if 'parent_name' in loc_data and loc_data['parent_name']:
                        parent_name = loc_data['parent_name']
                        if parent_name in results['name_map']:
                            loc_data['parent_id'] = results['name_map'][parent_name]
                        else:
                            # Try to find existing parent
                            existing_parents = self.api_client.search_locations({'pattern': parent_name})
                            if existing_parents:
                                # Use first match
                                loc_data['parent_id'] = existing_parents[0]['id']
                            else:
                                results['errors'].append(f"Parent '{parent_name}' not found for '{loc_data['name']}'")
                                continue
                        
                        # Remove parent_name from the data
                        del loc_data['parent_name']
                    
                    # Create the location
                    created_location = self.api_client.create_location(loc_data)
                    results['created'].append(created_location)
                    results['name_map'][loc_data['name']] = created_location['id']
                    
                except APIError as e:
                    error_msg = f"Failed to create '{loc_data['name']}': {e.message}"
                    results['errors'].append(error_msg)
                except Exception as e:
                    error_msg = f"Failed to create '{loc_data['name']}': {str(e)}"
                    results['errors'].append(error_msg)
            
            # Determine overall success
            results['success'] = len(results['created']) > 0
            
            return results
            
        except Exception as e:
            logger.error(f"Import process failed: {e}")
            return {
                'success': False,
                'errors': [f"Import process failed: {str(e)}"],
                'created': [],
                'name_map': {}
            }
    
    def _sort_by_hierarchy(self, locations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort locations by hierarchy level for proper creation order."""
        type_order = {'house': 0, 'room': 1, 'container': 2, 'shelf': 3}
        
        return sorted(locations, key=lambda x: (
            type_order.get(x.get('location_type', ''), 999),
            0 if 'parent_id' not in x and 'parent_name' not in x else 1
        ))

def show_export_interface():
    """Display export functionality interface."""
    st.subheader("📤 Export Data")
    st.markdown("Export your location data in various formats for backup or analysis.")
    
    # Get API client
    api_client = st.session_state.get('api_client')
    if not api_client:
        st.error("API client not available")
        return
    
    # Export format selection
    export_format = st.selectbox(
        "Export Format",
        ["CSV", "JSON", "Complete Backup (ZIP)"],
        key="export_format_selector",
        help="Choose the format for your data export"
    )
    
    # Export scope
    st.markdown("**Export Scope:**")
    export_scope = st.radio(
        "What to export",
        ["All Locations", "Filtered Locations"],
        key="export_scope_radio",
        help="Choose whether to export all data or apply filters"
    )
    
    # Filter options for filtered export
    if export_scope == "Filtered Locations":
        with st.expander("🔍 Export Filters"):
            filter_type = st.selectbox(
                "Filter by type",
                ["All Types", "house", "room", "container", "shelf"]
            )
            
            filter_parent = st.text_input(
                "Filter by parent name (optional)",
                help="Export only locations under this parent"
            )
    
    # Export button
    if st.button("📥 Export Data", type="primary", key="export_data_button"):
        with st.spinner("Preparing export..."):
            try:
                # Get locations based on scope
                if export_scope == "All Locations":
                    locations = api_client.get_locations(limit=10000)  # Large limit for all
                else:
                    # Apply filters
                    search_params = {}
                    if filter_type != "All Types":
                        search_params['location_type'] = filter_type
                    
                    if filter_parent:
                        search_params['pattern'] = filter_parent
                    
                    if search_params:
                        locations = api_client.search_locations(search_params)
                    else:
                        locations = api_client.get_locations(limit=10000)
                
                if not locations:
                    st.warning("No locations found to export")
                    return
                
                # Create exporter
                exporter = LocationExporter(api_client)
                
                # Generate export based on format
                if export_format == "CSV":
                    export_data = exporter.export_to_csv(locations)
                    filename = f"locations_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    mime_type = "text/csv"
                    
                elif export_format == "JSON":
                    export_data = exporter.export_to_json(locations)
                    filename = f"locations_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    mime_type = "application/json"
                    
                else:  # Complete Backup
                    export_data = exporter.create_backup_archive(locations)
                    filename = f"locations_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                    mime_type = "application/zip"
                
                # Provide download
                st.download_button(
                    label=f"💾 Download {export_format}",
                    data=export_data,
                    file_name=filename,
                    mime=mime_type,
                    use_container_width=True
                )
                
                show_success(f"Export prepared successfully! {len(locations)} locations included.")
                
            except Exception as e:
                handle_api_error(e, "export data")

def show_import_interface():
    """Display import functionality interface."""
    st.subheader("📥 Import Data")
    st.markdown("Import location data from CSV or JSON files.")
    
    # Get API client
    api_client = st.session_state.get('api_client')
    if not api_client:
        st.error("API client not available")
        return
    
    # Import format selection
    import_format = st.selectbox(
        "Import Format",
        ["CSV", "JSON"],
        key="import_format_selector",
        help="Choose the format of your import file"
    )
    
    # Show format requirements
    with st.expander(f"📋 {import_format} Format Requirements"):
        if import_format == "CSV":
            st.markdown("""
            **Required columns:**
            - `name`: Location name (required)
            - `location_type`: Type (house, room, container, shelf)
            
            **Optional columns:**
            - `description`: Location description
            - `parent_name`: Name of parent location
            - `parent_id`: ID of parent location
            
            **Example CSV:**
            ```
            name,location_type,description,parent_name
            My House,house,Main residence,
            Living Room,room,Main living area,My House
            Coffee Table,container,Center table,Living Room
            Drawer,shelf,Table drawer,Coffee Table
            ```
            """)
        else:  # JSON
            st.markdown("""
            **JSON Format:**
            Array of location objects with required fields:
            - `name`: Location name (required)
            - `location_type`: Type (house, room, container, shelf)
            
            **Optional fields:**
            - `description`: Location description
            - `parent_name`: Name of parent location
            - `parent_id`: ID of parent location
            
            **Example JSON:**
            ```json
            [
                {
                    "name": "My House",
                    "location_type": "house",
                    "description": "Main residence"
                },
                {
                    "name": "Living Room",
                    "location_type": "room",
                    "description": "Main living area",
                    "parent_name": "My House"
                }
            ]
            ```
            """)
    
    # File upload
    uploaded_file = st.file_uploader(
        f"Choose {import_format} file",
        type=[import_format.lower()],
        key=f"import_{import_format.lower()}_uploader",
        help=f"Upload a {import_format} file with location data"
    )
    
    if uploaded_file:
        try:
            # Read file content
            if import_format == "CSV":
                content = uploaded_file.getvalue().decode('utf-8')
            else:
                content = uploaded_file.getvalue().decode('utf-8')
            
            # Show preview
            st.markdown("**Preview:**")
            
            if import_format == "CSV":
                try:
                    df = pd.read_csv(io.StringIO(content))
                    st.dataframe(df.head(10), use_container_width=True)
                    if len(df) > 10:
                        st.info(f"Showing first 10 rows of {len(df)} total rows")
                except Exception as e:
                    st.error(f"Failed to parse CSV: {e}")
                    return
            else:
                try:
                    data = json.loads(content)
                    if isinstance(data, dict) and 'locations' in data:
                        data = data['locations']
                    st.json(data[:3] if len(data) > 3 else data)
                    if len(data) > 3:
                        st.info(f"Showing first 3 items of {len(data)} total items")
                except Exception as e:
                    st.error(f"Failed to parse JSON: {e}")
                    return
            
            # Import options
            st.markdown("**Import Options:**")
            
            col1, col2 = st.columns(2)
            with col1:
                validate_only = st.checkbox(
                    "Validate only (don't import)",
                    key="validate_only_checkbox",
                    help="Check data format without actually importing"
                )
            
            with col2:
                confirm_import = st.checkbox(
                    "I understand this will create new locations",
                    key="confirm_import_checkbox",
                    help="Confirm you want to proceed with the import"
                )
            
            # Import button
            if st.button("🚀 Import Data", type="primary", key="import_data_button", disabled=not (confirm_import or validate_only)):
                with st.spinner("Processing import..."):
                    # Create importer
                    importer = LocationImporter(api_client)
                    
                    if validate_only:
                        # Validation only
                        if import_format == "CSV":
                            df = pd.read_csv(io.StringIO(content))
                            is_valid, errors = DataValidator.validate_csv_data(df)
                        else:
                            data = json.loads(content)
                            if isinstance(data, dict) and 'locations' in data:
                                data = data['locations']
                            is_valid, errors = DataValidator.validate_json_data(data)
                        
                        if is_valid:
                            show_success("✅ Data validation passed! File is ready for import.")
                        else:
                            show_error("❌ Data validation failed:")
                            for error in errors:
                                st.error(f"• {error}")
                    
                    else:
                        # Actual import
                        if import_format == "CSV":
                            result = importer.import_from_csv(content)
                        else:
                            result = importer.import_from_json(content)
                        
                        # Show results
                        if result['success']:
                            show_success(f"Import completed! Created {len(result['created'])} locations.")
                            
                            if result['created']:
                                with st.expander("📋 Created Locations"):
                                    for loc in result['created']:
                                        st.write(f"✅ {loc['name']} (ID: {loc['id']})")
                        
                        if result['errors']:
                            show_warning(f"{len(result['errors'])} errors occurred during import:")
                            for error in result['errors']:
                                st.error(f"• {error}")
                        
                        # Refresh page if locations were created
                        if result['created']:
                            st.balloons()
                            if st.button("🔄 Refresh to see changes", key="refresh_after_import"):
                                st.rerun()
        
        except Exception as e:
            show_error("Failed to process file", str(e))

def show_import_export_interface():
    """Main import/export interface."""
    st.markdown("---")
    st.subheader("🔄 Data Import/Export")
    st.markdown("Manage your location data with import and export capabilities.")
    
    # Tab interface
    import_tab, export_tab = st.tabs(["📥 Import", "📤 Export"])
    
    with import_tab:
        show_import_interface()
    
    with export_tab:
        show_export_interface()