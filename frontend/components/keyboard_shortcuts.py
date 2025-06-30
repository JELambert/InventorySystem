"""
Keyboard shortcuts and UX enhancements for the Home Inventory System.

This module provides keyboard shortcuts, hotkeys, and improved user experience
features for the Streamlit frontend.
"""

import streamlit as st
import streamlit.components.v1 as components
from typing import Dict, Any, Callable, Optional

def enable_keyboard_shortcuts():
    """Enable global keyboard shortcuts for the application."""
    
    # JavaScript for keyboard shortcuts
    shortcut_script = """
    <script>
    document.addEventListener('keydown', function(e) {
        // Prevent default behavior for our shortcuts
        const shortcuts = {
            'KeyN': () => { // Alt+N for New Location
                if (e.altKey && !e.ctrlKey && !e.shiftKey) {
                    e.preventDefault();
                    // Trigger Streamlit event
                    window.parent.postMessage({
                        type: 'streamlit:shortcut',
                        action: 'new_location'
                    }, '*');
                }
            },
            'KeyS': () => { // Alt+S for Search
                if (e.altKey && !e.ctrlKey && !e.shiftKey) {
                    e.preventDefault();
                    const searchInput = document.querySelector('input[placeholder*="Search"], input[placeholder*="search"]');
                    if (searchInput) {
                        searchInput.focus();
                        searchInput.select();
                    }
                }
            },
            'KeyD': () => { // Alt+D for Dashboard
                if (e.altKey && !e.ctrlKey && !e.shiftKey) {
                    e.preventDefault();
                    window.parent.postMessage({
                        type: 'streamlit:shortcut',
                        action: 'dashboard'
                    }, '*');
                }
            },
            'KeyL': () => { // Alt+L for Locations
                if (e.altKey && !e.ctrlKey && !e.shiftKey) {
                    e.preventDefault();
                    window.parent.postMessage({
                        type: 'streamlit:shortcut',
                        action: 'locations'
                    }, '*');
                }
            },
            'KeyM': () => { // Alt+M for Manage
                if (e.altKey && !e.ctrlKey && !e.shiftKey) {
                    e.preventDefault();
                    window.parent.postMessage({
                        type: 'streamlit:shortcut',
                        action: 'manage'
                    }, '*');
                }
            },
            'KeyR': () => { // Alt+R for Refresh
                if (e.altKey && !e.ctrlKey && !e.shiftKey) {
                    e.preventDefault();
                    window.parent.postMessage({
                        type: 'streamlit:shortcut',
                        action: 'refresh'
                    }, '*');
                }
            },
            'Escape': () => { // ESC to clear/cancel
                if (!e.altKey && !e.ctrlKey && !e.shiftKey) {
                    window.parent.postMessage({
                        type: 'streamlit:shortcut',
                        action: 'cancel'
                    }, '*');
                }
            }
        };
        
        if (shortcuts[e.code]) {
            shortcuts[e.code]();
        }
    });
    
    // Handle Streamlit messages
    window.addEventListener('message', function(e) {
        if (e.data.type === 'streamlit:shortcut') {
            // Store the action in session storage for Streamlit to read
            sessionStorage.setItem('streamlit_shortcut', e.data.action);
            
            // Trigger a small DOM change to notify Streamlit
            const event = new CustomEvent('streamlit_shortcut', {
                detail: { action: e.data.action }
            });
            document.dispatchEvent(event);
        }
    });
    </script>
    """
    
    components.html(shortcut_script, height=0)

def check_keyboard_shortcuts() -> Optional[str]:
    """Check if a keyboard shortcut was triggered and return the action."""
    # Use JavaScript to check session storage
    check_script = """
    <script>
    const action = sessionStorage.getItem('streamlit_shortcut');
    if (action) {
        sessionStorage.removeItem('streamlit_shortcut');
        // Send to Streamlit
        window.parent.postMessage({
            type: 'streamlit:action',
            action: action
        }, '*');
    }
    </script>
    """
    
    # This is a simplified approach - in a real implementation,
    # we'd need a more sophisticated message passing system
    return None

def show_keyboard_shortcuts_help():
    """Display keyboard shortcuts help in the sidebar."""
    with st.sidebar.expander("⌨️ Keyboard Shortcuts"):
        st.markdown("""
        **Navigation:**
        - `Alt + D` - Go to Dashboard
        - `Alt + L` - Go to Locations
        - `Alt + M` - Go to Manage
        
        **Actions:**
        - `Alt + N` - New Location
        - `Alt + S` - Focus Search
        - `Alt + R` - Refresh Page
        - `Esc` - Cancel/Clear
        
        **Tips:**
        - Use Tab to navigate between form fields
        - Enter to submit forms
        - Arrow keys in tables and lists
        """)

def create_enhanced_search_box(
    placeholder: str = "Search locations...",
    key: str = "search",
    help_text: str = "Search in location names and descriptions"
) -> str:
    """Create an enhanced search box with better UX."""
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        search_value = st.text_input(
            "Search",
            placeholder=placeholder,
            key=key,
            help=help_text,
            label_visibility="collapsed"
        )
    
    with col2:
        # Clear button
        if st.button("🗑️", key=f"{key}_clear", help="Clear search"):
            st.session_state[key] = ""
            st.rerun()
    
    return search_value

