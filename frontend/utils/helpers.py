"""
Helper utilities for the Streamlit frontend application.
"""

import streamlit as st
import pandas as pd
import logging
import re
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from contextlib import contextmanager

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


def safe_float_format(value: Any, default: float = 0.0, format_str: str = ".2f") -> str:
    """Safely convert and format numeric values from API responses.
    
    Args:
        value: Value to convert (could be string, int, float, None, etc.)
        default: Default value if conversion fails
        format_str: Format string for the float (e.g., ".2f", ",.2f")
    
    Returns:
        Formatted string representation of the numeric value
    """
    try:
        if value is None:
            numeric_value = default
        elif isinstance(value, str):
            # Handle empty strings using safe_strip
            stripped = safe_strip(value)
            if not stripped:
                numeric_value = default
            else:
                numeric_value = float(stripped)
        elif isinstance(value, (int, float)):
            numeric_value = float(value)
        else:
            # For any other type, try to convert
            numeric_value = float(value)
    except (ValueError, TypeError):
        logger.warning(f"Could not convert value '{value}' to float, using default {default}")
        numeric_value = default
    
    try:
        return f"{numeric_value:{format_str}}"
    except ValueError:
        # If format string is invalid, use basic float formatting
        return f"{numeric_value:.2f}"


def safe_currency_format(value: Any, currency: str = "$", default: float = 0.0) -> str:
    """Safely format monetary values with currency symbol.
    
    Args:
        value: Monetary value to format
        currency: Currency symbol (default: $)
        default: Default value if conversion fails
        
    Returns:
        Formatted currency string (e.g., "$1,234.56")
    """
    formatted_value = safe_float_format(value, default, ",.2f")
    return f"{currency}{formatted_value}"


def safe_int_convert(value: Any, default: int = 0) -> int:
    """Safely convert values to integers.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Integer value
    """
    try:
        if value is None:
            return default
        elif isinstance(value, str):
            if not safe_strip(value):
                return default
            # Handle string numbers that might be floats
            return int(float(value))
        elif isinstance(value, (int, float)):
            return int(value)
        else:
            return int(value)
    except (ValueError, TypeError):
        logger.warning(f"Could not convert value '{value}' to int, using default {default}")
        return default


def safe_strip(value: Any) -> str:
    """Safely strip string values, handling None and non-string types.
    
    Args:
        value: Value to strip (can be None, string, or other types)
        
    Returns:
        Stripped string or empty string if None/invalid
    """
    if value is None:
        return ""
    try:
        return str(value).strip()
    except (AttributeError, TypeError):
        return ""


def safe_string_check(value: Any) -> bool:
    """Check if a value contains meaningful string content after stripping.
    
    Args:
        value: Value to check
        
    Returns:
        True if value has content after stripping, False otherwise
    """
    stripped = safe_strip(value)
    return bool(stripped)


