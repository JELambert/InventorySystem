"""
Home Inventory System - Streamlit Frontend Application

Main application entry point for the web-based inventory management system.
"""

import streamlit as st
import logging
from utils.config import AppConfig
from utils.api_client import APIClient
from components.performance import enable_performance_monitoring, show_cache_management
from components.keyboard_shortcuts import enable_keyboard_shortcuts, show_keyboard_shortcuts_help
from components.auth import show_login_page, show_logout_button, is_authenticated

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Home Inventory System",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/inventory-system/help',
        'Report a bug': 'https://github.com/inventory-system/issues',
        'About': "# Home Inventory System\nA comprehensive inventory management system for your home."
    }
)

# Initialize session state
if 'api_client' not in st.session_state:
    st.session_state.api_client = APIClient()

if 'connection_status' not in st.session_state:
    st.session_state.connection_status = None

def check_api_connection():
    """Check API connectivity and update session state."""
    try:
        is_connected = st.session_state.api_client.health_check()
        st.session_state.connection_status = "connected" if is_connected else "disconnected"
        return is_connected
    except Exception as e:
        logger.error(f"API connection check failed: {e}")
        st.session_state.connection_status = "error"
        return False

def show_connection_status():
    """Display API connection status in sidebar."""
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔗 System Status")
    
    if st.sidebar.button("🔄 Check Connection"):
        with st.spinner("Checking API connection..."):
            check_api_connection()
    
    status = st.session_state.connection_status
    if status == "connected":
        st.sidebar.success("✅ API Connected")
    elif status == "disconnected":
        st.sidebar.error("❌ API Disconnected")
    elif status == "error":
        st.sidebar.error("⚠️ Connection Error")
    else:
        st.sidebar.info("❓ Status Unknown")

def main():
    """Main application function."""
    # Check authentication first
    if not is_authenticated():
        show_login_page()
        return
    
    # Header
    st.title("🏠 Home Inventory System")
    st.markdown("Welcome to your comprehensive home inventory management system.")
    
    # Enable keyboard shortcuts
    enable_keyboard_shortcuts()
    
    # Sidebar navigation
    st.sidebar.title("📋 Navigation")
    
    # Show logout button and user info
    show_logout_button()
    
    # Show keyboard shortcuts help
    show_keyboard_shortcuts_help()
    
    # Show performance monitoring
    enable_performance_monitoring()
    
    # Show cache management
    show_cache_management()
    
    # Show connection status
    show_connection_status()
    
    # Main content area
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        ## 🎯 Quick Start
        
        Use the navigation in the sidebar to access different features:
        
        ### 📊 Dashboard
        View system overview, statistics, and recent activity.
        
        ### 📍 Locations
        Browse, search, and filter all your inventory locations.
        
        ### ⚙️ Manage
        Create, edit, and delete locations in your inventory system.
        """)
        
        # Quick stats if API is available
        if st.session_state.connection_status == "connected":
            try:
                with st.spinner("Loading system statistics..."):
                    stats = st.session_state.api_client.get_location_stats()
                    
                if stats:
                    st.markdown("### 📈 Quick Stats")
                    stat_col1, stat_col2, stat_col3 = st.columns(3)
                    
                    with stat_col1:
                        st.metric(
                            "Total Locations", 
                            stats.get('total_locations', 0)
                        )
                    
                    with stat_col2:
                        st.metric(
                            "Root Locations",
                            stats.get('root_locations', 0)
                        )
                    
                    with stat_col3:
                        houses = stats.get('by_type', {}).get('house', 0)
                        st.metric("Houses", houses)
                        
            except Exception as e:
                logger.error(f"Failed to load quick stats: {e}")
                st.warning("⚠️ Unable to load system statistics")
        
        else:
            st.warning("🔌 Connect to the API to view system statistics")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <small>Home Inventory System v1.0 | Built with Streamlit</small>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()