def create_quick_filter_buttons(
    current_filter: str,
    filter_options: Dict[str, str],
    key_prefix: str = "filter"
) -> str:
    """Create quick filter buttons for common actions."""
    
    st.markdown("**Quick Filters:**")
    
    cols = st.columns(len(filter_options))
    selected_filter = current_filter
    
    for i, (filter_key, filter_label) in enumerate(filter_options.items()):
        with cols[i]:
            is_active = current_filter == filter_key
            button_type = "primary" if is_active else "secondary"
            
            if st.button(
                filter_label, 
                key=f"{key_prefix}_{filter_key}",
                type=button_type,
                use_container_width=True
            ):
                selected_filter = filter_key
    
    return selected_filter

def create_pagination_controls(
    current_page: int,
    total_items: int,
    items_per_page: int,
    key_prefix: str = "page"
) -> int:
    """Create enhanced pagination controls with jump-to-page."""
    
    total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
    
    if total_pages <= 1:
        return current_page
    
    st.markdown("---")
    
    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
    
    new_page = current_page
    
    with col1:
        if st.button("⏮️ First", key=f"{key_prefix}_first", disabled=current_page == 0):
            new_page = 0
    
    with col2:
        if st.button("⬅️ Prev", key=f"{key_prefix}_prev", disabled=current_page == 0):
            new_page = max(0, current_page - 1)
    
    with col3:
        # Jump to page
        page_options = list(range(1, total_pages + 1))
        selected_page = st.selectbox(
            "Page",
            page_options,
            index=current_page,
            key=f"{key_prefix}_select",
            format_func=lambda x: f"Page {x} of {total_pages}"
        )
        if selected_page != current_page + 1:
            new_page = selected_page - 1
    
    with col4:
        if st.button("Next ➡️", key=f"{key_prefix}_next", disabled=current_page >= total_pages - 1):
            new_page = min(total_pages - 1, current_page + 1)
    
    with col5:
        if st.button("Last ⏭️", key=f"{key_prefix}_last", disabled=current_page >= total_pages - 1):
            new_page = total_pages - 1
    
    # Show page info
    start_item = current_page * items_per_page + 1
    end_item = min(start_item + items_per_page - 1, total_items)
    
    st.caption(f"Showing {start_item}-{end_item} of {total_items} items")
    
    return new_page

def create_action_buttons_row(
    actions: Dict[str, Dict[str, Any]],
    key_prefix: str = "action"
):
    """Create a row of action buttons with consistent styling."""
    
    if not actions:
        return
    
    cols = st.columns(len(actions))
    
    for i, (action_key, action_config) in enumerate(actions.items()):
        with cols[i]:
            button_args = {
                'label': action_config.get('label', action_key),
                'key': f"{key_prefix}_{action_key}",
                'type': action_config.get('type', 'secondary'),
                'disabled': action_config.get('disabled', False),
                'use_container_width': True
            }
            
            if 'help' in action_config:
                button_args['help'] = action_config['help']
            
            if st.button(**button_args):
                callback = action_config.get('callback')
                if callback and callable(callback):
                    callback()
                
                # Store action in session state
                st.session_state[f'{key_prefix}_triggered'] = action_key

def create_bulk_selection_interface(
    items: list,
    id_field: str = 'id',
    display_field: str = 'name',
    key_prefix: str = "bulk"
) -> Dict[str, Any]:
    """Create bulk selection interface for items."""
    
    if not items:
        return {'selected_items': [], 'select_all': False}
    
    # Select all checkbox
    select_all = st.checkbox(
        f"Select all {len(items)} items",
        key=f"{key_prefix}_select_all"
    )
    
    # Individual checkboxes
    selected_items = []
    
    if select_all:
        selected_items = [item[id_field] for item in items]
        st.session_state[f"{key_prefix}_selected"] = selected_items
    else:
        # Show individual selection
        for item in items:
            item_id = item[id_field]
            item_display = item.get(display_field, str(item_id))
            
            is_selected = st.checkbox(
                item_display,
                key=f"{key_prefix}_item_{item_id}",
                value=item_id in st.session_state.get(f"{key_prefix}_selected", [])
            )
            
            if is_selected:
                selected_items.append(item_id)
    
    st.session_state[f"{key_prefix}_selected"] = selected_items
    
    # Show selection summary
    if selected_items:
        st.info(f"Selected {len(selected_items)} item(s)")
    
    return {
        'selected_items': selected_items,
        'select_all': select_all,
        'total_selected': len(selected_items)
    }

def create_confirmation_dialog(
    title: str,
    message: str,
    confirm_text: str = "Confirm",
    cancel_text: str = "Cancel",
    key_prefix: str = "confirm"
) -> Optional[bool]:
    """Create a confirmation dialog."""
    
    st.markdown(f"### {title}")
    st.warning(message)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(
            confirm_text,
            key=f"{key_prefix}_confirm",
            type="primary",
            use_container_width=True
        ):
            return True
    
    with col2:
        if st.button(
            cancel_text,
            key=f"{key_prefix}_cancel",
            use_container_width=True
        ):
            return False
    
    return None