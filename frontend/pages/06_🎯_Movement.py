"""
Item Movement page for the Home Inventory System.

Provides sophisticated drag-and-drop interfaces for moving items between locations,
advanced quantity operations, and comprehensive movement history tracking.
"""

import streamlit as st
import pandas as pd
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from utils.api_client import APIClient, APIError
from utils.helpers import (
    safe_api_call, show_error, show_success, show_warning,
    handle_api_error, SessionManager, format_datetime,
    safe_strip, safe_string_check, safe_string_or_none
)
from components.item_movement import (
    create_drag_drop_movement_interface,
    create_movement_history_panel,
    create_advanced_quantity_operations_panel,
    show_movement_modals
)
from components.keyboard_shortcuts import (
    enable_keyboard_shortcuts, show_keyboard_shortcuts_help
)

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Movement - Home Inventory System",
    page_icon="🎯",
    layout="wide"
)


def show_movement_page():
    """Main movement page display."""
    # Page header
    st.title("🎯 Item Movement & History")
    st.markdown("Sophisticated tools for moving items, tracking history, and managing quantities")
    
    # Initialize session manager
    session = SessionManager()
    api_client = APIClient()
    
    # Enable keyboard shortcuts
    enable_keyboard_shortcuts()
    
    # Create tabs for different movement features
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 Drag & Drop Movement", 
        "📊 Movement History", 
        "⚙️ Advanced Operations",
        "📈 Movement Analytics"
    ])
    
    with tab1:
        show_drag_drop_interface()
    
    with tab2:
        show_movement_history_interface()
    
    with tab3:
        show_advanced_operations_interface()
    
    with tab4:
        show_movement_analytics_interface()
    
    # Display movement modals
    show_movement_modals()


def show_drag_drop_interface():
    """Display the drag and drop movement interface."""
    st.markdown("### 🎯 Interactive Item Movement")
    st.markdown("_Move items between locations using visual drag-and-drop interface_")
    
    # Load data
    api_client = APIClient()
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        # Filter controls
        st.markdown("#### 🎛️ Filters")
        
        # Item type filter
        item_types = ["all", "electronics", "furniture", "clothing", "books", "tools", "kitchen", "other"]
        selected_type = st.selectbox("Item Type:", item_types, format_func=lambda x: x.title())
        
        # Location type filter  
        location_types = ["all", "house", "room", "container", "shelf"]
        selected_location_type = st.selectbox("Location Type:", location_types, format_func=lambda x: x.title())
        
        # Only show items with inventory
        show_only_inventory = st.checkbox("Only items in inventory", value=True)
        
        # Refresh button
        if st.button("🔄 Refresh Data", help="Reload items and locations"):
            if 'movement_items_cache' in st.session_state:
                del st.session_state.movement_items_cache
            if 'movement_locations_cache' in st.session_state:
                del st.session_state.movement_locations_cache
            st.rerun()
    
    with col2:
        # Load items and locations
        with st.spinner("Loading items and locations..."):
            # Load items
            if 'movement_items_cache' not in st.session_state:
                item_params = {}
                if selected_type != "all":
                    item_params["item_type"] = selected_type
                
                if show_only_inventory:
                    items = safe_api_call(
                        lambda: api_client.get_items_with_inventory(**item_params),
                        "Failed to load items with inventory"
                    ) or []
                else:
                    items = safe_api_call(
                        lambda: api_client.get_items(**item_params),
                        "Failed to load items"
                    ) or []
                
                st.session_state.movement_items_cache = items
            else:
                items = st.session_state.movement_items_cache
            
            # Load locations
            if 'movement_locations_cache' not in st.session_state:
                location_params = {"skip": 0, "limit": 1000}
                if selected_location_type != "all":
                    location_params["location_type"] = selected_location_type
                
                locations = safe_api_call(
                    lambda: api_client.get_locations(**location_params),
                    "Failed to load locations"
                ) or []
                
                st.session_state.movement_locations_cache = locations
            else:
                locations = st.session_state.movement_locations_cache
        
        # Display drag and drop interface
        if items and locations:
            create_drag_drop_movement_interface(items, locations)
        else:
            st.info("No items or locations available for movement operations.")