def safe_string_or_none(value: Any) -> Optional[str]:
    """Convert value to stripped string or None if empty.
    
    Args:
        value: Value to convert
        
    Returns:
        Stripped string if has content, None if empty/None
    """
    stripped = safe_strip(value)
    return stripped if stripped else None


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
    
    stripped_name = safe_strip(name)
    if not stripped_name:
        errors.append("Location name is required")
    elif len(stripped_name) > 255:
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
    """Enhanced session state management for the application."""
    
    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """Get a value from session state safely."""
        return safe_session_state_access(key, default)
    
    @staticmethod
    def set(key: str, value: Any) -> None:
        """Set a value in session state."""
        try:
            st.session_state[key] = value
        except Exception as e:
            logger.error(f"Failed to set session state key {key}: {e}")
    
    @staticmethod
    def clear(key: str) -> None:
        """Clear a value from session state safely."""
        try:
            if key in st.session_state:
                del st.session_state[key]
        except Exception as e:
            logger.error(f"Failed to clear session state key {key}: {e}")
    
    @staticmethod
    def has(key: str) -> bool:
        """Check if a key exists in session state safely."""
        try:
            return key in st.session_state
        except Exception as e:
            logger.error(f"Failed to check session state key {key}: {e}")
            return False
    
    @staticmethod
    def backup_session_state() -> Dict[str, Any]:
        """Create a backup of current session state."""
        try:
            return dict(st.session_state)
        except Exception as e:
            logger.error(f"Failed to backup session state: {e}")
            return {}
    
    @staticmethod
    def restore_session_state(backup: Dict[str, Any]) -> bool:
        """Restore session state from backup."""
        try:
            # Clear current state
            for key in list(st.session_state.keys()):
                if not key.startswith('_'):  # Keep internal streamlit keys
                    del st.session_state[key]
            
            # Restore from backup
            for key, value in backup.items():
                st.session_state[key] = value
            
            return True
        except Exception as e:
            logger.error(f"Failed to restore session state: {e}")
            return False
    
    @staticmethod
    def get_session_stats() -> Dict[str, Any]:
        """Get session state statistics."""
        try:
            total_keys = len(st.session_state.keys())
            temp_keys = len([k for k in st.session_state.keys() if k.startswith('temp_')])
            cache_keys = len([k for k in st.session_state.keys() if k.endswith('_cache')])
            
            return {
                "total_keys": total_keys,
                "temporary_keys": temp_keys,
                "cache_keys": cache_keys,
                "application_keys": total_keys - temp_keys - cache_keys
            }
        except Exception as e:
            logger.error(f"Failed to get session stats: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def get_or_create(key: str, factory: Callable) -> Any:
        """Get a value from session state or create it with factory function."""
        if key not in st.session_state:
            st.session_state[key] = factory()
        return st.session_state[key]


def safe_operation_with_feedback(
    operation_func: Callable, 
    operation_name: str,
    success_message: Optional[str] = None,
    error_message: Optional[str] = None,
    loading_message: Optional[str] = None,
    show_progress: bool = False
) -> Any:
    """
    Execute an operation with comprehensive user feedback.
    
    Args:
        operation_func: Function to execute
        operation_name: Name of the operation for messaging
        success_message: Custom success message
        error_message: Custom error message
        loading_message: Custom loading message
        show_progress: Whether to show progress indicator
        
    Returns:
        Result of operation_func or None if failed
    """
    loading_msg = loading_message or f"Performing {operation_name}..."
    success_msg = success_message or f"{operation_name} completed successfully"
    error_msg = error_message or f"Failed to {operation_name.lower()}"
    
    if show_progress:
        with st.spinner(loading_msg):
            try:
                result = operation_func()
                st.success(success_msg)
                return result
            except Exception as e:
                logger.error(f"Operation {operation_name} failed: {e}")
                show_error(error_msg, str(e))
                return None
    else:
        try:
            result = operation_func()
            st.success(success_msg)
            return result
        except Exception as e:
            logger.error(f"Operation {operation_name} failed: {e}")
            show_error(error_msg, str(e))
            return None


def safe_session_state_access(key: str, default: Any = None, 
                             validator: Optional[Callable] = None) -> Any:
    """
    Safely access session state with validation and defaults.
    
    Args:
        key: Session state key
        default: Default value if key doesn't exist
        validator: Optional validation function
        
    Returns:
        Session state value or default
    """
    try:
        if key not in st.session_state:
            return default
        
        value = st.session_state[key]
        
        # Apply validator if provided
        if validator and not validator(value):
            logger.warning(f"Session state validation failed for key {key}, using default")
            return default
        
        return value
    except Exception as e:
        logger.error(f"Error accessing session state key {key}: {e}")
        return default


def format_error_for_user(error: Exception) -> str:
    """
    Format error message for user display.
    
    Args:
        error: Exception to format
        
    Returns:
        User-friendly error message
    """
    from utils.api_client import APIError
    
    if isinstance(error, APIError):
        if error.status_code == 404:
            return "The requested item was not found"
        elif error.status_code == 403:
            return "You don't have permission to perform this action"
        elif error.status_code == 400:
            return "Invalid request. Please check your input"
        elif error.status_code >= 500:
            return "Server error. Please try again later"
        else:
            return error.message
    elif isinstance(error, ConnectionError):
        return "Unable to connect to the server. Please check your internet connection"
    elif isinstance(error, TimeoutError):
        return "The request timed out. Please try again"
    elif isinstance(error, (ValueError, TypeError)):
        return "Invalid data provided. Please check your input"
    else:
        return "An unexpected error occurred. Please try again"


def create_confirmation_dialog(
    title: str,
    message: str,
    confirm_text: str = "Confirm",
    cancel_text: str = "Cancel",
    danger: bool = False
) -> Optional[bool]:
    """
    Create a confirmation dialog using Streamlit.
    
    Args:
        title: Dialog title
        message: Confirmation message
        confirm_text: Text for confirm button
        cancel_text: Text for cancel button
        danger: Whether this is a dangerous action
        
    Returns:
        True if confirmed, False if cancelled, None if no action taken
    """
    st.markdown(f"### {title}")
    st.write(message)
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if danger:
            confirm_clicked = st.button(f"⚠️ {confirm_text}", type="primary")
        else:
            confirm_clicked = st.button(f"✅ {confirm_text}", type="primary")
    
    with col2:
        cancel_clicked = st.button(f"❌ {cancel_text}")
    
    if confirm_clicked:
        return True
    elif cancel_clicked:
        return False
    else:
        return None


def format_bytes(bytes_value: int) -> str:
    """
    Format bytes into human-readable format.
    
    Args:
        bytes_value: Number of bytes
        
    Returns:
        Formatted string (e.g., "1.2 MB")
    """
    try:
        if bytes_value == 0:
            return "0 B"
        
        sizes = ['B', 'KB', 'MB', 'GB', 'TB']
        i = 0
        while bytes_value >= 1024 and i < len(sizes) - 1:
            bytes_value /= 1024.0
            i += 1
        
        return f"{bytes_value:.1f} {sizes[i]}"
    except (TypeError, ValueError):
        return "Unknown"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to specified length with suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum length before truncation
        suffix: Suffix to add when truncated
        
    Returns:
        Truncated text with suffix if needed
    """
    try:
        text = safe_strip(text)
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix
    except (TypeError, AttributeError):
        return ""


def generate_unique_key(prefix: str = "key", suffix: str = "") -> str:
    """
    Generate a unique key for Streamlit widgets.
    
    Args:
        prefix: Key prefix
        suffix: Key suffix
        
    Returns:
        Unique key string
    """
    import time
    import random
    
    timestamp = str(int(time.time() * 1000))
    random_part = str(random.randint(1000, 9999))
    
    parts = [prefix, timestamp, random_part]
    if suffix:
        parts.append(suffix)
    
    return "_".join(parts)


@contextmanager
def loading_state(message: str = "Loading...", min_duration: float = 0.5):
    """
    Context manager for showing loading state with minimum duration.
    
    Args:
        message: Loading message to display
        min_duration: Minimum duration to show loading (prevents flickering)
    """
    import time
    start_time = time.time()
    
    with st.spinner(message):
        try:
            yield
        finally:
            # Ensure minimum loading duration to prevent flickering
            elapsed = time.time() - start_time
            if elapsed < min_duration:
                time.sleep(min_duration - elapsed)


def retry_operation(
    operation_func: Callable,
    max_retries: int = 3,
    delay: float = 1.0,
    exponential_backoff: bool = True,
    retry_on_exceptions: tuple = (ConnectionError, TimeoutError)
) -> Any:
    """
    Retry an operation with configurable retry logic.
    
    Args:
        operation_func: Function to retry
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries
        exponential_backoff: Whether to use exponential backoff
        retry_on_exceptions: Tuple of exceptions to retry on
        
    Returns:
        Result of operation_func
        
    Raises:
        Last exception if all retries fail
    """
    import time
    
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return operation_func()
        except retry_on_exceptions as e:
            last_exception = e
            
            if attempt < max_retries:
                wait_time = delay
                if exponential_backoff:
                    wait_time = delay * (2 ** attempt)
                
                logger.info(f"Retry attempt {attempt + 1}/{max_retries} after {wait_time}s")
                time.sleep(wait_time)
            else:
                logger.error(f"All {max_retries} retry attempts failed")
                break
        except Exception as e:
            # Don't retry on other exceptions
            logger.error(f"Non-retryable exception: {e}")
            raise e
    
    # Re-raise the last exception if all retries failed
    if last_exception:
        raise last_exception


def safe_json_loads(json_string: str, default: Any = None) -> Any:
    """
    Safely parse JSON string with fallback.
    
    Args:
        json_string: JSON string to parse
        default: Default value if parsing fails
        
    Returns:
        Parsed JSON or default value
    """
    import json
    
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.warning(f"Failed to parse JSON: {e}")
        return default


def safe_list_access(lst: List[Any], index: int, default: Any = None) -> Any:
    """
    Safely access list element by index.
    
    Args:
        lst: List to access
        index: Index to access
        default: Default value if index is out of bounds
        
    Returns:
        List element or default value
    """
    try:
        if lst and 0 <= index < len(lst):
            return lst[index]
        return default
    except (TypeError, IndexError):
        return default


def safe_dict_access(dictionary: Dict[str, Any], key: str, default: Any = None) -> Any:
    """
    Safely access dictionary value with nested key support.
    
    Args:
        dictionary: Dictionary to access
        key: Key to access (supports nested keys with dot notation)
        default: Default value if key doesn't exist
        
    Returns:
        Dictionary value or default
    """
    try:
        if not isinstance(dictionary, dict):
            return default
        
        # Support nested key access with dot notation
        if '.' in key:
            keys = key.split('.')
            value = dictionary
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return value
        else:
            return dictionary.get(key, default)
    except (TypeError, AttributeError):
        return default