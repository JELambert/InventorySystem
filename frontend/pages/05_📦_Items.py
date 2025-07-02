"""
Items page for the Home Inventory System.

Browse, search, filter, and manage all inventory items.
"""

import streamlit as st
import pandas as pd
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from utils.api_client import APIClient, APIError
from utils.helpers import (
    safe_api_call, show_error, show_success, show_warning,
    handle_api_error, SessionManager, safe_currency_format, format_datetime,
    safe_strip, safe_string_check, safe_string_or_none
)
from components.keyboard_shortcuts import (
    enable_keyboard_shortcuts, show_keyboard_shortcuts_help,
    create_enhanced_search_box, create_quick_filter_buttons,
    create_pagination_controls, create_bulk_selection_interface,
    create_action_buttons_row
)

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Items - Home Inventory System",
    page_icon="📦",
    layout="wide"
)

def get_item_type_options() -> List[str]:
    """Get available item type options."""
    return [
        "electronics", "furniture", "clothing", "books", "documents", 
        "tools", "kitchen", "decor", "collectibles", "hobby", 
        "office", "personal", "seasonal", "storage", "other"
    ]

def get_condition_options() -> List[str]:
    """Get available condition options."""
    return [
        "excellent", "very_good", "good", "fair", "poor", "for_repair", "not_working"
    ]

def get_status_options() -> List[str]:
    """Get available status options."""
    return [
        "available", "in_use", "reserved", "loaned", "missing", "disposed", "sold"
    ]

def create_search_filters() -> Dict[str, Any]:
    """Create enhanced search and filter controls with semantic search."""
    st.sidebar.subheader("🔍 Smart Search & Filters")
    
    # Semantic Search Toggle
    semantic_enabled = st.sidebar.toggle(
        "🧠 AI-Powered Search",
        value=st.session_state.get("semantic_search_enabled", True),
        help="Use artificial intelligence for natural language search (e.g., 'kitchen tools under $50')"
    )
    st.session_state.semantic_search_enabled = semantic_enabled
    
    # Enhanced search box with semantic capabilities
    if semantic_enabled:
        search_placeholder = "Try natural language: 'blue electronics', 'camping gear in garage'..."
        search_help = "AI-powered search understands natural language queries"
    else:
        search_placeholder = "Enter item name, description, brand, or model..."
        search_help = "Traditional keyword search in item fields"
    
    search_text = create_enhanced_search_box(
        placeholder=search_placeholder,
        key="item_search",
        help_text=search_help
    )
    
    # Search mode indicator
    if search_text:
        search_mode = "🧠 Smart Search" if semantic_enabled else "📝 Keyword Search"
        st.sidebar.caption(f"Using: {search_mode}")
    
    # Advanced search options
    with st.sidebar.expander("🔧 Search Options"):
        if not semantic_enabled:
            case_sensitive = st.checkbox(
                "Case sensitive search",
                help="Enable case-sensitive search"
            )
            search_descriptions = st.checkbox(
                "Include descriptions",
                value=True,
                help="Search in item descriptions"
            )
            search_notes = st.checkbox(
                "Include notes",
                help="Search in item notes"
            )
        else:
            # Semantic search options - set default values for traditional search variables
            case_sensitive = False
            search_descriptions = True
            search_notes = False
            
            certainty_threshold = st.slider(
                "Search Sensitivity",
                min_value=0.5,
                max_value=1.0,
                value=0.7,
                step=0.05,
                help="Higher values = more precise matches, lower values = more flexible matches"
            )
            st.session_state.semantic_certainty = certainty_threshold
    
    # Debug Information (Development Mode)
    if st.sidebar.checkbox("🐛 Debug Mode", help="Show technical details for troubleshooting"):
        st.session_state.debug_mode = True
        with st.sidebar.expander("🔍 Debug Info", expanded=True):
            st.caption("**Search Configuration:**")
            st.text(f"Mode: {'AI-powered' if semantic_enabled else 'Traditional'}")
            st.text(f"Query: '{search_text}'")
            if semantic_enabled:
                st.text(f"Sensitivity: {st.session_state.get('semantic_certainty', 0.7):.0%}")
    else:
        st.session_state.debug_mode = False
    
    # Quick filter buttons
    st.sidebar.subheader("⚡ Quick Filters")
    
    quick_filter_options = {
        'electronics': '📱 Electronics',
        'furniture': '🪑 Furniture',
        'clothing': '👕 Clothing',
        'books': '📚 Books',
        'tools': '🔧 Tools',
        'kitchen': '🍴 Kitchen'
    }
    
    current_filter = st.session_state.get('item_type_filter', 'all')
    selected_filter = create_quick_filter_buttons(
        current_filter,
        quick_filter_options,
        "item_type"
    )
    
    if selected_filter != current_filter:
        st.session_state.item_type_filter = selected_filter
    
    # Advanced filters
    st.sidebar.subheader("🎛️ Advanced Filters")
    
    # Item type filter
    selected_types = st.multiselect(
        "Item Types",
        options=get_item_type_options(),
        help="Filter by item type"
    )
    
    # Condition filter
    selected_conditions = st.multiselect(
        "Condition",
        options=get_condition_options(),
        help="Filter by item condition"
    )
    
    # Status filter
    selected_statuses = st.multiselect(
        "Status",
        options=get_status_options(),
        help="Filter by item status"
    )
    
    # Category filter (load from API)
    api_client = APIClient()
    categories_data = safe_api_call(
        api_client.get_categories,
        error_message="Failed to load categories for filtering"
    )
    
    category_options = []
    if categories_data and 'items' in categories_data:
        category_options = [(cat['name'], cat['id']) for cat in categories_data['items']]
    
    selected_category_ids = []
    if category_options:
        selected_categories = st.multiselect(
            "Categories",
            options=[name for name, _ in category_options],
            help="Filter by category"
        )
        selected_category_ids = [id for name, id in category_options if name in selected_categories]
    
    # Location filter (load from API)
    locations_data = safe_api_call(
        lambda: api_client.get_locations(skip=0, limit=1000),
        error_message="Failed to load locations for filtering"
    )
    
    location_options = []
    if locations_data:
        location_options = [(loc['name'], loc['id']) for loc in locations_data]
    
    selected_location_ids = []
    if location_options:
        selected_locations = st.multiselect(
            "Locations",
            options=[name for name, _ in location_options],
            help="Filter by location where items are stored"
        )
        selected_location_ids = [id for name, id in location_options if name in selected_locations]
    
    # Special location filters
    col1, col2 = st.columns(2)
    with col1:
        show_unassigned = st.checkbox(
            "Items without location",
            help="Show items that are not assigned to any location"
        )
    with col2:
        show_multiple_locations = st.checkbox(
            "Items in multiple locations",
            help="Show items that are stored in multiple locations"
        )
    
    # Value range filter
    with st.expander("💰 Value Range"):
        col1, col2 = st.columns(2)
        with col1:
            min_value = st.number_input(
                "Min Value ($)",
                min_value=0.0,
                value=0.0,
                help="Minimum item value"
            )
        with col2:
            max_value = st.number_input(
                "Max Value ($)",
                min_value=0.0,
                value=10000.0,
                help="Maximum item value"
            )
    
    # Date range filter
    with st.expander("📅 Purchase Date Range"):
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "From Date",
                help="Filter items purchased after this date"
            )
        with col2:
            end_date = st.date_input(
                "To Date",
                help="Filter items purchased before this date"
            )
    
    # Tags filter
    tag_filter = st.text_input(
        "Tags (comma-separated)",
        help="Filter by tags (e.g., 'important, fragile')"
    )
    
    return {
        "search_text": search_text or "",
        "case_sensitive": case_sensitive,
        "search_descriptions": search_descriptions,
        "search_notes": search_notes,
        "item_types": (selected_types or []) or ([selected_filter] if selected_filter != 'all' else []),
        "conditions": selected_conditions or [],
        "statuses": selected_statuses or [],
        "category_ids": selected_category_ids or [],
        "location_ids": selected_location_ids or [],
        "show_unassigned": show_unassigned,
        "show_multiple_locations": show_multiple_locations,
        "min_value": min_value if min_value > 0 else None,
        "max_value": max_value if max_value < 10000 else None,
        "start_date": start_date,
        "end_date": end_date,
        "tags": [safe_strip(tag) for tag in (tag_filter or "").split(",") if safe_string_check(tag)] if tag_filter else []
    }

