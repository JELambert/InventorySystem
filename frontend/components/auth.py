"""
Authentication components for the Home Inventory System.

This module provides authentication functionality using streamlit-authenticator.
"""

import streamlit as st
import yaml
import streamlit_authenticator as stauth
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def load_auth_config():
    """Load authentication configuration from YAML file."""
    try:
        config_path = Path(__file__).parent.parent / "config" / "auth_config.yaml"
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        return config
    except Exception as e:
        logger.error(f"Failed to load authentication config: {e}")
        return None

def initialize_authenticator():
    """Initialize the streamlit-authenticator object."""
    if 'authenticator' not in st.session_state:
        config = load_auth_config()
        if config:
            st.session_state.authenticator = stauth.Authenticate(
                config['credentials'],
                config['cookie']['name'],
                config['cookie']['key'],
                config['cookie']['expiry_days'],
                config['preauthorized']
            )
        else:
            st.error("Failed to load authentication configuration")
            st.stop()
    
    return st.session_state.authenticator

def check_authentication():
    """Check if user is authenticated and handle login/logout."""
    authenticator = initialize_authenticator()
    
    # Handle login
    name, authentication_status, username = authenticator.login('Login', 'main')
    
    if authentication_status == False:
        st.error('Username/password is incorrect')
        return False
    elif authentication_status == None:
        st.warning('Please enter your username and password')
        return False
    elif authentication_status:
        # User is authenticated
        st.session_state.name = name
        st.session_state.username = username
        st.session_state.authentication_status = authentication_status
        return True
    
    return False

def show_logout_button():
    """Display logout button in sidebar for authenticated users."""
    if st.session_state.get('authentication_status'):
        authenticator = st.session_state.authenticator
        
        # Show user info in sidebar
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"**Welcome, {st.session_state.name}!**")
        st.sidebar.markdown(f"*Username: {st.session_state.username}*")
        
        # Logout button
        if st.sidebar.button("🚪 Logout"):
            authenticator.logout('Logout', 'sidebar')
            st.session_state.authentication_status = None
            st.session_state.name = None
            st.session_state.username = None
            st.rerun()

def require_authentication():
    """Decorator function to require authentication for a page."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not st.session_state.get('authentication_status'):
                st.error('🔒 Please log in to access this page')
                st.stop()
            return func(*args, **kwargs)
        return wrapper
    return decorator

def show_login_page():
    """Display a dedicated login page."""
    st.title("🔐 Login Required")
    st.markdown("Please log in to access the Home Inventory System.")
    
    # Add some styling
    st.markdown("""
    <style>
    .main > div {
        padding-top: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🏠 Home Inventory System")
        st.markdown("---")
        
        # Login form will be handled by check_authentication()
        if not check_authentication():
            st.markdown("---")
            st.markdown("#### Default Login Credentials:")
            st.markdown("- **Admin:** username=`admin`, password=`admin123`")
            st.markdown("- **User:** username=`user`, password=`user123`")
            st.markdown("- **Demo:** username=`demo`, password=`demo123`")
            
            return False
        else:
            st.success("✅ Login successful! Redirecting...")
            st.rerun()
            return True

def get_current_user():
    """Get the current authenticated user's information."""
    if st.session_state.get('authentication_status'):
        return {
            'name': st.session_state.get('name'),
            'username': st.session_state.get('username'),
            'authenticated': True
        }
    return {'authenticated': False}

def is_authenticated():
    """Simple check if user is authenticated."""
    return bool(st.session_state.get('authentication_status'))