def show_movement_history_interface():
    """Display the movement history interface."""
    st.markdown("### 📊 Movement History & Audit Trail")
    
    # Movement history controls
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown("#### 🔍 History Filters")
        
        # Item selection for filtering
        api_client = APIClient()
        items = safe_api_call(
            lambda: api_client.get_items(skip=0, limit=1000),
            "Failed to load items for filtering"
        ) or []
        
        item_options = {"all": "All Items"}
        item_options.update({item['id']: f"{item['name']} - {item.get('item_type', '').replace('_', ' ').title()}" 
                           for item in items})
        
        selected_item_filter = st.selectbox(
            "Filter by Item:",
            options=list(item_options.keys()),
            format_func=lambda x: item_options[x]
        )
        
        item_id_filter = None if selected_item_filter == "all" else selected_item_filter
        
        # Quick time period buttons
        st.markdown("**Quick Time Filters:**")
        
        time_filters = {
            "today": "Today",
            "week": "This Week", 
            "month": "This Month",
            "quarter": "This Quarter",
            "all": "All Time"
        }
        
        selected_time = st.radio("Time Period:", list(time_filters.keys()), 
                                format_func=lambda x: time_filters[x], index=1)
        
        # Movement type filter
        movement_types = ["all", "create", "move", "adjust"]
        selected_movement_type = st.selectbox(
            "Movement Type:",
            movement_types,
            format_func=lambda x: x.title() if x != "all" else "All Types"
        )
        
        # User filter
        user_filter = st.text_input("User Filter:", placeholder="Enter user ID")
        
        # Show summary button
        show_summary = st.checkbox("Show Summary Stats", value=True)
    
    with col2:
        # Display movement history with filters
        history_params = {}
        
        if item_id_filter:
            history_params['item_id'] = item_id_filter
        
        if selected_movement_type != "all":
            history_params['movement_type'] = selected_movement_type
        
        if user_filter:
            history_params['user_id'] = user_filter
        
        # Calculate date range based on time filter
        if selected_time != "all":
            now = datetime.now()
            if selected_time == "today":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif selected_time == "week":
                start_date = now - timedelta(days=7)
            elif selected_time == "month":
                start_date = now - timedelta(days=30)
            elif selected_time == "quarter":
                start_date = now - timedelta(days=90)
            
            history_params['start_date'] = start_date.isoformat()
        
        # Display movement history
        create_movement_history_panel(item_id_filter)
        
        # Show summary if requested
        if show_summary:
            st.markdown("---")
            show_movement_summary(history_params)


def show_movement_summary(history_params: Dict[str, Any]):
    """Show movement summary statistics."""
    st.markdown("#### 📈 Movement Summary")
    
    api_client = APIClient()
    
    # Get summary data
    summary_params = {}
    if 'start_date' in history_params:
        summary_params['start_date'] = history_params['start_date']
    
    summary = safe_api_call(
        lambda: api_client.get_movement_history_summary(**summary_params),
        "Failed to load movement summary"
    )
    
    if summary:
        # Display key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Movements", summary.get('total_movements', 0))
        
        with col2:
            st.metric("Items Moved", summary.get('total_items_moved', 0))
        
        with col3:
            st.metric("Unique Items", summary.get('unique_items', 0))
        
        with col4:
            st.metric("Locations Involved", summary.get('unique_locations', 0))
        
        # Movement types breakdown
        movement_types = summary.get('movement_types', [])
        if movement_types:
            st.markdown("**Movement Types Breakdown:**")
            
            # Create a simple chart
            types_df = pd.DataFrame(movement_types)
            if not types_df.empty:
                st.bar_chart(types_df.set_index('movement_type')['count'])
        
        # Date range info
        date_range = summary.get('date_range', {})
        if date_range:
            st.info(f"Data from {date_range.get('earliest', 'Unknown')} to {date_range.get('latest', 'Unknown')}")