def create_item_dataframe(items: List[Dict], show_inventory: bool = True) -> pd.DataFrame:
    """Create a pandas DataFrame from items data with inventory information."""
    if not items:
        return pd.DataFrame()
    
    # Extract basic item data
    df_data = []
    for item in items:
        row = {
            "ID": item.get("id"),
            "Name": item.get("name", ""),
            "Type": item.get("item_type", "").replace("_", " ").title(),
            "Brand": item.get("brand", ""),
            "Model": item.get("model", ""),
            "Condition": item.get("condition", "").replace("_", " ").title(),
            "Status": item.get("status", "").replace("_", " ").title(),
            "Current Value": safe_currency_format(item.get('current_value')) if item.get('current_value') else "",
            "Purchase Price": safe_currency_format(item.get('purchase_price')) if item.get('purchase_price') else "",
            "Purchase Date": item.get("purchase_date", "").split("T")[0] if item.get("purchase_date") else "",
            "Category": item.get("category", {}).get("name", "") if item.get("category") else "",
            "Tags": item.get("tags", ""),
            "Serial Number": item.get("serial_number", ""),
            "Description": (item.get("description") or "")[:100] + "..." if len(item.get("description") or "") > 100 else (item.get("description") or ""),
        }
        
        # Add inventory information if requested
        if show_inventory:
            inventory_entries = item.get("inventory_entries", [])
            if inventory_entries:
                locations = []
                total_quantity = 0
                for entry in inventory_entries:
                    if entry.get("location"):
                        locations.append(f"{entry['location']['name']} ({entry.get('quantity', 1)})")
                        total_quantity += entry.get('quantity', 1)
                
                row["Locations"] = ", ".join(locations)
                row["Total Quantity"] = total_quantity
            else:
                row["Locations"] = "Not in inventory"
                row["Total Quantity"] = 0
        
        df_data.append(row)
    
    df = pd.DataFrame(df_data)
    
    # Ensure consistent column order
    base_columns = ["ID", "Name", "Type", "Brand", "Model", "Condition", "Status"]
    if show_inventory:
        base_columns.extend(["Locations", "Total Quantity"])
    base_columns.extend(["Current Value", "Purchase Price", "Purchase Date", "Category", "Tags", "Serial Number", "Description"])
    
    # Reorder columns and fill missing ones
    for col in base_columns:
        if col not in df.columns:
            df[col] = ""
    
    return df[base_columns]

def display_item_details(item: Dict):
    """Display detailed view of a specific item."""
    st.subheader(f"📦 {item.get('name', 'Unknown Item')}")
    
    # Basic information
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Type", item.get("item_type", "").replace("_", " ").title())
        st.metric("Condition", item.get("condition", "").replace("_", " ").title())
        st.metric("Status", item.get("status", "").replace("_", " ").title())
    
    with col2:
        if item.get("current_value"):
            st.metric("Current Value", safe_currency_format(item['current_value']))
        if item.get("purchase_price"):
            st.metric("Purchase Price", safe_currency_format(item['purchase_price']))
        if item.get("purchase_date"):
            st.metric("Purchase Date", item["purchase_date"].split("T")[0])
    
    with col3:
        if item.get("brand"):
            st.metric("Brand", item["brand"])
        if item.get("model"):
            st.metric("Model", item["model"])
        if item.get("serial_number"):
            st.metric("Serial Number", item["serial_number"])
    
    # Description and notes
    if item.get("description"):
        st.subheader("Description")
        st.write(item["description"])
    
    if item.get("notes"):
        st.subheader("Notes")
        st.write(item["notes"])
    
    # Tags
    if item.get("tags"):
        st.subheader("Tags")
        tags = [safe_strip(tag) for tag in safe_strip(item["tags"]).split(",") if safe_string_check(tag)]
        tag_cols = st.columns(len(tags)) if tags else []
        for i, tag in enumerate(tags):
            with tag_cols[i]:
                st.write(f"`{tag}`")
    
    # Inventory information
    st.subheader("📍 Location Information")
    
    # Use inventory data from item if available, otherwise make API call
    inventory_entries = item.get("inventory_entries", [])
    
    if not inventory_entries:
        # Fallback to API call if inventory data not included
        api_client = APIClient()
        inventory_entries = safe_api_call(
            lambda: api_client.get_inventory(item_id=item.get("id")),
            "Failed to load item inventory"
        ) or []
    
    if inventory_entries:
        location_df_data = []
        total_quantity = 0
        
        for entry in inventory_entries:
            quantity = entry.get("quantity", 1)
            total_quantity += quantity
            
            location_name = "Unknown Location"
            if entry.get("location"):
                location_name = entry["location"].get("name", "Unknown Location")
            elif entry.get("location_id"):
                # Try to get location name if only ID is available
                try:
                    api_client = APIClient()
                    location = api_client.get_location(entry["location_id"])
                    location_name = location.get("name", f"Location {entry['location_id']}")
                except:
                    location_name = f"Location {entry['location_id']}"
            
            location_df_data.append({
                "Location": location_name,
                "Quantity": quantity,
                "Last Updated": entry.get("updated_at", "").split("T")[0] if entry.get("updated_at") else "",
                "Total Value": safe_currency_format(entry.get('total_value')) if entry.get('total_value') else ""
            })
        
        if location_df_data:
            # Show summary
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Quantity", total_quantity)
            with col2:
                st.metric("Locations", len(inventory_entries))
            
            # Show detailed table
            location_df = pd.DataFrame(location_df_data)
            st.dataframe(location_df, use_container_width=True)
        else:
            st.info("This item is not currently in any location inventory.")
    else:
        st.info("No location information available for this item.")


