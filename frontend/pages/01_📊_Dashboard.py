"""
Dashboard page for the Home Inventory System.

Displays system overview, statistics, and recent activity.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import logging
from typing import Dict, Any

from utils.api_client import APIClient, APIError
from utils.helpers import (
    safe_api_call, show_error, show_warning, format_datetime,
    safe_currency_format, safe_float_format, safe_int_convert
)
from utils.config import AppConfig
from utils.performance import (
    SessionStateOptimizer, LazyLoader, performance_monitor,
    create_performance_dashboard, optimize_session_state
)
from components.keyboard_shortcuts import (
    enable_keyboard_shortcuts, show_keyboard_shortcuts_help,
    create_action_buttons_row
)

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Dashboard - Home Inventory System",
    page_icon="📊",
    layout="wide"
)

@performance_monitor
def load_dashboard_data() -> Dict[str, Any]:
    """Load data for the dashboard with caching."""
    if 'api_client' not in st.session_state:
        st.session_state.api_client = APIClient()
    
    api_client = st.session_state.api_client
    
    # Check API connection
    if not api_client.health_check():
        show_error("Cannot connect to the API. Please check if the backend is running.")
        return {}
    
    # Use optimized cached loading
    def load_stats():
        return api_client.get_location_stats()
    
    def load_inventory_summary():
        return api_client.get_inventory_summary()
    
    def load_performance_metrics():
        try:
            return api_client.get_performance_metrics()
        except Exception as e:
            # Silently handle performance metrics failure - not critical for dashboard
            logger.debug(f"Performance metrics unavailable: {e}")
            return None
    
    # Load statistics with caching
    stats = SessionStateOptimizer.get_or_compute(
        "dashboard_location_stats",
        load_stats,
        ttl_seconds=300  # Cache for 5 minutes
    )
    
    # Load recent locations (cached)
    locations = SessionStateOptimizer.get_or_compute(
        "dashboard_recent_locations",
        lambda: api_client.get_locations(skip=0, limit=10),
        ttl_seconds=600  # Cache for 10 minutes
    )
    
    # Load category statistics (cached)
    category_stats = SessionStateOptimizer.get_or_compute(
        "dashboard_category_stats",
        lambda: api_client.get_category_stats(),
        ttl_seconds=300  # Cache for 5 minutes
    )
    
    # Load categories for analytics (cached)
    categories_data = SessionStateOptimizer.get_or_compute(
        "dashboard_categories_data",
        lambda: api_client.get_categories(page=1, per_page=100, include_inactive=True),
        ttl_seconds=900  # Cache for 15 minutes
    )
    
    # Load item statistics (cached)
    item_stats = SessionStateOptimizer.get_or_compute(
        "dashboard_item_stats",
        lambda: api_client.get_item_statistics(),
        ttl_seconds=300  # Cache for 5 minutes
    )
    
    # Load inventory summary (cached)
    inventory_summary = SessionStateOptimizer.get_or_compute(
        "dashboard_inventory_summary",
        load_inventory_summary,
        ttl_seconds=300  # Cache for 5 minutes
    )
    
    # Load recent items (cached)
    recent_items = SessionStateOptimizer.get_or_compute(
        "dashboard_recent_items",
        lambda: api_client.get_items(skip=0, limit=10),
        ttl_seconds=600  # Cache for 10 minutes
    )
    
    # Load performance metrics (cached, optional)
    performance_metrics = SessionStateOptimizer.get_or_compute(
        "dashboard_performance_metrics",
        load_performance_metrics,
        ttl_seconds=60  # Cache for 1 minute
    )
    
    return {
        'stats': stats or {},
        'locations': locations or [],
        'category_stats': category_stats or {},
        'categories': categories_data.get('categories', []) if categories_data else [],
        'item_stats': item_stats or {},
        'inventory_summary': inventory_summary or {},
        'recent_items': recent_items or [],
        'performance_metrics': performance_metrics
    }

def create_stats_metrics(stats: Dict[str, Any]):
    """Create metrics display for statistics."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🏠 Total Locations",
            value=stats.get('total_locations', 0),
            help="Total number of locations in your inventory"
        )
    
    with col2:
        st.metric(
            label="🌳 Root Locations", 
            value=stats.get('root_locations', 0),
            help="Top-level locations (usually houses)"
        )
    
    with col3:
        houses = stats.get('by_type', {}).get('house', 0)
        rooms = stats.get('by_type', {}).get('room', 0)
        st.metric(
            label="🏘️ Houses/Rooms",
            value=f"{houses}/{rooms}",
            help="Number of houses and rooms"
        )
    
    with col4:
        containers = stats.get('by_type', {}).get('container', 0)
        shelves = stats.get('by_type', {}).get('shelf', 0)
        st.metric(
            label="📦 Storage Units",
            value=f"{containers}/{shelves}",
            help="Containers and shelves for storage"
        )

