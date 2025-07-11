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
from components.auth import is_authenticated, show_logout_button
from utils.helpers import (
    safe_api_call, show_error, show_success, show_warning,
    handle_api_error, SessionManager, format_datetime,
    safe_strip, safe_string_check, safe_string_or_none
)
from components.item_movement import (
    create_drag_drop_movement_interface,
    create_movement_history_panel,
    create_advanced_quantity_operations_panel,
    show_movement_modals,
    create_simplified_movement_interface
)
from components.movement_validation import (
    create_movement_validation_widget,
    create_bulk_validation_widget,
    show_validation_report_widget,
    create_business_rules_override_widget
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
    # Check authentication
    if not is_authenticated():
        st.error('🔒 Please log in to access this page')
        st.stop()
    
    # Page header
    st.title("🎯 Item Movement & History")
    st.markdown("Sophisticated tools for moving items, tracking history, and managing quantities")
    
    # Show logout button
    show_logout_button()
    
    # Initialize session manager
    session = SessionManager()
    api_client = APIClient()
    
    # Enable keyboard shortcuts
    enable_keyboard_shortcuts()
    
    # Create simplified tabs for different movement features
    tab1, tab2, tab3 = st.tabs([
        "🎯 Quick Movement", 
        "📊 Movement History", 
        "⚙️ Advanced Features"
    ])
    
    with tab1:
        # Use the new simplified movement interface
        create_simplified_movement_interface()
    
    with tab2:
        show_movement_history_interface()
    
    with tab3:
        # Combine advanced operations, analytics, validation, and admin
        show_advanced_features_interface()
    
    # Display movement modals
    show_movement_modals()


def show_drag_drop_interface():
    """Display the drag and drop movement interface."""
    st.markdown("### 🎯 Interactive Item Movement")
    st.markdown("_Move items between locations using visual drag-and-drop interface_")
    
    # Load data
    api_client = APIClient()
    
    # Filter controls section
    with st.container():
        st.markdown("#### 🎛️ Filters")
        
        # Create filter controls in a horizontal layout
        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
        
        with filter_col1:
            # Item type filter
            item_types = ["all", "electronics", "furniture", "clothing", "books", "tools", "kitchen", "other"]
            selected_type = st.selectbox("Item Type:", item_types, format_func=lambda x: x.title())
        
        with filter_col2:
            # Location type filter  
            location_types = ["all", "house", "room", "container", "shelf"]
            selected_location_type = st.selectbox("Location Type:", location_types, format_func=lambda x: x.title())
        
        with filter_col3:
            # Only show items with inventory
            show_only_inventory = st.checkbox("Only items in inventory", value=True)
        
        with filter_col4:
            # Refresh button
            if st.button("🔄 Refresh Data", help="Reload items and locations"):
                if 'movement_items_cache' in st.session_state:
                    del st.session_state.movement_items_cache
                if 'movement_locations_cache' in st.session_state:
                    del st.session_state.movement_locations_cache
                st.rerun()
    
    # Data loading section
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
    """Display the simplified movement history interface."""
    st.markdown("### 📊 Movement History & Audit Trail")
    
    api_client = APIClient()
    
    # Simplified filters
    with st.container():
        st.markdown("#### 🔍 Quick Filters")
        
        # Create filter controls in horizontal layout
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        
        with filter_col1:
            # Time period filter (most common use case)
            time_filters = {
                "today": "Today",
                "week": "This Week", 
                "month": "This Month",
                "all": "All Time"
            }
            
            selected_time = st.selectbox(
                "📅 Time Period:", 
                list(time_filters.keys()), 
                format_func=lambda x: time_filters[x], 
                index=1
            )
        
        with filter_col2:
            # Movement type filter
            movement_types = ["all", "move", "create", "adjust"]
            selected_movement_type = st.selectbox(
                "🔄 Movement Type:",
                movement_types,
                format_func=lambda x: x.title() if x != "all" else "All Types"
            )
        
        with filter_col3:
            # Quick refresh and summary toggle
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🔄 Refresh", help="Refresh movement history"):
                    st.rerun()
            with col_b:
                show_summary = st.toggle("📊 Summary", value=True, help="Show summary statistics")
    
    # Advanced filters in expander
    with st.expander("🔧 Advanced Filters", expanded=False):
        adv_col1, adv_col2 = st.columns(2)
        
        with adv_col1:
            # Item filter (load with inventory for better UX)
            items = safe_api_call(
                lambda: api_client.get_items_with_inventory(limit=1000),
                "Failed to load items for filtering"
            ) or []
            
            item_options = {"all": "All Items"}
            for item in items:
                inventory_count = len(item.get('inventory_entries', []))
                inventory_text = f" ({inventory_count} locations)" if inventory_count > 1 else ""
                item_options[item['id']] = f"{item['name']}{inventory_text}"
            
            selected_item_filter = st.selectbox(
                "🔍 Filter by Item:",
                options=list(item_options.keys()),
                format_func=lambda x: item_options[x]
            )
            
            item_id_filter = None if selected_item_filter == "all" else selected_item_filter
        
        with adv_col2:
            user_filter = st.text_input("👤 User Filter:", placeholder="Enter user ID (optional)")
    
    # Calculate history parameters
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
    
    # Create tools in horizontal layout
    tools_col1, tools_col2 = st.columns(2)
    
    with tools_col1:
        st.markdown("**📋 Bulk Operations**")
        if st.button("🔄 Bulk Move Items", help="Move multiple items at once"):
            st.session_state.show_bulk_move_modal = True
            st.rerun()
        
        if st.button("📊 Bulk Quantity Adjust", help="Adjust quantities for multiple items"):
            st.session_state.show_bulk_adjust_modal = True
            st.rerun()
    
    with tools_col2:
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
    
    # Analysis period selection
    with st.container():
        st.markdown("#### ⏱️ Analysis Period")
        
        analysis_periods = {
            "week": "Last Week",
            "month": "Last Month", 
            "quarter": "Last Quarter",
            "year": "Last Year",
            "all": "All Time"
        }
        
        period_col1, period_col2 = st.columns(2)
        
        with period_col1:
            selected_period = st.selectbox(
                "Analysis Period:",
                list(analysis_periods.keys()),
                format_func=lambda x: analysis_periods[x],
                index=1
            )
        
        with period_col2:
            # Refresh analytics
            if st.button("🔄 Refresh Analytics"):
                if 'analytics_cache' in st.session_state:
                    del st.session_state.analytics_cache
                st.rerun()
    
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
            
            # Display metrics in simple layout using containers
            with st.container():
                insights_col1, insights_col2, insights_col3 = st.columns(3)
                
                with insights_col1:
                    avg_daily = len(movements) / max(1, (datetime.now().date() - movements_df['date'].min()).days)
                    st.metric("Avg Daily Movements", f"{avg_daily:.1f}")
                
                with insights_col2:
                    most_moved_item = movements_df['item_id'].value_counts().index[0] if not movements_df.empty else None
                    if most_moved_item:
                        # Get item name
                        try:
                            item = api_client.get_item(most_moved_item)
                            item_name = item.get('name', 'Unknown')
                        except:
                            item_name = f"Item {most_moved_item}"
                        st.metric("Most Moved Item", item_name[:20] + "..." if len(item_name) > 20 else item_name)
                
                with insights_col3:
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


def show_validation_interface():
    """Display the validation interface."""
    st.markdown("### 🔍 Movement Validation & Testing")
    st.markdown("_Validate movements before execution and test business rules_")
    
    validation_tabs = st.tabs(["🔍 Single Movement", "📦 Bulk Validation", "📊 Validation Report"])
    
    with validation_tabs[0]:
        # Single movement validation
        create_movement_validation_widget()
    
    with validation_tabs[1]:
        # Bulk movement validation
        create_bulk_validation_widget()
    
    with validation_tabs[2]:
        # Validation system report
        show_validation_report_widget()


def show_advanced_features_interface():
    """Display consolidated advanced features interface."""
    st.markdown("### ⚙️ Advanced Movement Features")
    st.markdown("_Advanced operations, analytics, validation, and administrative tools_")
    
    # Create sub-tabs for advanced features
    advanced_tabs = st.tabs([
        "🔧 Advanced Operations", 
        "📈 Analytics", 
        "🔍 Validation", 
        "⚙️ Administration",
        "🗂️ Classic Interface"
    ])
    
    with advanced_tabs[0]:
        show_advanced_operations_interface()
    
    with advanced_tabs[1]:
        show_movement_analytics_interface()
    
    with advanced_tabs[2]:
        show_validation_interface()
    
    with advanced_tabs[3]:
        show_admin_interface()
    
    with advanced_tabs[4]:
        # Show the original drag-and-drop interface for users who prefer it
        st.markdown("#### 🎯 Classic Drag & Drop Interface")
        st.info("This is the original movement interface. The new Quick Movement tab is recommended for most users.")
        show_drag_drop_interface()


def show_admin_interface():
    """Display the admin interface for movement system management."""
    st.markdown("#### ⚙️ Movement System Administration")
    st.markdown("_Administrative tools for movement system configuration and monitoring_")
    
    admin_tabs = st.tabs(["🔧 Business Rules", "📊 System Health", "🔄 Maintenance"])
    
    with admin_tabs[0]:
        # Business rules management
        create_business_rules_override_widget()
    
    with admin_tabs[1]:
        # System health monitoring
        show_system_health_monitoring()
    
    with admin_tabs[2]:
        # Maintenance tools
        show_maintenance_tools()


def show_system_health_monitoring():
    """Display system health monitoring dashboard."""
    st.markdown("#### 🏥 System Health Monitoring")
    
    api_client = APIClient()
    
    # Health check controls
    with st.container():
        health_col1, health_col2 = st.columns(2)
        
        with health_col1:
            if st.button("🔄 Refresh Health Status", type="primary"):
                with st.spinner("Checking system health..."):
                    health_status = safe_api_call(
                        lambda: api_client.health_check(),
                        "Failed to check system health"
                    )
                    
                    validation_report = safe_api_call(
                        lambda: api_client.get_validation_report(),
                        "Failed to get validation report"
                    )
                    
                    if health_status:
                        show_success("✅ Backend API is healthy")
                    else:
                        show_error("❌ Backend API health check failed")
                    
                    if validation_report:
                        SessionManager.set('health_validation_report', validation_report)
                        st.rerun()
        
        with health_col2:
            # Current health status
            validation_report = SessionManager.get('health_validation_report')
            if validation_report:
                api_status = "🟢 Online" if api_client.health_check() else "🔴 Offline"
                st.metric("API Status", api_status)
    
    # Display health metrics
    validation_report = SessionManager.get('health_validation_report')
    if validation_report:
        system_health = validation_report.get('system_health', {})
        
        # System metrics section
        st.markdown("**📊 System Metrics**")
        
        with st.container():
            metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
            
            with metrics_col1:
                st.metric(
                    "Movements (24h)",
                    system_health.get('movements_last_24h', 0),
                    help="Total movements in the last 24 hours"
                )
            
            with metrics_col2:
                st.metric(
                    "Active Rules",
                    system_health.get('validation_rules_active', 0),
                    help="Number of active business rules"
                )
            
            with metrics_col3:
                total_movements = system_health.get('total_movements', 0)
                st.metric("Total Movements", total_movements)
        
        # Business rules status
        business_rules = validation_report.get('business_rules', {})
        if business_rules:
            st.markdown("**🔧 Business Rules Status:**")
            
            rules_data = []
            for rule_name, rule_config in business_rules.items():
                rules_data.append({
                    "Rule": rule_name.replace('_', ' ').title(),
                    "Status": "✅ Enabled" if rule_config.get('enabled', False) else "❌ Disabled",
                    "Description": rule_config.get('description', 'No description')
                })
            
            if rules_data:
                rules_df = pd.DataFrame(rules_data)
                st.dataframe(rules_df, use_container_width=True)


def show_maintenance_tools():
    """Display maintenance and troubleshooting tools."""
    st.markdown("#### 🔄 Maintenance & Troubleshooting")
    
    api_client = APIClient()
    
    # API connection testing
    st.markdown("**🔌 API Connection Testing**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🏥 Test Health Endpoint"):
            with st.spinner("Testing health endpoint..."):
                health_result = safe_api_call(
                    lambda: api_client.health_check(),
                    "Health endpoint test failed"
                )
                
                if health_result:
                    show_success("Health endpoint is responding correctly")
                else:
                    show_error("Health endpoint is not responding")
    
    with col2:
        if st.button("📊 Test Validation Endpoint"):
            with st.spinner("Testing validation endpoint..."):
                # Test with a simple movement
                test_movement = {
                    "item_id": 1,
                    "movement_type": "move",
                    "from_location_id": 1,
                    "to_location_id": 2,
                    "quantity_moved": 1,
                    "reason": "Maintenance test"
                }
                
                validation_result = safe_api_call(
                    lambda: api_client.validate_movement(test_movement, enforce_strict=False),
                    "Validation endpoint test failed"
                )
                
                if validation_result:
                    show_success("Validation endpoint is responding correctly")
                    with st.expander("📋 Test Result"):
                        st.json(validation_result)
                else:
                    show_error("Validation endpoint is not responding")
    
    # Cache management
    st.markdown("---")
    st.markdown("**🗃️ Cache Management**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🗑️ Clear Movement Cache"):
            # Clear movement-related session state
            keys_to_clear = [key for key in st.session_state.keys() if 'movement' in key.lower()]
            for key in keys_to_clear:
                del st.session_state[key]
            show_success(f"Cleared {len(keys_to_clear)} movement cache entries")
    
    with col2:
        if st.button("🗑️ Clear Validation Cache"):
            # Clear validation-related session state
            keys_to_clear = [key for key in st.session_state.keys() if 'validation' in key.lower()]
            for key in keys_to_clear:
                del st.session_state[key]
            show_success(f"Cleared {len(keys_to_clear)} validation cache entries")
    
    with col3:
        if st.button("🗑️ Clear All Cache"):
            # Clear all session state
            session_keys = list(st.session_state.keys())
            st.session_state.clear()
            show_success(f"Cleared all {len(session_keys)} cache entries")
    
    # System information
    st.markdown("---")
    st.markdown("**ℹ️ System Information**")
    
    if st.button("📋 Show Connection Info"):
        connection_info = api_client.get_connection_info()
        
        with st.expander("🔗 Connection Details", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**Base URL:** {connection_info['base_url']}")
                st.markdown(f"**Timeout:** {connection_info['timeout']} seconds")
            
            with col2:
                connection_status = "🟢 Connected" if connection_info['is_connected'] else "🔴 Disconnected"
                st.markdown(f"**Status:** {connection_status}")
                st.markdown(f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Additional diagnostics
        with st.expander("🔍 Diagnostic Information"):
            st.markdown("**Session State Keys:**")
            session_keys = list(st.session_state.keys())
            if session_keys:
                for key in sorted(session_keys):
                    st.markdown(f"- {key}")
            else:
                st.markdown("_No session state data_")
            
            st.markdown("**API Client Configuration:**")
            st.json({
                "base_url": api_client.base_url,
                "timeout": api_client.timeout,
                "session_configured": api_client.session is not None
            })


# Main execution
if __name__ == "__main__":
    try:
        show_movement_page()
    except Exception as e:
        logger.error(f"Error in movement page: {str(e)}")
        show_error(f"An error occurred: {str(e)}")
        st.info("Please refresh the page or contact support if the problem persists.")