def show_similar_items(item: Dict):
    """Display items similar to the selected item using semantic search."""
    st.markdown(f"### Items Similar to '{item.get('name', 'Unknown')}'")
    
    api_client = APIClient()
    
    with st.spinner("Finding similar items using AI..."):
        # Get similar items from semantic search
        similar_result = safe_api_call(
            lambda: api_client.get_similar_items(item.get('id'), limit=10),
            error_message="Failed to find similar items"
        )
        
        if similar_result and similar_result.get("similar_items"):
            similar_items = similar_result["similar_items"]
            semantic_available = similar_result.get("semantic_available", False)
            
            if not semantic_available:
                st.warning("⚠️ AI-powered similarity search is currently unavailable. Showing alternative suggestions.")
            else:
                st.success(f"🧠 Found {len(similar_items)} similar items using AI analysis")
            
            # Display similar items
            for idx, similar_item in enumerate(similar_items):
                item_data = similar_item.get("item_data", {})
                score = similar_item.get("score", 0.0)
                
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.subheader(item_data.get("name", "Unknown Item"))
                        if item_data.get("description"):
                            st.write(f"**Description:** {item_data['description']}")
                        
                        # Show key attributes
                        attrs = []
                        if item_data.get("item_type"):
                            attrs.append(f"Type: {item_data['item_type'].replace('_', ' ').title()}")
                        if item_data.get("brand"):
                            attrs.append(f"Brand: {item_data['brand']}")
                        if item_data.get("category_name"):
                            attrs.append(f"Category: {item_data['category_name']}")
                        
                        if attrs:
                            st.write(" • ".join(attrs))
                    
                    with col2:
                        if semantic_available:
                            similarity_pct = score * 100
                            st.metric("Similarity", f"{similarity_pct:.0f}%")
                        else:
                            st.write("**Alternative**")
                    
                    with col3:
                        if st.button(f"View Details", key=f"similar_detail_{item_data.get('id', idx)}"):
                            # Get full item details
                            try:
                                full_item = api_client.get_item(item_data['id'])
                                st.session_state.selected_item = full_item
                                st.session_state.show_item_details = True
                                st.session_state.show_similar_items = False
                                if 'similar_to_item' in st.session_state:
                                    del st.session_state.similar_to_item
                                st.rerun()
                            except:
                                show_error("Failed to load item details")
        else:
            st.info("🤔 No similar items found. This might be a unique item!")
            
            # Suggest alternative search
            if item.get("item_type"):
                item_type = item["item_type"].replace("_", " ").title()
                st.write(f"**Suggestion:** Try searching for other {item_type} items using the main search.")