def create_item_metrics(item_stats: Dict[str, Any]):
    """Create metrics display for item statistics."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📦 Total Items",
            value=safe_int_convert(item_stats.get('total_items'), 0),
            help="Total number of items in your inventory"
        )
    
    with col2:
        st.metric(
            label="💰 Total Value",
            value=safe_currency_format(item_stats.get('total_value')),
            help="Total value of all items"
        )
    
    with col3:
        # Calculate available items from status distribution
        by_status = item_stats.get('by_status', {})
        available_count = safe_int_convert(by_status.get('available'), 0)
        st.metric(
            label="✅ Available Items",
            value=available_count,
            help="Items currently available for use"
        )
    
    with col4:
        # Calculate in-use items from status distribution
        in_use_count = safe_int_convert(by_status.get('in_use'), 0)
        st.metric(
            label="🔄 In Use Items",
            value=in_use_count,
            help="Items currently being used"
        )

def create_category_metrics(category_stats: Dict[str, Any], categories: list):
    """Create metrics display for category statistics."""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🏷️ Total Categories",
            value=category_stats.get('total_categories', len(categories)),
            help="Total number of categories"
        )
    
    with col2:
        active_categories = len([c for c in categories if c.get('is_active', True)])
        st.metric(
            label="✅ Active Categories", 
            value=active_categories,
            help="Number of active categories"
        )
    
    with col3:
        inactive_categories = len([c for c in categories if not c.get('is_active', True)])
        st.metric(
            label="❌ Inactive Categories",
            value=inactive_categories,
            help="Number of inactive categories"
        )
    
    with col4:
        categories_with_color = len([c for c in categories if c.get('color')])
        st.metric(
            label="🎨 Colored Categories",
            value=categories_with_color,
            help="Categories with assigned colors"
        )

def create_category_visualizations(categories: list):
    """Create category analytics visualizations."""
    if not categories:
        st.info("No category data available for visualizations")
        return
    
    # Category status distribution
    active_count = len([c for c in categories if c.get('is_active', True)])
    inactive_count = len([c for c in categories if not c.get('is_active', True)])
    
    # Create status pie chart
    status_fig = px.pie(
        values=[active_count, inactive_count],
        names=['Active', 'Inactive'],
        title="Category Status Distribution",
        color_discrete_map={'Active': '#28a745', 'Inactive': '#dc3545'}
    )
    status_fig.update_traces(textposition='inside', textinfo='percent+label')
    
    # Color usage analysis
    colored_count = len([c for c in categories if c.get('color')])
    uncolored_count = len(categories) - colored_count
    
    color_usage_fig = px.pie(
        values=[colored_count, uncolored_count],
        names=['With Color', 'No Color'],
        title="Category Color Usage",
        color_discrete_map={'With Color': '#007bff', 'No Color': '#6c757d'}
    )
    color_usage_fig.update_traces(textposition='inside', textinfo='percent+label')
    
    # Category colors visualization (if any categories have colors)
    categories_with_colors = [c for c in categories if c.get('color')]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(status_fig, use_container_width=True)
    
    with col2:
        st.plotly_chart(color_usage_fig, use_container_width=True)
    
    # Color palette visualization
    if categories_with_colors:
        st.subheader("🎨 Category Color Palette")
        
        # Create color swatches
        colors_html = "<div style='display: flex; flex-wrap: wrap; gap: 10px; margin: 10px 0;'>"
        for category in categories_with_colors:
            color = category.get('color', '#000000')
            name = category.get('name', 'Unnamed')
            colors_html += f"""
                <div style='display: flex; align-items: center; background: white; padding: 5px; border-radius: 5px; border: 1px solid #ddd;'>
                    <div style='width: 30px; height: 30px; background-color: {color}; border-radius: 50%; margin-right: 10px; border: 1px solid #ccc;'></div>
                    <span style='font-size: 14px; color: #333;'>{name}</span>
                </div>
            """
        colors_html += "</div>"
        
        st.markdown(colors_html, unsafe_allow_html=True)
        
        # Most common colors
        color_counts = {}
        for category in categories_with_colors:
            color = category.get('color', '#000000')
            color_counts[color] = color_counts.get(color, 0) + 1
        
        if len(color_counts) > 1:
            sorted_colors = sorted(color_counts.items(), key=lambda x: x[1], reverse=True)
            
            st.subheader("📈 Most Used Colors")
            for i, (color, count) in enumerate(sorted_colors[:5]):  # Top 5 colors
                st.markdown(
                    f"<div style='display: flex; align-items: center; margin: 5px 0;'>"
                    f"<div style='width: 20px; height: 20px; background-color: {color}; border-radius: 50%; margin-right: 10px; border: 1px solid #ccc;'></div>"
                    f"<span>{color} - Used by {count} categor{'y' if count == 1 else 'ies'}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
    
    # Category creation timeline (if created_at is available)
    categories_with_dates = [c for c in categories if c.get('created_at')]
    if categories_with_dates:
        st.subheader("📅 Category Creation Timeline")
        
        # Create timeline data
        timeline_data = []
        for category in categories_with_dates:
            try:
                # Convert to datetime and make timezone naive
                created_at = pd.to_datetime(category['created_at'])
                if created_at.tz is not None:
                    created_at = created_at.tz_convert('UTC').tz_localize(None)
                
                # Extract month-year string directly
                month_str = created_at.strftime('%Y-%m')
                
                timeline_data.append({
                    'Date': created_at,
                    'Month': month_str,
                    'Category': category.get('name', 'Unnamed'),
                    'Status': 'Active' if category.get('is_active', True) else 'Inactive'
                })
            except Exception as e:
                logger.debug(f"Failed to parse date for category {category.get('name')}: {e}")
                continue
        
        if timeline_data:
            timeline_df = pd.DataFrame(timeline_data)
            
            # Count categories by month using string month
            monthly_counts = timeline_df.groupby(['Month', 'Status']).size().reset_index(name='Count')
            # Sort by month
            monthly_counts = monthly_counts.sort_values('Month')
            
            timeline_fig = px.bar(
                monthly_counts,
                x='Month',
                y='Count',
                color='Status',
                title='Categories Created Over Time',
                color_discrete_map={'Active': '#28a745', 'Inactive': '#dc3545'}
            )
            timeline_fig.update_layout(xaxis_title='Month', yaxis_title='Categories Created')
            
            st.plotly_chart(timeline_fig, use_container_width=True)

def create_item_visualizations(item_stats: Dict[str, Any], inventory_summary: Dict[str, Any], recent_items: list):
    """Create visualizations for item statistics."""
    # Item status distribution
    if 'status_distribution' in item_stats:
        status_data = item_stats['status_distribution']
        status_fig = px.pie(
            values=list(status_data.values()),
            names=list(status_data.keys()),
            title="Item Status Distribution",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        status_fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(status_fig, use_container_width=True)
    
    # Value distribution
    if 'value_distribution' in item_stats:
        value_data = item_stats['value_distribution']
        value_fig = px.bar(
            x=list(value_data.keys()),
            y=list(value_data.values()),
            title="Items by Value Range",
            labels={'x': 'Value Range', 'y': 'Count'}
        )
        st.plotly_chart(value_fig, use_container_width=True)
    
    # Recent items timeline if available
    if recent_items:
        st.subheader("📅 Recent Items Added")
        items_with_dates = [item for item in recent_items if item.get('created_at')]
        if items_with_dates:
            timeline_data = []
            for item in items_with_dates:
                try:
                    created_at = pd.to_datetime(item['created_at'])
                    if created_at.tz is not None:
                        created_at = created_at.tz_convert('UTC').tz_localize(None)
                    timeline_data.append({
                        'Date': created_at,
                        'Item': item.get('name', 'Unnamed'),
                        'Value': item.get('purchase_price', 0)
                    })
                except:
                    continue
            
            if timeline_data:
                timeline_df = pd.DataFrame(timeline_data)
                timeline_fig = px.scatter(
                    timeline_df,
                    x='Date',
                    y='Value',
                    hover_name='Item',
                    title='Recent Items by Date and Value'
                )
                st.plotly_chart(timeline_fig, use_container_width=True)

def show_recent_items(items: list):
    """Display recent items in a table."""
    if not items:
        st.info("No recent items found")
        return
    
    display_data = []
    for item in items:
        display_data.append({
            'Name': item.get('name', ''),
            'Type': item.get('item_type', '').title(),
            'Status': item.get('status', '').title(),
            'Value': safe_currency_format(item.get('purchase_price')) if item.get('purchase_price') else 'N/A',
            'Location': item.get('location_name', 'Unassigned'),
            'Created': format_datetime(item.get('created_at', '')),
            'ID': item.get('id')
        })
    
    df = pd.DataFrame(display_data)
    
    column_config = {
        "Name": st.column_config.TextColumn("Item Name"),
        "Type": st.column_config.TextColumn("Type"),
        "Status": st.column_config.TextColumn("Status"),
        "Value": st.column_config.TextColumn("Value"),
        "Location": st.column_config.TextColumn("Location"),
        "Created": st.column_config.TextColumn("Created"),
        "ID": st.column_config.NumberColumn("ID", disabled=True)
    }
    
    st.dataframe(
        df,
        column_config=column_config,
        use_container_width=True,
        hide_index=True
    )

def create_enhanced_visualizations(locations: list):
    """Create enhanced visualizations using the new visualization components."""
    if not locations:
        st.info("No location data available for visualizations")
        return
    
    # Try to import visualization components, fallback to basic visualizations if not available
    try:
        from components.visualizations import LocationVisualizationBuilder, create_location_statistics_cards
        
        # Create visualization builder
        viz_builder = LocationVisualizationBuilder(locations)
        
        # Statistics cards
        st.subheader("📈 Key Metrics")
        create_location_statistics_cards(locations)
        
        st.markdown("---")
        
        # Visualization options
        st.subheader("📊 Advanced Visualizations")
        
        viz_tabs = st.tabs([
            "📈 Overview", 
            "🌳 Hierarchy", 
            "📅 Timeline", 
            "📋 Analytics"
        ])
        
        with viz_tabs[0]:
            # Overview visualizations
            col1, col2 = st.columns(2)
            
            with col1:
                st.plotly_chart(
                    viz_builder.create_type_distribution_pie(),
                    use_container_width=True
                )
            
            with col2:
                st.plotly_chart(
                    viz_builder.create_hierarchy_depth_bar(),
                    use_container_width=True
                )
        
        with viz_tabs[1]:
            # Hierarchy visualization
            max_depth = st.selectbox(
                "Select maximum depth to display",
                options=[1, 2, 3, 4, 5],
                index=2,  # Index 2 = value 3
                help="Choose how many levels of the hierarchy to show"
            )
            
            st.plotly_chart(
                viz_builder.create_hierarchy_tree_chart(max_depth=max_depth),
                use_container_width=True
            )
        
        with viz_tabs[2]:
            # Timeline visualization
            st.plotly_chart(
                viz_builder.create_creation_timeline(),
                use_container_width=True
            )
        
        with viz_tabs[3]:
            # Analytics dashboard
            st.plotly_chart(
                viz_builder.create_location_metrics_dashboard(),
                use_container_width=True
            )
    
    except ImportError:
        # Fallback to basic visualizations
        st.warning("Advanced visualizations not available - using basic charts")
        create_basic_location_visualizations(locations)

def create_basic_location_visualizations(locations: list):
    """Create basic location visualizations when advanced components are not available."""
    # Location type distribution
    type_counts = {}
    for loc in locations:
        loc_type = loc.get('location_type', 'unknown')
        type_counts[loc_type] = type_counts.get(loc_type, 0) + 1
    
    if type_counts:
        type_fig = px.pie(
            values=list(type_counts.values()),
            names=list(type_counts.keys()),
            title="Location Types Distribution"
        )
        st.plotly_chart(type_fig, use_container_width=True)
    
    # Creation timeline
    locations_with_dates = [loc for loc in locations if loc.get('created_at')]
    if locations_with_dates:
        timeline_data = []
        for loc in locations_with_dates:
            try:
                created_at = pd.to_datetime(loc['created_at'])
                if created_at.tz is not None:
                    created_at = created_at.tz_convert('UTC').tz_localize(None)
                timeline_data.append({
                    'Date': created_at,
                    'Location': loc.get('name', 'Unnamed'),
                    'Type': loc.get('location_type', 'unknown')
                })
            except:
                continue
        
        if timeline_data:
            timeline_df = pd.DataFrame(timeline_data)
            timeline_fig = px.scatter(
                timeline_df,
                x='Date',
                y='Type',
                hover_name='Location',
                title='Location Creation Timeline'
            )
            st.plotly_chart(timeline_fig, use_container_width=True)

def show_recent_locations(locations: list):
    """Display recent locations in a table."""
    if not locations:
        st.info("No locations found")
        return
    
    # Create display data
    display_data = []
    for loc in locations:
        display_data.append({
            'Name': loc.get('name', ''),
            'Type': loc.get('location_type', '').title(),
            'Path': loc.get('full_path', ''),
            'Created': format_datetime(loc.get('created_at', '')),
            'ID': loc.get('id')
        })
    
    df = pd.DataFrame(display_data)
    
    # Configure columns
    column_config = {
        "Name": st.column_config.TextColumn("Location Name"),
        "Type": st.column_config.TextColumn("Type"),
        "Path": st.column_config.TextColumn("Full Path"),
        "Created": st.column_config.TextColumn("Created"),
        "ID": st.column_config.NumberColumn("ID", disabled=True)
    }
    
    st.dataframe(
        df, 
        column_config=column_config,
        use_container_width=True,
        hide_index=True
    )

def main():
    """Main dashboard page function."""
    st.title("📊 Dashboard")
    st.markdown("System overview and statistics for your Home Inventory System")
    
    # Enable keyboard shortcuts
    enable_keyboard_shortcuts()
    show_keyboard_shortcuts_help()
    
    # Load data
    with st.spinner("Loading dashboard data..."):
        data = load_dashboard_data()
    
    if not data:
        st.stop()
    
    stats = data.get('stats', {})
    locations = data.get('locations', [])
    category_stats = data.get('category_stats', {})
    categories = data.get('categories', [])
    item_stats = data.get('item_stats', {})
    inventory_summary = data.get('inventory_summary', {})
    recent_items = data.get('recent_items', [])
    performance_metrics = data.get('performance_metrics')
    
    # Add performance controls
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.subheader("📈 System Overview")
    
    with col2:
        if st.button("🗑️ Clear Cache"):
            SessionStateOptimizer.invalidate_cache("dashboard_")
            st.success("Dashboard cache cleared!")
            st.rerun()
    
    with col3:
        if st.button("🔧 Optimize"):
            optimize_session_state()
            st.success("Session optimized!")
            st.rerun()
    
    # Create tabs for different metric types
    metric_tabs = st.tabs(["📍 Locations", "📦 Items", "🏷️ Categories"])
    
    with metric_tabs[0]:
        create_stats_metrics(stats)
    
    with metric_tabs[1]:
        create_item_metrics(item_stats)
    
    with metric_tabs[2]:
        create_category_metrics(category_stats, categories)
    
    st.markdown("---")
    
    # Enhanced visualizations section with categories
    # Create main visualization tabs
    main_tabs = st.tabs([
        "📍 Locations", 
        "📦 Items",
        "🏷️ Categories", 
        "📊 Combined Analytics",
        "🚀 Performance"
    ])
    
    with main_tabs[0]:
        st.subheader("📍 Location Analytics")
        create_enhanced_visualizations(locations)
    
    with main_tabs[1]:
        st.subheader("📦 Item Analytics")
        create_item_visualizations(item_stats, inventory_summary, recent_items)
    
    with main_tabs[2]:
        st.subheader("🏷️ Category Analytics") 
        create_category_visualizations(categories)
    
    with main_tabs[3]:
        st.subheader("📊 Combined System Analytics")
        
        # Combined metrics in columns
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "📍 Total Locations",
                stats.get('total_locations', 0),
                help="All locations in the system"
            )
            st.metric(
                "📦 Total Items",
                item_stats.get('total_items', 0),
                help="All items in the system"
            )
            st.metric(
                "🏷️ Total Categories", 
                category_stats.get('total_categories', len(categories)),
                help="All categories in the system"
            )
        
        with col2:
            # Calculate locations with categories
            locations_with_categories = len([l for l in locations if l.get('category_id')])
            st.metric(
                "🔗 Categorized Locations",
                locations_with_categories,
                help="Locations assigned to categories"
            )
            
            # Calculate inventory distribution
            total_inventory_entries = inventory_summary.get('total_entries', 0)
            st.metric(
                "📋 Inventory Entries",
                total_inventory_entries,
                help="Total item-location relationships"
            )
            
            # Calculate utilization rate
            if stats.get('total_locations', 0) > 0:
                utilization_rate = round((locations_with_categories / stats.get('total_locations', 1)) * 100, 1)
                st.metric(
                    "📈 Category Utilization",
                    f"{utilization_rate}%",
                    help="Percentage of locations with assigned categories"
                )
    
    with main_tabs[4]:
        st.subheader("🚀 Performance Metrics")
        
        # Show cache statistics
        cache_stats = SessionStateOptimizer.get_cache_stats()
        perf_col1, perf_col2, perf_col3, perf_col4 = st.columns(4)
        
        with perf_col1:
            st.metric("🗃️ Cache Entries", cache_stats["total_cache_entries"])
        with perf_col2:
            st.metric("✅ Active Entries", cache_stats["active_entries"])
        with perf_col3:
            st.metric("⏰ Expired Entries", cache_stats["expired_entries"])
        with perf_col4:
            st.metric("🔑 Session Keys", len(st.session_state.keys()))
        
        # Performance dashboard
        if st.button("📊 Show Detailed Performance"):
            create_performance_dashboard()
        
        # Backend performance metrics
        if performance_metrics:
            st.markdown("### 🔧 Backend Performance")
            
            # Check if metrics are available
            if performance_metrics.get("cache_stats", {}).get("status") == "unavailable":
                st.info("ℹ️ Backend performance metrics are currently unavailable. This may be normal if the backend is starting up.")
            else:
                with st.expander("Backend Metrics", expanded=False):
                    st.json(performance_metrics)
        
        # Cache management buttons
        perf_actions_col1, perf_actions_col2, perf_actions_col3 = st.columns(3)
        
        with perf_actions_col1:
            if st.button("🔄 Warm Cache"):
                api_client = st.session_state.api_client
                result = api_client.warm_cache()
                if result.get("status") == "unavailable":
                    st.warning("⚠️ Cache warming is currently unavailable")
                else:
                    st.success("Cache warmed successfully!")
                    st.json(result)
        
        with perf_actions_col2:
            if st.button("📈 Create Indexes"):
                api_client = st.session_state.api_client
                result = api_client.create_performance_indexes()
                if result.get("status") == "unavailable":
                    st.warning("⚠️ Performance index creation is currently unavailable")
                else:
                    st.success("Performance indexes created!")
                    st.json(result)
        
        with perf_actions_col3:
            if st.button("🧹 Clear Backend Cache"):
                api_client = st.session_state.api_client
                result = api_client.clear_cache()
                if result.get("status") == "unavailable":
                    st.warning("⚠️ Cache clearing is currently unavailable")
                else:
                    st.success("Backend cache cleared!")
                    st.json(result)
    
    st.markdown("---")
    
    # Recent data section
    recent_tabs = st.tabs(["📍 Recent Locations", "📦 Recent Items"])
    
    with recent_tabs[0]:
        show_recent_locations(locations[:10])  # Show top 10 recent
    
    with recent_tabs[1]:
        show_recent_items(recent_items[:10])  # Show top 10 recent
    
    # Enhanced quick actions
    st.markdown("---")
    st.subheader("⚡ Quick Actions")
    
    quick_actions = {
        'view_locations': {
            'label': '📍 View All Locations',
            'callback': lambda: st.switch_page("pages/02_📍_Locations.py"),
            'help': 'Browse and search all locations (Alt+L)'
        },
        'add_location': {
            'label': '➕ Add New Location',
            'callback': lambda: st.switch_page("pages/03_⚙️_Manage.py"),
            'help': 'Create a new location (Alt+N)'
        },
        'view_items': {
            'label': '📦 View All Items',
            'callback': lambda: st.switch_page("pages/05_📦_Items.py"),
            'help': 'Browse and search all items (Alt+I)'
        },
        'add_item': {
            'label': '📦➕ Add New Item',
            'callback': lambda: (setattr(st.session_state, 'manage_tab', 'Items'), st.switch_page("pages/03_⚙️_Manage.py")),
            'help': 'Create a new inventory item'
        },
        'view_categories': {
            'label': '🏷️ Manage Categories',
            'callback': lambda: st.switch_page("pages/04_🏷️_Categories.py"),
            'help': 'Browse and manage categories (Alt+C)'
        },
        'refresh': {
            'label': '🔄 Refresh Data',
            'callback': lambda: st.rerun(),
            'help': 'Refresh dashboard data (Alt+R)'
        }
    }
    
    create_action_buttons_row(quick_actions, "dashboard_actions")
    
    # System information
    if st.checkbox("🔧 Show System Information"):
        st.markdown("### System Information")
        info_col1, info_col2 = st.columns(2)
        
        with info_col1:
            st.write("**API Configuration:**")
            st.code(f"""
Base URL: {AppConfig.API_BASE_URL}
Timeout: {AppConfig.API_TIMEOUT}s
Debug Mode: {AppConfig.DEBUG}
            """)
        
        with info_col2:
            st.write("**Connection Status:**")
            api_client = st.session_state.get('api_client')
            if api_client:
                connection_info = api_client.get_connection_info()
                st.json(connection_info)

if __name__ == "__main__":
    main()