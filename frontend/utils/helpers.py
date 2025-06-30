"""
Helper utilities for the Streamlit frontend application.
"""

import streamlit as st
import pandas as pd
import logging
import re
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


def format_datetime(dt_string: str) -> str:
    """Format datetime string for display."""
    try:
        dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return dt_string


def validate_hex_color(color: str) -> bool:
    """Validate hex color format."""
    if not color:
        return True  # Optional field
    pattern = r'^#[0-9A-Fa-f]{6}$'
    return bool(re.match(pattern, color))


def show_error(message: str, details: Optional[str] = None):
    """Display an error message with optional details."""
    st.error(f"❌ {message}")
    if details and st.checkbox("Show details", key=f"error_details_{hash(message)}"):
        st.code(details)


def show_success(message: str):
    """Display a success message."""
    st.success(f"✅ {message}")


def show_warning(message: str):
    """Display a warning message."""
    st.warning(f"⚠️ {message}")


def show_info(message: str):
    """Display an info message."""
    st.info(f"ℹ️ {message}")


def safe_api_call(func: Callable, error_message: str = "API call failed") -> Any:
    """Safely execute an API call with error handling."""
    try:
        return func()
    except Exception as e:
        logger.error(f"{error_message}: {e}")
        show_error(error_message, str(e))
        return None


def create_category_display(category_id: Optional[int], categories: List[Dict[str, Any]]) -> str:
    """Create a category display string with visual indicators."""
    if not category_id or not categories:
        return "❌ No Category"
    
    for category in categories:
        if category['id'] == category_id:
            name = category.get('name', 'Unnamed')
            color = category.get('color', '#666666')
            return f"🏷️ {name}"
    
    return f"❓ Unknown Category (ID: {category_id})"

def create_location_dataframe(locations: List[Dict[str, Any]], categories: Optional[List[Dict[str, Any]]] = None) -> pd.DataFrame:
    """Convert location data to a pandas DataFrame for display with category support."""
    if not locations:
        return pd.DataFrame()
    
    # Create category lookup for quick access
    category_lookup = {}
    if categories:
        for cat in categories:
            category_lookup[cat['id']] = {
                'name': cat.get('name', 'Unnamed'),
                'color': cat.get('color', '#666666')
            }
    
    # Extract relevant fields
    data = []
    for loc in locations:
        # Get category information
        category_id = loc.get('category_id')
        category_display = create_category_display(category_id, categories or [])
        
        # Extract category name for sorting
        if category_id and categories:
            category_info = category_lookup.get(category_id)
            category_name = category_info['name'] if category_info else "Unknown Category"
        else:
            category_name = "No Category"
        
        data.append({
            'ID': loc.get('id'),
            'Name': loc.get('name'),
            'Type': loc.get('location_type', '').title(),
            'Category': category_display,
            'Category_Name': category_name,  # For sorting
            'Description': loc.get('description') or 'No description',
            'Full Path': loc.get('full_path'),
            'Depth': loc.get('depth', 0),
            'Created': format_datetime(loc.get('created_at', '')),
            'Updated': format_datetime(loc.get('updated_at', ''))
        })
    
    return pd.DataFrame(data)


def get_location_type_options() -> List[str]:
    """Get available location type options."""
    return ['house', 'room', 'container', 'shelf']


def get_location_type_display(location_type: str) -> str:
    """Get display name for location type."""
    type_map = {
        'house': '🏠 House',
        'room': '🚪 Room', 
        'container': '📦 Container',
        'shelf': '📚 Shelf'
    }
    return type_map.get(location_type, location_type.title())


def validate_location_form(name: str, location_type: str) -> List[str]:
    """Validate location form data and return list of errors."""
    errors = []
    
    if not name or not name.strip():
        errors.append("Location name is required")
    elif len(name.strip()) > 255:
        errors.append("Location name must be 255 characters or less")
    
    if not location_type:
        errors.append("Location type is required")
    elif location_type not in get_location_type_options():
        errors.append("Invalid location type")
    
    return errors


def handle_api_error(error: Exception, operation: str = "operation") -> bool:
    """Handle API errors with user-friendly messages."""
    from utils.api_client import APIError
    
    if isinstance(error, APIError):
        if error.status_code == 404:
            show_error(f"Not found - The requested resource could not be found")
        elif error.status_code == 400:
            show_error(f"Invalid request - {error.message}")
        elif error.status_code >= 500:
            show_error(f"Server error - Please try again later")
        else:
            show_error(f"API error - {error.message}")
        
        return False
    else:
        show_error(f"Failed to {operation} - {str(error)}")
        return False


def create_data_editor_config() -> Dict[str, Any]:
    """Create configuration for st.data_editor."""
    return {
        "ID": st.column_config.NumberColumn("ID", disabled=True),
        "Name": st.column_config.TextColumn("Name", max_chars=255),
        "Type": st.column_config.SelectboxColumn(
            "Type", 
            options=['House', 'Room', 'Container', 'Shelf']
        ),
        "Description": st.column_config.TextColumn("Description", max_chars=500),
        "Full Path": st.column_config.TextColumn("Full Path", disabled=True),
        "Depth": st.column_config.NumberColumn("Depth", disabled=True),
        "Created": st.column_config.DatetimeColumn("Created", disabled=True),
        "Updated": st.column_config.DatetimeColumn("Updated", disabled=True)
    }


class SessionManager:
    """Manage Streamlit session state for the application."""
    
    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """Get a value from session state."""
        return st.session_state.get(key, default)
    
    @staticmethod
    def set(key: str, value: Any) -> None:
        """Set a value in session state."""
        st.session_state[key] = value
    
    @staticmethod
    def clear(key: str) -> None:
        """Clear a value from session state."""
        if key in st.session_state:
            del st.session_state[key]
    
    @staticmethod
    def has(key: str) -> bool:
        """Check if a key exists in session state."""
        return key in st.session_state
    
    @staticmethod
    def get_or_create(key: str, factory: Callable) -> Any:
        """Get a value from session state or create it with factory function."""
        if key not in st.session_state:
            st.session_state[key] = factory()
        return st.session_state[key]