def show_items_page():
    """Main items page display."""
    # Page header
    st.title("📦 Items Management")
    st.markdown("Browse, search, and manage all inventory items")
    
    # Initialize session manager
    session = SessionManager()
    api_client = APIClient()
    
    # Enable keyboard shortcuts
    enable_keyboard_shortcuts()
    
    # Create main layout
    main_content = st.container()
    
    with main_content:
        # Action buttons row
        action_col1, action_col2, action_col3, action_col4, action_col5 = st.columns([2, 1, 1, 1, 1])
        
        with action_col1:
            st.markdown("### Quick Actions")
        
        with action_col2:
            if st.button("➕ Add Item", type="primary", help="Create a new item"):
                st.session_state.show_create_form = True
        
        with action_col3:
            if st.button("🔄 Refresh", help="Reload items data"):
                if 'items_cache' in st.session_state:
                    del st.session_state.items_cache
                st.rerun()
        
        with action_col4:
            if st.button("📊 Statistics", help="View item statistics"):
                st.session_state.show_statistics = True
        
        with action_col5:
            if st.button("🔍 AI Status", help="Check semantic search availability"):
                st.session_state.show_search_health = True
        
        # Statistics modal
        if st.session_state.get('show_statistics', False):
            with st.expander("📊 Item Statistics", expanded=True):
                stats = safe_api_call(
                    api_client.get_item_statistics,
                    error_message="Failed to load item statistics"
                )
                
                if stats:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Items", stats.get("total_items", 0))
                    with col2:
                        st.metric("Total Value", safe_currency_format(stats.get('total_value')))
                    with col3:
                        st.metric("Available Items", stats.get("available_items", 0))
                    with col4:
                        st.metric("Categories", stats.get("total_categories", 0))
                
                if st.button("Close Statistics"):
                    st.session_state.show_statistics = False
                    st.rerun()
        
        # Search health check modal
        if st.session_state.get('show_search_health', False):
            with st.expander("🔍 AI Search System Status", expanded=True):
                st.markdown("### Semantic Search Health Check")
                
                # Test API connectivity
                with st.spinner("Checking AI search system..."):
                    health_result = safe_api_call(
                        lambda: api_client.get_search_health(),
                        error_message="Failed to check search health"
                    )
                
                if health_result:
                    status = health_result.get("status", "unknown")
                    weaviate_available = health_result.get("weaviate_available", False)
                    semantic_search = health_result.get("semantic_search", False)
                    
                    if status == "healthy" and weaviate_available:
                        st.success("✅ AI search system is fully operational!")
                        st.info(f"🧠 Weaviate: Connected\n🔗 Semantic Search: Available")
                    elif status == "partial":
                        st.warning("⚠️ AI search system is partially available")
                        st.info(f"🧠 Weaviate: {'Connected' if weaviate_available else 'Disconnected'}\n🔗 Semantic Search: {'Available' if semantic_search else 'Unavailable'}")
                    else:
                        st.error("❌ AI search system is unavailable")
                        st.info("💡 Falling back to traditional keyword search")
                        
                        if "error" in health_result:
                            st.error(f"Error details: {health_result['error']}")
                else:
                    st.error("❌ Unable to check AI search system status")
                    st.info("This likely means the backend search endpoints are not accessible")
                
                # Show backend endpoint info
                st.markdown("### Debug Information")
                st.code(f"""
Backend API: {api_client.base_url}
Search Endpoints:
- /api/v1/search/semantic
- /api/v1/search/hybrid  
- /api/v1/search/health
- /api/v1/search/similar/{{item_id}}
                """)
                
                # Test basic connectivity
                st.markdown("### Connectivity Test")
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("🏥 Test Backend Health"):
                        with st.spinner("Testing backend..."):
                            try:
                                response = api_client._make_request("GET", "")
                                if response:
                                    st.success("✅ Backend is accessible")
                                else:
                                    st.error("❌ Backend not responding")
                            except Exception as e:
                                st.error(f"❌ Backend error: {e}")
                
                with col2:
                    if st.button("🔍 Test Search Endpoint"):
                        with st.spinner("Testing search endpoint..."):
                            try:
                                test_result = api_client.get_search_health()
                                if test_result:
                                    st.success("✅ Search endpoint accessible")
                                    st.json(test_result)
                                else:
                                    st.error("❌ Search endpoint not accessible")
                            except Exception as e:
                                st.error(f"❌ Search endpoint error: {e}")
                
                if st.button("Close Health Check"):
                    st.session_state.show_search_health = False
                    st.rerun()
        
        # Get search filters
        filters = create_search_filters()
        
        # Create cache key based on search parameters to detect changes
        current_semantic_enabled = st.session_state.get("semantic_search_enabled", False)
        search_text = filters["search_text"]
        certainty = st.session_state.get("semantic_certainty", 0.7)
        
        # Create cache key including all search parameters
        cache_key_parts = [
            str(current_semantic_enabled),
            search_text or "",
            str(certainty),
            str(sorted(filters.get("item_types", []))),
            str(sorted(filters.get("conditions", []))),
            str(sorted(filters.get("statuses", []))),
            str(sorted(filters.get("category_ids", [])))
        ]
        current_cache_key = "|".join(cache_key_parts)
        
        # Check if search parameters changed - clear cache if so
        last_cache_key = st.session_state.get("current_cache_key", None)
        last_semantic_enabled = st.session_state.get("last_semantic_enabled", None)
        
        if (last_cache_key is not None and current_cache_key != last_cache_key) or \
           (last_semantic_enabled is not None and current_semantic_enabled != last_semantic_enabled):
            # Search parameters or mode changed - clear cache
            if 'items_cache' in st.session_state:
                del st.session_state.items_cache
            
            # Show appropriate message
            if last_semantic_enabled is not None and current_semantic_enabled != last_semantic_enabled:
                st.info(f"🔄 Search mode changed to {'AI-powered' if current_semantic_enabled else 'traditional'} - refreshing results")
            elif search_text:
                st.info(f"🔍 Search updated - finding results for: '{search_text}'")
        
        st.session_state.current_cache_key = current_cache_key
        st.session_state.last_semantic_enabled = current_semantic_enabled
        
        # Fetch items data
        if 'items_cache' not in st.session_state:
            with st.spinner("Loading items..."):
                # Determine search type and build query
                semantic_enabled = st.session_state.get("semantic_search_enabled", False)
                search_text = filters["search_text"]
                
                if semantic_enabled:
                    # Use AI-powered search (semantic or hybrid depending on filters)
                    certainty = st.session_state.get("semantic_certainty", 0.7)
                    
                    # Build filters for hybrid search (with null safety)
                    search_filters = {}
                    item_types = filters.get("item_types") or []
                    if item_types:
                        search_filters["item_type"] = item_types[0]
                    conditions = filters.get("conditions") or []
                    if conditions:
                        search_filters["condition"] = conditions[0]
                    statuses = filters.get("statuses") or []
                    if statuses:
                        search_filters["status"] = statuses[0]
                    category_ids = filters.get("category_ids") or []
                    if category_ids:
                        search_filters["category_id"] = category_ids[0]
                    
                    # Use search text or wildcard for "find all" semantic search
                    query = search_text if search_text else "*"
                    
                    # Choose appropriate API call based on filters
                    if search_filters:
                        # Use hybrid search when filters are applied
                        st.info(f"🧠 Performing AI hybrid search for: '{query}' with filters (sensitivity: {certainty:.0%})")
                        search_result = safe_api_call(
                            lambda: api_client.hybrid_search(
                                query=query,
                                filters=search_filters,
                                limit=100,
                                certainty=certainty
                            ),
                            error_message="❌ Hybrid search API failed - falling back to traditional search"
                        )
                    else:
                        # Use pure semantic search when no filters
                        st.info(f"🧠 Performing AI semantic search for: '{query}' (sensitivity: {certainty:.0%})")
                        search_result = safe_api_call(
                            lambda: api_client.semantic_search(
                                query=query,
                                limit=100,
                                certainty=certainty
                            ),
                            error_message="❌ Semantic search API failed - falling back to traditional search"
                        )
                    
                    if search_result and isinstance(search_result, dict) and search_result.get("results"):
                        # Extract item data from semantic search results (handles nested .item structure)
                        items_data = []
                        results = search_result.get("results", [])
                        
                        for result in results:
                            if isinstance(result, dict) and "item" in result:
                                # Semantic search result format: {"item": {...}, "score": 0.8, "match_type": "semantic"}
                                item_data = result["item"]
                                # Add semantic search metadata to item for display
                                if "score" in result:
                                    item_data["_semantic_score"] = result["score"]
                                if "match_type" in result:
                                    item_data["_match_type"] = result["match_type"]
                                items_data.append(item_data)
                            else:
                                # Traditional search result format (direct item object)
                                items_data.append(result)
                        
                        # Add search metadata to session state
                        st.session_state.search_metadata = {
                            "search_type": "semantic" if not search_filters else "hybrid",
                            "total_results": search_result.get("total_results", len(items_data) if items_data else 0),
                            "semantic_enabled": search_result.get("semantic_enabled", True),
                            "fallback_used": search_result.get("fallback_used", False),
                            "search_time_ms": search_result.get("search_time_ms", 0),
                            "query": query,
                            "certainty": certainty,
                            "api_response_keys": list(search_result.keys()) if search_result else []
                        }
                        
                        # Debug information
                        if st.session_state.get("debug_mode"):
                            st.success(f"✅ Search completed: {len(items_data) if items_data else 0} items found")
                            st.info(f"📊 API Response: {st.session_state.search_metadata}")
                        
                        # Enrich with inventory data if needed
                        for item in (items_data or []):
                            if "inventory_entries" not in item or item.get("inventory_entries") is None:
                                try:
                                    inventory_entries = api_client.get_inventory(item_id=item.get("id"))
                                    item["inventory_entries"] = inventory_entries or []
                                except:
                                    item["inventory_entries"] = []
                    else:
                        # Fallback to traditional search if semantic search fails
                        st.warning("⚠️ AI search unavailable - using traditional keyword search")
                        
                        # Build proper query params for traditional search
                        query_params = {"limit": 100}
                        if search_text:
                            query_params["search"] = search_text
                        if search_filters.get("item_type"):
                            query_params["item_type"] = search_filters["item_type"]
                        if search_filters.get("condition"):
                            query_params["condition"] = search_filters["condition"]
                        if search_filters.get("status"):
                            query_params["status"] = search_filters["status"]
                        if search_filters.get("category_id"):
                            query_params["category_id"] = search_filters["category_id"]
                        
                        items_data = safe_api_call(
                            lambda: api_client.get_items_with_inventory(**query_params),
                            error_message="Failed to load items data"
                        )
                        
                        # Ensure items_data is a list even if API call failed
                        if items_data is None:
                            items_data = []
                            
                        st.session_state.search_metadata = {
                            "search_type": "traditional_fallback",
                            "semantic_available": False,
                            "query": search_text or ""
                        }
                else:
                    # Traditional search (with null safety)
                    query_params = {}
                    if search_text:
                        query_params["search"] = search_text
                    item_types = filters.get("item_types") or []
                    if item_types:
                        query_params["item_type"] = item_types[0]
                    conditions = filters.get("conditions") or []
                    if conditions:
                        query_params["condition"] = conditions[0]
                    statuses = filters.get("statuses") or []
                    if statuses:
                        query_params["status"] = statuses[0]
                    category_ids = filters.get("category_ids") or []
                    if category_ids:
                        query_params["category_id"] = category_ids[0]
                    
                    items_data = safe_api_call(
                        lambda: api_client.get_items_with_inventory(**query_params),
                        error_message="Failed to load items data"
                    )
                    
                    # Ensure items_data is a list even if API call failed
                    if items_data is None:
                        items_data = []
                    
                    st.session_state.search_metadata = {
                        "search_type": "traditional",
                        "semantic_available": True,
                        "query": search_text or ""
                    }
                
                st.session_state.items_cache = items_data or []
        
        items = st.session_state.items_cache
        
        # Apply client-side filters (for filters not supported by API)
        try:
            filtered_items = items or []
        except Exception as e:
            st.error(f"Debug: Error with items assignment: {e}")
            filtered_items = []
        
        # Filter by multiple types/conditions/statuses if specified (with null safety)
        try:
            item_types = filters.get("item_types") or []
            if len(item_types) > 1:
                filtered_items = [item for item in filtered_items if item.get("item_type") in item_types]
            
            conditions = filters.get("conditions") or []
            if len(conditions) > 1:
                filtered_items = [item for item in filtered_items if item.get("condition") in conditions]
            
            statuses = filters.get("statuses") or []
            if len(statuses) > 1:
                filtered_items = [item for item in filtered_items if item.get("status") in statuses]
            
            # Filter by multiple categories
            category_ids = filters.get("category_ids") or []
            if len(category_ids) > 1:
                filtered_items = [item for item in filtered_items 
                                if item.get("category", {}).get("id") in category_ids]
        except Exception as e:
            st.error(f"Debug: Error in filter processing: {e}")
            st.error(f"Debug: filters = {filters}")
            filtered_items = filtered_items or []
        
        # Filter by value range
        if filters["min_value"] is not None or filters["max_value"] is not None:
            filtered_items = [item for item in filtered_items 
                            if (filters["min_value"] is None or (item.get("current_value", 0) >= filters["min_value"]))
                            and (filters["max_value"] is None or (item.get("current_value", 0) <= filters["max_value"]))]
        
        # Filter by tags
        if filters["tags"]:
            filtered_items = [item for item in filtered_items 
                            if any(tag.lower() in (item.get("tags", "")).lower() for tag in filters["tags"])]
        
        # Filter by location-based criteria
        if filters["location_ids"]:
            filtered_items = [item for item in filtered_items 
                            if any(entry.get('location_id') in filters["location_ids"] 
                                  for entry in item.get('inventory_entries', []))]
        
        # Filter items without location assignments
        try:
            if filters["show_unassigned"]:
                filtered_items = [item for item in filtered_items 
                                if not item.get('inventory_entries', [])]
            
            # Filter items in multiple locations
            if filters["show_multiple_locations"]:
                # Add extra safety for inventory_entries len() call
                safe_filtered_items = []
                for item in filtered_items:
                    try:
                        inventory_entries = item.get('inventory_entries')
                        if inventory_entries is None:
                            inventory_entries = []
                        if len(inventory_entries) > 1:
                            safe_filtered_items.append(item)
                    except Exception as inner_e:
                        st.error(f"Debug: Error processing item {item.get('id', 'unknown')}: {inner_e}")
                        # Include item in results to avoid hiding it due to processing error
                        safe_filtered_items.append(item)
                filtered_items = safe_filtered_items
        except Exception as e:
            st.error(f"Debug: Error in location filtering: {e}")
            # Keep original filtered_items if location filtering fails
        
        # Display search metadata and results
        search_metadata = st.session_state.get("search_metadata", {})
        
        if search_metadata and search_metadata.get("query"):
            # Show search type and confidence
            search_type = search_metadata.get("search_type", "traditional")
            query = search_metadata.get("query", "")
            
            if search_type in ["semantic", "hybrid"]:
                certainty = search_metadata.get("certainty", 0.7)
                st.success(f"🧠 **AI Search Results** for '{query}' (confidence: {certainty:.0%})")
                
                if search_metadata.get("total_count", 0) > len(filtered_items):
                    st.info(f"Showing {len(filtered_items)} of {search_metadata['total_count']} semantic matches after filtering")
            elif search_type == "traditional_fallback":
                st.warning(f"⚠️ **Fallback to Keyword Search** for '{query}' (AI search unavailable)")
            elif search_type == "traditional":
                if query:
                    st.info(f"📝 **Keyword Search Results** for '{query}'")
        
        st.markdown(f"**Found {len(filtered_items)} items**")
        
        if filtered_items:
            # Create dataframe for display
            items_df = create_item_dataframe(filtered_items)
            
            # Display mode selection
            col1, col2 = st.columns([3, 1])
            with col2:
                display_mode = st.selectbox(
                    "Display Mode",
                    ["Table", "Cards", "Details"],
                    help="Choose how to display items"
                )
            
            if display_mode == "Table":
                # Table view with selection
                selected_items = st.dataframe(
                    items_df,
                    use_container_width=True,
                    hide_index=True,
                    selection_mode="multi-row",
                    on_select="rerun"
                )
                
                # Handle row selection for actions
                if hasattr(selected_items, 'selection') and selected_items.selection.rows:
                    selected_indices = selected_items.selection.rows
                    st.info(f"Selected {len(selected_indices)} items")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("📝 Edit Selected"):
                            st.session_state.selected_items = [filtered_items[i] for i in selected_indices]
                            st.session_state.show_bulk_edit = True
                    
                    with col2:
                        if st.button("🗑️ Delete Selected"):
                            st.session_state.selected_items = [filtered_items[i] for i in selected_indices]
                            st.session_state.show_delete_confirm = True
                    
                    with col3:
                        if st.button("📍 Move Selected"):
                            st.session_state.selected_items = [filtered_items[i] for i in selected_indices]
                            st.session_state.show_move_form = True
            
            elif display_mode == "Cards":
                # Card view
                cols_per_row = 3
                for i in range(0, len(filtered_items), cols_per_row):
                    cols = st.columns(cols_per_row)
                    for j, col in enumerate(cols):
                        if i + j < len(filtered_items):
                            item = filtered_items[i + j]
                            with col:
                                with st.container(border=True):
                                    st.subheader(item.get("name", "Unknown"))
                                    st.write(f"**Type:** {item.get('item_type', '').replace('_', ' ').title()}")
                                    st.write(f"**Status:** {item.get('status', '').replace('_', ' ').title()}")
                                    
                                    # Show inventory information with debugging
                                    try:
                                        inventory_entries = item.get("inventory_entries") or []
                                        if inventory_entries:
                                            total_qty = sum(entry.get('quantity', 1) for entry in inventory_entries)
                                            if len(inventory_entries) == 1:
                                                location_name = inventory_entries[0].get('location', {}).get('name', 'Unknown')
                                                st.write(f"**Location:** {location_name} (Qty: {total_qty})")
                                            else:
                                                st.write(f"**Locations:** {len(inventory_entries)} locations (Total: {total_qty})")
                                        else:
                                            st.write("**Location:** Not assigned")
                                    except Exception as inventory_error:
                                        st.error(f"Debug: Error displaying inventory for item {item.get('id', 'unknown')}: {inventory_error}")
                                        st.write("**Location:** Error loading location data")
                                    
                                    if item.get("current_value"):
                                        st.write(f"**Value:** {safe_currency_format(item['current_value'])}")
                                    
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        if st.button("👁️ Details", key=f"view_{item.get('id')}"):
                                            st.session_state.selected_item = item
                                            st.session_state.show_item_details = True
                                    
                                    with col2:
                                        if st.button("🔍 Similar", key=f"similar_{item.get('id')}"):
                                            st.session_state.similar_to_item = item
                                            st.session_state.show_similar_items = True
            
            elif display_mode == "Details":
                # Detailed list view
                item_selection = st.selectbox(
                    "Select an item to view details:",
                    options=range(len(filtered_items)),
                    format_func=lambda i: f"{filtered_items[i].get('name', 'Unknown')} - {filtered_items[i].get('item_type', '').replace('_', ' ').title()}",
                    key="item_detail_selector"
                )
                
                if item_selection is not None:
                    display_item_details(filtered_items[item_selection])
        
        else:
            st.info("No items found matching the current filters.")
            if st.button("Clear All Filters"):
                if 'items_cache' in st.session_state:
                    del st.session_state.items_cache
                st.rerun()