def show_advanced_operations_interface():
    """Display the advanced quantity operations interface."""
    st.markdown("### ⚙️ Advanced Quantity Operations")
    st.markdown("_Split, merge, and adjust item quantities with comprehensive audit trails_")
    
    # Display the advanced operations panel
    create_advanced_quantity_operations_panel()
    
    # Additional tools section
    st.markdown("---")
    st.markdown("#### 🛠️ Additional Tools")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📋 Bulk Operations**")
        if st.button("🔄 Bulk Move Items", help="Move multiple items at once"):
            st.session_state.show_bulk_move_modal = True
            st.rerun()
        
        if st.button("📊 Bulk Quantity Adjust", help="Adjust quantities for multiple items"):
            st.session_state.show_bulk_adjust_modal = True
            st.rerun()
    
    with col2:
        st.markdown("**📤 Export Operations**")
        if st.button("📄 Export Movement History", help="Export movement history to CSV"):
            export_movement_history()
        
        if st.button("📊 Export Inventory Report", help="Export current inventory status"):
            export_inventory_report()


def show_movement_analytics_interface():
    """Display movement analytics and insights."""
    st.markdown("### 📈 Movement Analytics & Insights")
    st.markdown("_Advanced analytics and visualization of item movement patterns_")
    
    api_client = APIClient()
    
    # Time range selector
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown("#### ⏱️ Analysis Period")
        
        analysis_periods = {
            "week": "Last Week",
            "month": "Last Month", 
            "quarter": "Last Quarter",
            "year": "Last Year",
            "all": "All Time"
        }
        
        selected_period = st.selectbox(
            "Analysis Period:",
            list(analysis_periods.keys()),
            format_func=lambda x: analysis_periods[x],
            index=1
        )
        
        # Calculate date range
        now = datetime.now()
        if selected_period == "week":
            start_date = now - timedelta(days=7)
        elif selected_period == "month":
            start_date = now - timedelta(days=30)
        elif selected_period == "quarter":
            start_date = now - timedelta(days=90)
        elif selected_period == "year":
            start_date = now - timedelta(days=365)
        else:
            start_date = None
        
        # Refresh analytics
        if st.button("🔄 Refresh Analytics"):
            if 'analytics_cache' in st.session_state:
                del st.session_state.analytics_cache
            st.rerun()
    
    with col2:
        # Get analytics data
        analytics_params = {}
        if start_date:
            analytics_params['start_date'] = start_date.isoformat()
        
        # Load movement history for analytics
        movements = safe_api_call(
            lambda: api_client.get_movement_history(limit=1000, **analytics_params),
            "Failed to load movement data for analytics"
        ) or []
        
        if movements:
            # Movement trend analysis
            st.markdown("#### 📊 Movement Trends")
            
            # Create movements dataframe
            movements_df = pd.DataFrame([
                {
                    "date": pd.to_datetime(m.get('created_at')).date(),
                    "type": m.get('movement_type', 'unknown'),
                    "quantity": m.get('quantity_moved', 0),
                    "item_id": m.get('item_id'),
                    "from_location": m.get('from_location', {}).get('name', '') if m.get('from_location') else '',
                    "to_location": m.get('to_location', {}).get('name', '') if m.get('to_location') else ''
                }
                for m in movements
            ])
            
            if not movements_df.empty:
                # Daily movement volume
                daily_movements = movements_df.groupby('date').size().reset_index(name='count')
                if len(daily_movements) > 1:
                    st.line_chart(daily_movements.set_index('date')['count'])
                
                # Movement types distribution
                st.markdown("#### 🏷️ Movement Types Distribution")
                type_counts = movements_df['type'].value_counts()
                st.bar_chart(type_counts)
                
                # Most active locations
                st.markdown("#### 📍 Most Active Locations")
                
                # Combine from and to locations
                from_counts = movements_df[movements_df['from_location'] != '']['from_location'].value_counts()
                to_counts = movements_df[movements_df['to_location'] != '']['to_location'].value_counts()
                
                # Combine and get top locations
                all_locations = pd.concat([from_counts, to_counts]).groupby(level=0).sum().sort_values(ascending=False)
                
                if not all_locations.empty:
                    st.bar_chart(all_locations.head(10))
                
                # Movement insights
                st.markdown("#### 💡 Movement Insights")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    avg_daily = len(movements) / max(1, (datetime.now().date() - movements_df['date'].min()).days)
                    st.metric("Avg Daily Movements", f"{avg_daily:.1f}")
                
                with col2:
                    most_moved_item = movements_df['item_id'].value_counts().index[0] if not movements_df.empty else None
                    if most_moved_item:
                        # Get item name
                        try:
                            item = api_client.get_item(most_moved_item)
                            item_name = item.get('name', 'Unknown')
                        except:
                            item_name = f"Item {most_moved_item}"
                        st.metric("Most Moved Item", item_name[:20] + "..." if len(item_name) > 20 else item_name)
                
                with col3:
                    total_quantity = movements_df['quantity'].sum()
                    st.metric("Total Items Moved", total_quantity)
        
        else:
            st.info("No movement data available for the selected period.")


