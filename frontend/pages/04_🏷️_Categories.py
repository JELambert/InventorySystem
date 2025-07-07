"""
Categories page for the Home Inventory System.

Browse and view all inventory categories.
"""

import streamlit as st
import logging

from utils.api_client import APIClient
from components.auth import is_authenticated, show_logout_button
from components.keyboard_shortcuts import (
    enable_keyboard_shortcuts, show_keyboard_shortcuts_help
)
from components.category_management import browse_categories_section

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Categories - Home Inventory System",
    page_icon="🏷️",
    layout="wide"
)

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
    st.title("🏷️ Categories")
    st.markdown("Browse and explore your inventory categories")
    
    # Initialize API client
    api_client = APIClient()
    
    # Test API connection
    if not api_client.health_check():
        st.error("❌ Cannot connect to the API. Please check if the backend server is running.")
        st.stop()
    
    # Use the browse categories component
    browse_categories_section(api_client)
    
    # Keyboard shortcuts help
    with st.sidebar:
        st.divider()
        show_keyboard_shortcuts_help()

if __name__ == "__main__":
    main()