# Modal dialogs and forms
def show_modals():
    """Display modal dialogs based on session state."""
    # Item creation modal
    if st.session_state.get('show_create_form', False):
        with st.expander("➕ Create New Item", expanded=True):
            show_item_creation_form()
            if st.button("Cancel Creation"):
                st.session_state.show_create_form = False
                st.rerun()
    
    # Item details modal
    if st.session_state.get('show_item_details', False) and st.session_state.get('selected_item'):
        with st.expander("📦 Item Details", expanded=True):
            display_item_details(st.session_state.selected_item)
            if st.button("Close Details"):
                st.session_state.show_item_details = False
                if 'selected_item' in st.session_state:
                    del st.session_state.selected_item
                st.rerun()
    
    # Similar items modal
    if st.session_state.get('show_similar_items', False) and st.session_state.get('similar_to_item'):
        with st.expander("🔍 Similar Items", expanded=True):
            show_similar_items(st.session_state.similar_to_item)
            if st.button("Close Similar Items"):
                st.session_state.show_similar_items = False
                if 'similar_to_item' in st.session_state:
                    del st.session_state.similar_to_item
                st.rerun()
    
    # Inventory management modals
    if st.session_state.get('show_move_form', False) and st.session_state.get('selected_items'):
        with st.expander("📍 Move Items", expanded=True):
            show_move_items_form()
            if st.button("Cancel Move"):
                st.session_state.show_move_form = False
                if 'selected_items' in st.session_state:
                    del st.session_state.selected_items
                st.rerun()
    
    if st.session_state.get('show_assign_location_form', False) and st.session_state.get('selected_items'):
        with st.expander("📍 Assign Location", expanded=True):
            show_assign_location_form()
            if st.button("Cancel Assignment"):
                st.session_state.show_assign_location_form = False
                if 'selected_items' in st.session_state:
                    del st.session_state.selected_items
                st.rerun()
    
    if st.session_state.get('show_quantity_adjust_form', False) and st.session_state.get('selected_item'):
        with st.expander("📊 Adjust Quantity", expanded=True):
            show_quantity_adjust_form()
            if st.button("Cancel Quantity Adjustment"):
                st.session_state.show_quantity_adjust_form = False
                if 'selected_item' in st.session_state:
                    del st.session_state.selected_item
                st.rerun()