def export_movement_history():
    """Export movement history to CSV."""
    api_client = APIClient()
    
    with st.spinner("Exporting movement history..."):
        movements = safe_api_call(
            lambda: api_client.get_movement_history(limit=10000),
            "Failed to export movement history"
        )
        
        if movements:
            # Create CSV data
            csv_data = []
            for movement in movements:
                csv_data.append({
                    "Date": movement.get('created_at', ''),
                    "Item": movement.get('item', {}).get('name', 'Unknown'),
                    "Movement Type": movement.get('movement_type', ''),
                    "Description": movement.get('movement_description', ''),
                    "Quantity": movement.get('quantity_moved', 0),
                    "From Location": movement.get('from_location', {}).get('name', '') if movement.get('from_location') else '',
                    "To Location": movement.get('to_location', {}).get('name', '') if movement.get('to_location') else '',
                    "User": movement.get('user_id', ''),
                    "Reason": movement.get('reason', ''),
                    "Notes": movement.get('notes', '')
                })
            
            df = pd.DataFrame(csv_data)
            csv = df.to_csv(index=False)
            
            st.download_button(
                label="📄 Download Movement History CSV",
                data=csv,
                file_name=f"movement_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            show_success("Movement history export ready for download!")
        else:
            show_error("No movement history data to export.")


def export_inventory_report():
    """Export current inventory report."""
    api_client = APIClient()
    
    with st.spinner("Generating inventory report..."):
        inventory = safe_api_call(
            lambda: api_client.get_inventory(),
            "Failed to export inventory"
        )
        
        if inventory:
            # Create comprehensive inventory report
            csv_data = []
            for entry in inventory:
                item = entry.get('item', {})
                location = entry.get('location', {})
                
                csv_data.append({
                    "Item ID": entry.get('item_id', ''),
                    "Item Name": item.get('name', 'Unknown'),
                    "Item Type": item.get('item_type', ''),
                    "Brand": item.get('brand', ''),
                    "Model": item.get('model', ''),
                    "Condition": item.get('condition', ''),
                    "Status": item.get('status', ''),
                    "Location ID": entry.get('location_id', ''),
                    "Location Name": location.get('name', 'Unknown'),
                    "Location Type": location.get('location_type', ''),
                    "Quantity": entry.get('quantity', 0),
                    "Unit Value": item.get('current_value', ''),
                    "Total Value": entry.get('total_value', ''),
                    "Last Updated": entry.get('updated_at', ''),
                    "Serial Number": item.get('serial_number', ''),
                    "Tags": item.get('tags', '')
                })
            
            df = pd.DataFrame(csv_data)
            csv = df.to_csv(index=False)
            
            st.download_button(
                label="📊 Download Inventory Report CSV",
                data=csv,
                file_name=f"inventory_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            show_success("Inventory report ready for download!")
        else:
            show_error("No inventory data to export.")


# Main execution
if __name__ == "__main__":
    try:
        show_movement_page()
    except Exception as e:
        logger.error(f"Error in movement page: {str(e)}")
        show_error(f"An error occurred: {str(e)}")
        st.info("Please refresh the page or contact support if the problem persists.")