def show_item_creation_form():
    """Display item creation form."""
    st.markdown("### ➕ Create New Item")
    
    api_client = APIClient()
    
    # Load options for form
    locations = safe_api_call(
        lambda: api_client.get_locations(skip=0, limit=1000),
        "Failed to load locations"
    ) or []
    
    categories_data = safe_api_call(
        lambda: api_client.get_categories(),
        "Failed to load categories"
    )
    categories = categories_data.get('categories', []) if categories_data else []
    
    # Item creation form
    with st.form("create_item_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Item Name*", help="Enter the item name")
            description = st.text_area("Description", help="Optional description of the item")
            
            # Item type selection
            item_types = get_item_type_options()
            item_type = st.selectbox("Item Type*", item_types, help="Select the primary type")
            
            # Condition and status
            conditions = get_condition_options()
            condition = st.selectbox("Condition", conditions, index=2, help="Current condition")  # Default to 'good'
            
            statuses = get_status_options()
            status = st.selectbox("Status", statuses, help="Current status")
            
            # Location selection (required for inventory tracking)
            if locations:
                location_options = {loc['id']: f"{loc['name']} ({loc.get('location_type', '').title()})" for loc in locations}
                selected_location_id = st.selectbox(
                    "Location*",
                    options=list(location_options.keys()),
                    format_func=lambda x: location_options[x],
                    help="Required: Select where this item will be stored"
                )
                
                # Quantity input
                quantity = st.number_input(
                    "Quantity",
                    min_value=1,
                    value=1,
                    help="Number of items to add to this location"
                )
            else:
                st.error("⚠️ No locations available. Please create at least one location before adding items.")
                st.stop()
                selected_location_id = None
                quantity = 1
            
            # Category selection
            selected_category_id = None
            if categories:
                category_options = {cat['id']: cat['name'] for cat in categories}
                category_options[None] = "No Category"
                selected_category_id = st.selectbox(
                    "Category",
                    options=list(category_options.keys()),
                    format_func=lambda x: category_options[x],
                    help="Optional category for organization"
                )
        
        with col2:
            # Brand and model
            brand = st.text_input("Brand", help="Manufacturer or brand name")
            model = st.text_input("Model", help="Model number or name")
            
            # Identification
            serial_number = st.text_input("Serial Number", help="Serial number if available")
            barcode = st.text_input("Barcode", help="Barcode or UPC if available")
            
            # Value tracking
            purchase_price = st.number_input("Purchase Price ($)", min_value=0.0, format="%.2f")
            current_value = st.number_input("Current Value ($)", min_value=0.0, format="%.2f")
            
            # Dates
            purchase_date = st.date_input("Purchase Date", help="When was this item purchased?")
            warranty_expiry = st.date_input("Warranty Expiry", help="When does the warranty expire?")
            
            # Physical properties
            weight = st.number_input("Weight (kg)", min_value=0.0, format="%.3f")
            color = st.text_input("Color", help="Primary color")
            dimensions = st.text_input("Dimensions", help="e.g., '10x20x5 cm'")
            
            # Additional metadata
            tags = st.text_input("Tags", help="Comma-separated tags (e.g., 'important, fragile')")
            notes = st.text_area("Notes", help="Additional notes or observations")
        
        # Submit button
        submitted = st.form_submit_button("✅ Create Item", type="primary", use_container_width=True)
        
        if submitted:
            stripped_name = safe_strip(name)
            if not stripped_name:
                st.error("Item name is required")
                return
            
            if not selected_location_id:
                st.error("Location is required")
                return
            
            # Prepare item data including location and quantity
            item_data = {
                "name": stripped_name,
                "item_type": item_type,
                "condition": condition,
                "status": status,
                "location_id": selected_location_id,
                "quantity": quantity
            }
            
            # Add optional fields using safe string helpers
            description_clean = safe_string_or_none(description)
            if description_clean:
                item_data["description"] = description_clean
            if selected_category_id:
                item_data["category_id"] = selected_category_id
            
            brand_clean = safe_string_or_none(brand)
            if brand_clean:
                item_data["brand"] = brand_clean
            
            model_clean = safe_string_or_none(model)
            if model_clean:
                item_data["model"] = model_clean
            
            serial_number_clean = safe_string_or_none(serial_number)
            if serial_number_clean:
                item_data["serial_number"] = serial_number_clean
            
            barcode_clean = safe_string_or_none(barcode)
            if barcode_clean:
                item_data["barcode"] = barcode_clean
            
            if purchase_price > 0:
                item_data["purchase_price"] = purchase_price
            if current_value > 0:
                item_data["current_value"] = current_value
            if purchase_date:
                item_data["purchase_date"] = purchase_date.isoformat()
            if warranty_expiry:
                item_data["warranty_expiry"] = warranty_expiry.isoformat()
            if weight > 0:
                item_data["weight"] = weight
            
            color_clean = safe_string_or_none(color)
            if color_clean:
                item_data["color"] = color_clean
            
            dimensions_clean = safe_string_or_none(dimensions)
            if dimensions_clean:
                item_data["dimensions"] = dimensions_clean
            
            tags_clean = safe_string_or_none(tags)
            if tags_clean:
                item_data["tags"] = tags_clean
            
            notes_clean = safe_string_or_none(notes)
            if notes_clean:
                item_data["notes"] = notes_clean
            
            # Create the item with location assignment
            with st.spinner("Creating item and assigning to location..."):
                result = safe_api_call(
                    lambda: api_client.create_item_with_location(item_data),
                    "Failed to create item"
                )
                
                if result:
                    location_name = location_options.get(selected_location_id, "Unknown Location")
                    if quantity == 1:
                        show_success(f"Item '{name}' created and assigned to {location_name}!")
                    else:
                        show_success(f"Item '{name}' created with {quantity} units assigned to {location_name}!")
                    
                    # Clear cache and close form
                    if 'items_cache' in st.session_state:
                        del st.session_state.items_cache
                    st.session_state.show_create_form = False
                    st.rerun()

def show_move_items_form():
    """Display form for moving selected items between locations."""
    st.markdown("### 📍 Move Items Between Locations")
    
    selected_items = st.session_state.get('selected_items', [])
    if not selected_items:
        st.error("No items selected for moving.")
        return
    
    api_client = APIClient()
    
    # Load locations for destination selection
    locations = safe_api_call(
        lambda: api_client.get_locations(skip=0, limit=1000),
        "Failed to load locations"
    ) or []
    
    if not locations:
        st.error("No locations available for moving items.")
        return
    
    # Display selected items
    st.markdown(f"**Moving {len(selected_items)} items:**")
    for item in selected_items:
        st.write(f"• {item.get('name', 'Unknown Item')}")
    
    with st.form("move_items_form"):
        # Destination location selection
        location_options = {loc['id']: f"{loc['name']} ({loc.get('location_type', '').title()})" for loc in locations}
        destination_location_id = st.selectbox(
            "Destination Location*",
            options=list(location_options.keys()),
            format_func=lambda x: location_options[x],
            help="Select where to move the selected items"
        )
        
        # Quantity to move (for items with multiple quantities)
        move_all = st.checkbox("Move all quantities", value=True, help="Move all quantities to new location")
        
        if not move_all:
            quantity_to_move = st.number_input(
                "Quantity to Move",
                min_value=1,
                value=1,
                help="Number of items to move (for partial moves)"
            )
        else:
            quantity_to_move = None
        
        # Optional notes
        move_notes = st.text_area("Move Notes", help="Optional notes about this move operation")
        
        # Submit button
        submitted = st.form_submit_button("✅ Move Items", type="primary")
        
        if submitted:
            success_count = 0
            errors = []
            
            with st.spinner("Moving items..."):
                for item in selected_items:
                    try:
                        # Get current inventory entries for this item
                        current_inventory = safe_api_call(
                            lambda: api_client.get_inventory(item_id=item['id']),
                            f"Failed to get inventory for {item.get('name', 'Unknown')}"
                        ) or []
                        
                        if not current_inventory:
                            # Item not in inventory - create new entry
                            result = safe_api_call(
                                lambda: api_client.create_inventory_entry(
                                    item_id=item['id'],
                                    location_id=destination_location_id,
                                    quantity=1
                                ),
                                f"Failed to assign {item.get('name', 'Unknown')} to location"
                            )
                            if result:
                                success_count += 1
                        else:
                            # Move from existing location(s)
                            for entry in current_inventory:
                                current_location_id = entry['location_id']
                                current_quantity = entry.get('quantity', 1)
                                move_qty = quantity_to_move if quantity_to_move else current_quantity
                                
                                result = safe_api_call(
                                    lambda: api_client.move_item(
                                        item_id=item['id'],
                                        from_location_id=current_location_id,
                                        to_location_id=destination_location_id,
                                        quantity=move_qty
                                    ),
                                    f"Failed to move {item.get('name', 'Unknown')}"
                                )
                                if result:
                                    success_count += 1
                                    break  # Only move from first location for now
                    
                    except Exception as e:
                        errors.append(f"{item.get('name', 'Unknown')}: {str(e)}")
            
            # Show results
            if success_count > 0:
                destination_name = location_options.get(destination_location_id, "Unknown Location")
                show_success(f"Successfully moved {success_count} items to {destination_name}!")
            
            if errors:
                st.error("Some items could not be moved:")
                for error in errors:
                    st.write(f"• {error}")
            
            # Clear cache and close form
            if 'items_cache' in st.session_state:
                del st.session_state.items_cache
            st.session_state.show_move_form = False
            if 'selected_items' in st.session_state:
                del st.session_state.selected_items
            st.rerun()

def show_assign_location_form():
    """Display form for assigning locations to items without inventory entries."""
    st.markdown("### 📍 Assign Items to Locations")
    
    selected_items = st.session_state.get('selected_items', [])
    if not selected_items:
        st.error("No items selected for location assignment.")
        return
    
    api_client = APIClient()
    
    # Load locations
    locations = safe_api_call(
        lambda: api_client.get_locations(skip=0, limit=1000),
        "Failed to load locations"
    ) or []
    
    if not locations:
        st.error("No locations available. Please create locations first.")
        return
    
    # Filter items that don't have inventory entries
    items_without_location = []
    for item in selected_items:
        inventory_entries = item.get('inventory_entries', [])
        if not inventory_entries or len(inventory_entries) == 0:
            items_without_location.append(item)
    
    if not items_without_location:
        st.info("All selected items already have location assignments.")
        return
    
    # Display items to be assigned
    st.markdown(f"**Assigning locations to {len(items_without_location)} items:**")
    for item in items_without_location:
        st.write(f"• {item.get('name', 'Unknown Item')}")
    
    with st.form("assign_location_form"):
        # Location selection
        location_options = {loc['id']: f"{loc['name']} ({loc.get('location_type', '').title()})" for loc in locations}
        selected_location_id = st.selectbox(
            "Assign to Location*",
            options=list(location_options.keys()),
            format_func=lambda x: location_options[x],
            help="Select location to assign these items to"
        )
        
        # Default quantity
        default_quantity = st.number_input(
            "Default Quantity",
            min_value=1,
            value=1,
            help="Default quantity for each item"
        )
        
        # Optional notes
        assignment_notes = st.text_area("Assignment Notes", help="Optional notes about this assignment")
        
        # Submit button
        submitted = st.form_submit_button("✅ Assign to Location", type="primary")
        
        if submitted:
            success_count = 0
            errors = []
            
            with st.spinner("Assigning items to location..."):
                for item in items_without_location:
                    try:
                        result = safe_api_call(
                            lambda: api_client.create_inventory_entry(
                                item_id=item['id'],
                                location_id=selected_location_id,
                                quantity=default_quantity
                            ),
                            f"Failed to assign {item.get('name', 'Unknown')} to location"
                        )
                        
                        if result:
                            success_count += 1
                    
                    except Exception as e:
                        errors.append(f"{item.get('name', 'Unknown')}: {str(e)}")
            
            # Show results
            if success_count > 0:
                location_name = location_options.get(selected_location_id, "Unknown Location")
                show_success(f"Successfully assigned {success_count} items to {location_name}!")
            
            if errors:
                st.error("Some items could not be assigned:")
                for error in errors:
                    st.write(f"• {error}")
            
            # Clear cache and close form
            if 'items_cache' in st.session_state:
                del st.session_state.items_cache
            st.session_state.show_assign_location_form = False
            if 'selected_items' in st.session_state:
                del st.session_state.selected_items
            st.rerun()

def show_quantity_adjust_form():
    """Display form for adjusting item quantities at specific locations."""
    st.markdown("### 📊 Adjust Item Quantity")
    
    selected_item = st.session_state.get('selected_item')
    if not selected_item:
        st.error("No item selected for quantity adjustment.")
        return
    
    api_client = APIClient()
    
    # Get current inventory entries for this item
    inventory_entries = safe_api_call(
        lambda: api_client.get_inventory(item_id=selected_item['id']),
        f"Failed to load inventory for {selected_item.get('name', 'Unknown')}"
    ) or []
    
    if not inventory_entries:
        st.error("This item is not currently assigned to any locations.")
        return
    
    st.markdown(f"**Adjusting quantities for: {selected_item.get('name', 'Unknown Item')}**")
    
    with st.form("quantity_adjust_form"):
        st.markdown("**Current Inventory:**")
        
        # Show current quantities and allow adjustment
        adjustments = {}
        for i, entry in enumerate(inventory_entries):
            location_name = "Unknown Location"
            if entry.get('location'):
                location_name = entry['location'].get('name', 'Unknown Location')
            elif entry.get('location_id'):
                try:
                    location = api_client.get_location(entry['location_id'])
                    location_name = location.get('name', f"Location {entry['location_id']}")
                except:
                    location_name = f"Location {entry['location_id']}"
            
            current_qty = entry.get('quantity', 1)
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write(f"**{location_name}**")
                st.write(f"Current: {current_qty}")
            
            with col2:
                new_qty = st.number_input(
                    "New Quantity",
                    min_value=0,
                    value=current_qty,
                    key=f"qty_{i}",
                    help=f"New quantity for {location_name}"
                )
                adjustments[entry.get('id')] = {
                    'current': current_qty,
                    'new': new_qty,
                    'location_name': location_name
                }
        
        # Adjustment reason
        adjustment_reason = st.text_area(
            "Reason for Adjustment",
            help="Optional notes explaining the quantity changes"
        )
        
        # Submit button
        submitted = st.form_submit_button("✅ Update Quantities", type="primary")
        
        if submitted:
            success_count = 0
            errors = []
            changes_made = []
            
            with st.spinner("Updating quantities..."):
                for inventory_id, adjustment in adjustments.items():
                    current_qty = adjustment['current']
                    new_qty = adjustment['new']
                    location_name = adjustment['location_name']
                    
                    if current_qty != new_qty:
                        try:
                            if new_qty == 0:
                                # Remove inventory entry if quantity is 0
                                result = safe_api_call(
                                    lambda: api_client.delete_inventory_entry(inventory_id),
                                    f"Failed to remove item from {location_name}"
                                )
                                if result:
                                    success_count += 1
                                    changes_made.append(f"Removed from {location_name}")
                            else:
                                # Update quantity
                                result = safe_api_call(
                                    lambda: api_client.update_inventory_entry(
                                        inventory_id,
                                        {'quantity': new_qty}
                                    ),
                                    f"Failed to update quantity at {location_name}"
                                )
                                if result:
                                    success_count += 1
                                    changes_made.append(f"{location_name}: {current_qty} → {new_qty}")
                        
                        except Exception as e:
                            errors.append(f"{location_name}: {str(e)}")
            
            # Show results
            if success_count > 0:
                show_success(f"Successfully updated {success_count} inventory entries!")
                if changes_made:
                    st.info("Changes made:")
                    for change in changes_made:
                        st.write(f"• {change}")
            
            if errors:
                st.error("Some quantities could not be updated:")
                for error in errors:
                    st.write(f"• {error}")
            
            # Clear cache and close form
            if 'items_cache' in st.session_state:
                del st.session_state.items_cache
            st.session_state.show_quantity_adjust_form = False
            if 'selected_item' in st.session_state:
                del st.session_state.selected_item
            st.rerun()

# Main execution
if __name__ == "__main__":
    try:
        show_items_page()
        show_modals()
    except Exception as e:
        logger.error(f"Error in items page: {str(e)}")
        show_error(f"An error occurred: {str(e)}")
        st.info("Please refresh the page or contact support if the problem persists.")