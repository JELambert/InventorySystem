"""
Item Movement UI Component for the Home Inventory System.

Provides sophisticated drag-and-drop interfaces for moving items between locations,
with visual feedback and integration with the movement history system.
"""

import streamlit as st
import pandas as pd
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from utils.api_client import APIClient, APIError
from utils.helpers import (
    safe_api_call, show_error, show_success, show_warning,
    handle_api_error, format_datetime, safe_currency_format
)


def create_drag_drop_movement_interface(items: List[Dict], locations: List[Dict]) -> None:
    """
    Create an interactive drag-and-drop interface for moving items between locations.
    
    Args:
        items: List of items with inventory information
        locations: List of available locations
    """
    st.markdown("### 🎯 Drag & Drop Item Movement")
    st.markdown("_Drag items between location containers to move them_")
    
    # Create a visual board layout using containers instead of columns to avoid nesting
    st.markdown("#### 📦 Items")
    _render_items_panel(items)
    
    st.markdown("---")
    
    st.markdown("#### 📍 Locations")
    _render_locations_panel(locations, items)


def _render_items_panel(items: List[Dict]) -> None:
    """Render the items panel with draggable items."""
    # Group items by their current locations
    items_by_location = {}
    unassigned_items = []
    
    for item in items:
        inventory_entries = item.get('inventory_entries', [])
        if not inventory_entries:
            unassigned_items.append(item)
        else:
            for entry in inventory_entries:
                location_id = entry.get('location_id')
                location_name = entry.get('location', {}).get('name', f'Location {location_id}')
                
                if location_name not in items_by_location:
                    items_by_location[location_name] = []
                
                # Create item copy with quantity info
                item_copy = item.copy()
                item_copy['current_quantity'] = entry.get('quantity', 1)
                item_copy['current_location_id'] = location_id
                items_by_location[location_name].append(item_copy)
    
    # Display unassigned items first
    if unassigned_items:
        with st.container(border=True):
            st.markdown("**🔍 Unassigned Items**")
            for item in unassigned_items:
                _render_draggable_item(item, None)
    
    # Display items grouped by location
    for location_name, location_items in items_by_location.items():
        with st.container(border=True):
            st.markdown(f"**📍 {location_name}**")
            for item in location_items:
                _render_draggable_item(item, item.get('current_location_id'))


def _render_draggable_item(item: Dict, current_location_id: Optional[int]) -> None:
    """Render a single draggable item card."""
    item_id = item.get('id')
    quantity = item.get('current_quantity', 1) if current_location_id else 1
    
    # Create item card with drag functionality
    with st.container():
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            # Item name and type
            st.markdown(f"**{item.get('name', 'Unknown Item')}**")
            item_type = item.get('item_type', '').replace('_', ' ').title()
            st.caption(f"{item_type}")
        
        with col2:
            if quantity > 1:
                st.metric("Qty", quantity)
            if item.get('current_value'):
                st.caption(safe_currency_format(item['current_value']))
        
        with col3:
            # Quick move button
            if st.button("📍", key=f"quick_move_{item_id}_{current_location_id}", 
                        help="Quick move this item"):
                st.session_state.quick_move_item = item
                st.session_state.quick_move_from_location = current_location_id
                st.session_state.show_quick_move_modal = True
                st.rerun()


def _render_locations_panel(locations: List[Dict], items: List[Dict]) -> None:
    """Render the locations panel as drop targets."""
    # Create location cards that can receive items
    cols_per_row = 2
    
    for i in range(0, len(locations), cols_per_row):
        cols = st.columns(cols_per_row)
        
        for j, col in enumerate(cols):
            if i + j < len(locations):
                location = locations[i + j]
                with col:
                    _render_drop_target_location(location, items)


def _render_drop_target_location(location: Dict, items: List[Dict]) -> None:
    """Render a location as a drop target for items."""
    location_id = location.get('id')
    location_name = location.get('name', 'Unknown Location')
    location_type = location.get('location_type', '').replace('_', ' ').title()
    
    # Count items in this location
    items_in_location = []
    total_quantity = 0
    
    for item in items:
        for entry in item.get('inventory_entries', []):
            if entry.get('location_id') == location_id:
                items_in_location.append(item)
                total_quantity += entry.get('quantity', 1)
    
    # Location card
    with st.container(border=True):
        st.markdown(f"**🏠 {location_name}**")
        st.caption(f"{location_type}")
        
        # Quick stats
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Items", len(items_in_location))
        with col2:
            st.metric("Total Qty", total_quantity)
        
        # Quick add button
        if st.button("➕ Add Item", key=f"add_to_{location_id}", 
                    help=f"Add item to {location_name}"):
            st.session_state.target_location_id = location_id
            st.session_state.target_location_name = location_name
            st.session_state.show_add_to_location_modal = True
            st.rerun()
        
        # Show summary of items if any
        if items_in_location:
            with st.expander(f"Items in {location_name}", expanded=False):
                for item in items_in_location[:3]:  # Show first 3 items
                    qty = sum(entry.get('quantity', 1) for entry in item.get('inventory_entries', []) 
                             if entry.get('location_id') == location_id)
                    st.write(f"• {item.get('name', 'Unknown')} (Qty: {qty})")
                
                if len(items_in_location) > 3:
                    st.caption(f"... and {len(items_in_location) - 3} more items")


def create_movement_history_panel(item_id: Optional[int] = None) -> None:
    """
    Create a panel showing movement history with filtering options.
    
    Args:
        item_id: Optional item ID to filter history for specific item
    """
    st.markdown("### 📊 Movement History")
    
    api_client = APIClient()
    
    # Filter controls in a simple layout to avoid column nesting
    with st.container():
        st.markdown("**📋 History Filters**")
        
        # Create filter row
        filter_col1, filter_col2, filter_col3 = st.columns(3)
        
        with filter_col1:
            # Date range filter
            days_back = st.selectbox(
                "Show movements from:",
                options=[7, 30, 90, 365, 0],
                format_func=lambda x: f"Last {x} days" if x > 0 else "All time",
                index=1  # Default to 30 days
            )
        
        with filter_col2:
            # Movement type filter
            movement_type = st.selectbox(
                "Movement type:",
                options=["all", "move", "adjust", "create"],
                format_func=lambda x: x.title() if x != "all" else "All Types"
            )
        
        with filter_col3:
            # User filter (if available)
            user_filter = st.text_input("User:", placeholder="Filter by user ID")
    
    # Fetch movement history
    history_params = {
        'limit': 50,
        'skip': 0
    }
    
    if item_id:
        history_params['item_id'] = item_id
    
    if movement_type != "all":
        history_params['movement_type'] = movement_type
    
    if user_filter:
        history_params['user_id'] = user_filter
    
    # Calculate start date if filtering by days
    if days_back > 0:
        from datetime import datetime, timedelta
        start_date = datetime.now() - timedelta(days=days_back)
        history_params['start_date'] = start_date.isoformat()
    
    # Load movement history
    movements = safe_api_call(
        lambda: api_client.get_movement_history(**history_params),
        "Failed to load movement history"
    ) or []
    
    if movements:
        # Create movements dataframe
        movement_data = []
        for movement in movements:
            # Extract basic movement info
            row = {
                "Time": format_datetime(movement.get('created_at')),
                "Item": movement.get('item', {}).get('name', 'Unknown Item'),
                "Type": movement.get('movement_type', '').title(),
                "Description": movement.get('movement_description', ''),
                "Quantity": movement.get('quantity_moved', 0),
                "From": movement.get('from_location', {}).get('name', '') if movement.get('from_location') else '',
                "To": movement.get('to_location', {}).get('name', '') if movement.get('to_location') else '',
                "User": movement.get('user_id', ''),
                "Reason": movement.get('reason', '')
            }
            movement_data.append(row)
        
        # Display movements table
        movements_df = pd.DataFrame(movement_data)
        st.dataframe(
            movements_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Time": st.column_config.DatetimeColumn("Time", width="medium"),
                "Item": st.column_config.TextColumn("Item", width="medium"),
                "Type": st.column_config.TextColumn("Type", width="small"),
                "Description": st.column_config.TextColumn("Description", width="large"),
                "Quantity": st.column_config.NumberColumn("Qty", width="small"),
                "From": st.column_config.TextColumn("From Location", width="medium"),
                "To": st.column_config.TextColumn("To Location", width="medium"),
                "User": st.column_config.TextColumn("User", width="small"),
                "Reason": st.column_config.TextColumn("Reason", width="medium")
            }
        )
        
        # Movement summary
        with st.expander("📈 Movement Summary", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Movements", len(movements))
            
            with col2:
                total_items = sum(m.get('quantity_moved', 0) for m in movements)
                st.metric("Items Moved", total_items)
            
            with col3:
                unique_items = len(set(m.get('item_id') for m in movements if m.get('item_id')))
                st.metric("Unique Items", unique_items)
            
            with col4:
                # Count unique locations involved
                locations = set()
                for m in movements:
                    if m.get('from_location_id'):
                        locations.add(m['from_location_id'])
                    if m.get('to_location_id'):
                        locations.add(m['to_location_id'])
                st.metric("Locations Involved", len(locations))
    
    else:
        st.info("No movement history found for the selected criteria.")


def create_advanced_quantity_operations_panel() -> None:
    """Create panel for advanced quantity operations (split, merge, adjust)."""
    st.markdown("### ⚙️ Advanced Quantity Operations")
    
    # Operation type selection
    operation_type = st.selectbox(
        "Select Operation:",
        options=["split", "merge", "adjust"],
        format_func=lambda x: {
            "split": "🔄 Split - Move quantity to another location",
            "merge": "🔗 Merge - Consolidate from multiple locations",
            "adjust": "📊 Adjust - Set new quantity at location"
        }[x]
    )
    
    if operation_type == "split":
        _show_split_operation_form()
    elif operation_type == "merge":
        _show_merge_operation_form()
    elif operation_type == "adjust":
        _show_adjust_operation_form()


def _show_split_operation_form():
    """Show form for split quantity operation."""
    st.markdown("#### 🔄 Split Item Quantity")
    st.info("Move part of an item's quantity from one location to another.")
    
    api_client = APIClient()
    
    # Load items with inventory
    items = safe_api_call(
        lambda: api_client.get_items_with_inventory(),
        "Failed to load items"
    ) or []
    
    # Filter items that have inventory
    items_with_inventory = [item for item in items if item.get('inventory_entries')]
    
    if not items_with_inventory:
        st.error("No items with inventory found.")
        return
    
    with st.form("split_operation_form"):
        # Item selection
        item_options = {item['id']: f"{item['name']} - {item.get('item_type', '').replace('_', ' ').title()}" 
                       for item in items_with_inventory}
        selected_item_id = st.selectbox(
            "Select Item:",
            options=list(item_options.keys()),
            format_func=lambda x: item_options[x]
        )
        
        # Get selected item details
        selected_item = next((item for item in items_with_inventory if item['id'] == selected_item_id), None)
        
        if selected_item:
            inventory_entries = selected_item.get('inventory_entries', [])
            
            # Source location selection
            source_options = {}
            for entry in inventory_entries:
                location = entry.get('location', {})
                location_id = entry.get('location_id')
                location_name = location.get('name', f'Location {location_id}')
                quantity = entry.get('quantity', 1)
                source_options[location_id] = f"{location_name} (Qty: {quantity})"
            
            source_location_id = st.selectbox(
                "From Location:",
                options=list(source_options.keys()),
                format_func=lambda x: source_options[x]
            )
            
            # Get available quantity at source
            source_entry = next((entry for entry in inventory_entries 
                               if entry.get('location_id') == source_location_id), None)
            max_quantity = source_entry.get('quantity', 1) if source_entry else 1
            
            # Quantity to move
            quantity_to_move = st.number_input(
                "Quantity to Move:",
                min_value=1,
                max_value=max_quantity,
                value=1,
                help=f"Maximum available: {max_quantity}"
            )
            
            # Destination location
            locations = safe_api_call(
                lambda: api_client.get_locations(skip=0, limit=1000),
                "Failed to load locations"
            ) or []
            
            # Filter out source location
            dest_locations = [loc for loc in locations if loc['id'] != source_location_id]
            dest_options = {loc['id']: f"{loc['name']} ({loc.get('location_type', '').replace('_', ' ').title()})"
                           for loc in dest_locations}
            
            dest_location_id = st.selectbox(
                "To Location:",
                options=list(dest_options.keys()),
                format_func=lambda x: dest_options[x]
            )
            
            # Optional reason
            reason = st.text_area("Reason:", placeholder="Optional reason for this split operation")
            
            # Submit button
            submitted = st.form_submit_button("🔄 Split Quantity", type="primary")
            
            if submitted:
                split_data = {
                    "source_location_id": source_location_id,
                    "dest_location_id": dest_location_id,
                    "quantity_to_move": quantity_to_move,
                    "reason": reason
                }
                
                with st.spinner("Splitting item quantity..."):
                    result = safe_api_call(
                        lambda: api_client.split_item_quantity(selected_item_id, split_data),
                        "Failed to split item quantity"
                    )
                    
                    if result:
                        source_name = source_options.get(source_location_id, "Unknown")
                        dest_name = dest_options.get(dest_location_id, "Unknown")
                        show_success(f"Successfully moved {quantity_to_move} units of {selected_item['name']} from {source_name} to {dest_name}!")
                        st.rerun()


def _show_merge_operation_form():
    """Show form for merge quantity operation."""
    st.markdown("#### 🔗 Merge Item Quantities")
    st.info("Consolidate item quantities from multiple locations into one target location.")
    
    api_client = APIClient()
    
    # Load items with inventory in multiple locations
    items = safe_api_call(
        lambda: api_client.get_items_with_inventory(),
        "Failed to load items"
    ) or []
    
    # Filter items that have inventory in multiple locations
    items_in_multiple_locations = []
    for item in items:
        inventory_entries = item.get('inventory_entries', [])
        if len(inventory_entries) > 1:
            items_in_multiple_locations.append(item)
    
    if not items_in_multiple_locations:
        st.info("No items found in multiple locations.")
        return
    
    with st.form("merge_operation_form"):
        # Item selection
        item_options = {item['id']: f"{item['name']} - {len(item.get('inventory_entries', []))} locations" 
                       for item in items_in_multiple_locations}
        selected_item_id = st.selectbox(
            "Select Item:",
            options=list(item_options.keys()),
            format_func=lambda x: item_options[x]
        )
        
        # Get selected item details
        selected_item = next((item for item in items_in_multiple_locations if item['id'] == selected_item_id), None)
        
        if selected_item:
            inventory_entries = selected_item.get('inventory_entries', [])
            
            # Source locations selection (multi-select)
            source_options = {}
            for entry in inventory_entries:
                location = entry.get('location', {})
                location_id = entry.get('location_id')
                location_name = location.get('name', f'Location {location_id}')
                quantity = entry.get('quantity', 1)
                source_options[location_id] = f"{location_name} (Qty: {quantity})"
            
            source_location_names = st.multiselect(
                "From Locations:",
                options=list(source_options.keys()),
                format_func=lambda x: source_options[x],
                help="Select locations to merge from"
            )
            
            if source_location_names:
                # Target location selection
                target_options = {loc_id: name for loc_id, name in source_options.items()}
                target_location_id = st.selectbox(
                    "Target Location:",
                    options=list(target_options.keys()),
                    format_func=lambda x: target_options[x],
                    help="Select location to merge all quantities into"
                )
                
                # Show merge preview
                total_quantity = sum(entry.get('quantity', 1) for entry in inventory_entries 
                                   if entry.get('location_id') in source_location_names)
                st.info(f"Will merge {total_quantity} total units into {target_options.get(target_location_id, 'Unknown')}")
                
                # Optional reason
                reason = st.text_area("Reason:", placeholder="Optional reason for this merge operation")
                
                # Submit button
                submitted = st.form_submit_button("🔗 Merge Quantities", type="primary")
                
                if submitted:
                    if target_location_id in source_location_names:
                        st.error("Target location cannot be one of the source locations.")
                    else:
                        merge_data = {
                            "location_ids": source_location_names,
                            "target_location_id": target_location_id,
                            "reason": reason
                        }
                        
                        with st.spinner("Merging item quantities..."):
                            result = safe_api_call(
                                lambda: api_client.merge_item_quantities(selected_item_id, merge_data),
                                "Failed to merge item quantities"
                            )
                            
                            if result:
                                target_name = target_options.get(target_location_id, "Unknown")
                                show_success(f"Successfully merged {total_quantity} units of {selected_item['name']} into {target_name}!")
                                st.rerun()


def _show_adjust_operation_form():
    """Show form for adjust quantity operation."""
    st.markdown("#### 📊 Adjust Item Quantity")
    st.info("Set a new quantity for an item at a specific location.")
    
    api_client = APIClient()
    
    # Load items with inventory
    items = safe_api_call(
        lambda: api_client.get_items_with_inventory(),
        "Failed to load items"
    ) or []
    
    items_with_inventory = [item for item in items if item.get('inventory_entries')]
    
    if not items_with_inventory:
        st.error("No items with inventory found.")
        return
    
    with st.form("adjust_operation_form"):
        # Item selection
        item_options = {item['id']: f"{item['name']} - {item.get('item_type', '').replace('_', ' ').title()}" 
                       for item in items_with_inventory}
        selected_item_id = st.selectbox(
            "Select Item:",
            options=list(item_options.keys()),
            format_func=lambda x: item_options[x]
        )
        
        # Get selected item details
        selected_item = next((item for item in items_with_inventory if item['id'] == selected_item_id), None)
        
        if selected_item:
            inventory_entries = selected_item.get('inventory_entries', [])
            
            # Location selection
            location_options = {}
            for entry in inventory_entries:
                location = entry.get('location', {})
                location_id = entry.get('location_id')
                location_name = location.get('name', f'Location {location_id}')
                quantity = entry.get('quantity', 1)
                location_options[location_id] = f"{location_name} (Current: {quantity})"
            
            location_id = st.selectbox(
                "Location:",
                options=list(location_options.keys()),
                format_func=lambda x: location_options[x]
            )
            
            # Get current quantity
            current_entry = next((entry for entry in inventory_entries 
                                if entry.get('location_id') == location_id), None)
            current_quantity = current_entry.get('quantity', 1) if current_entry else 1
            
            # New quantity input
            new_quantity = st.number_input(
                "New Quantity:",
                min_value=0,
                value=current_quantity,
                help="Set to 0 to remove item from this location"
            )
            
            # Show change preview
            if new_quantity != current_quantity:
                change = new_quantity - current_quantity
                if change > 0:
                    st.info(f"Will increase quantity by {change} (from {current_quantity} to {new_quantity})")
                elif change < 0:
                    st.warning(f"Will decrease quantity by {abs(change)} (from {current_quantity} to {new_quantity})")
                
                if new_quantity == 0:
                    st.warning("⚠️ Setting quantity to 0 will remove this item from the location.")
            
            # Optional reason
            reason = st.text_area("Reason:", placeholder="Required reason for quantity adjustment")
            
            # Submit button
            submitted = st.form_submit_button("📊 Adjust Quantity", type="primary")
            
            if submitted:
                if not reason.strip():
                    st.error("Please provide a reason for the quantity adjustment.")
                else:
                    adjustment_data = {
                        "new_quantity": new_quantity,
                        "reason": reason
                    }
                    
                    with st.spinner("Adjusting item quantity..."):
                        result = safe_api_call(
                            lambda: api_client.adjust_item_quantity(selected_item_id, location_id, adjustment_data),
                            "Failed to adjust item quantity"
                        )
                        
                        if result:
                            location_name = location_options.get(location_id, "Unknown").split(" (Current:")[0]
                            if new_quantity == 0:
                                show_success(f"Successfully removed {selected_item['name']} from {location_name}!")
                            else:
                                show_success(f"Successfully adjusted {selected_item['name']} quantity at {location_name} to {new_quantity}!")
                            st.rerun()


def show_movement_modals():
    """Display movement-related modal dialogs."""
    # Quick move modal
    if st.session_state.get('show_quick_move_modal', False):
        _show_quick_move_modal()
    
    # Add to location modal
    if st.session_state.get('show_add_to_location_modal', False):
        _show_add_to_location_modal()


def _show_quick_move_modal():
    """Show quick move modal for rapid item movement."""
    quick_move_item = st.session_state.get('quick_move_item')
    from_location_id = st.session_state.get('quick_move_from_location')
    
    if not quick_move_item:
        return
    
    with st.expander("🚀 Quick Move Item", expanded=True):
        st.markdown(f"**Moving:** {quick_move_item.get('name', 'Unknown Item')}")
        
        api_client = APIClient()
        
        # Load locations
        locations = safe_api_call(
            lambda: api_client.get_locations(skip=0, limit=1000),
            "Failed to load locations"
        ) or []
        
        # Filter out current location
        available_locations = [loc for loc in locations if loc['id'] != from_location_id]
        
        with st.form("quick_move_form"):
            if available_locations:
                location_options = {loc['id']: f"{loc['name']} ({loc.get('location_type', '').replace('_', ' ').title()})"
                                  for loc in available_locations}
                
                to_location_id = st.selectbox(
                    "Move to:",
                    options=list(location_options.keys()),
                    format_func=lambda x: location_options[x]
                )
                
                # Get current quantity if moving from a location
                current_quantity = quick_move_item.get('current_quantity', 1)
                if current_quantity > 1:
                    move_quantity = st.number_input(
                        "Quantity to move:",
                        min_value=1,
                        max_value=current_quantity,
                        value=current_quantity,
                        help=f"Maximum available: {current_quantity}"
                    )
                else:
                    move_quantity = 1
                
                reason = st.text_input("Reason:", placeholder="Optional reason for move")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.form_submit_button("✅ Move Item", type="primary"):
                        if from_location_id:
                            # Move from existing location
                            result = safe_api_call(
                                lambda: api_client.move_item(
                                    item_id=quick_move_item['id'],
                                    from_location_id=from_location_id,
                                    to_location_id=to_location_id,
                                    quantity=move_quantity
                                ),
                                "Failed to move item"
                            )
                        else:
                            # Assign to location (item was unassigned)
                            result = safe_api_call(
                                lambda: api_client.create_inventory_entry(
                                    item_id=quick_move_item['id'],
                                    location_id=to_location_id,
                                    quantity=move_quantity
                                ),
                                "Failed to assign item to location"
                            )
                        
                        if result:
                            to_location_name = location_options.get(to_location_id, "Unknown")
                            show_success(f"Successfully moved {quick_move_item['name']} to {to_location_name}!")
                            _close_quick_move_modal()
                            st.rerun()
                
                with col2:
                    if st.form_submit_button("❌ Cancel"):
                        _close_quick_move_modal()
                        st.rerun()
            else:
                st.error("No available locations to move to.")
                if st.form_submit_button("❌ Close"):
                    _close_quick_move_modal()
                    st.rerun()


def _show_add_to_location_modal():
    """Show modal for adding items to a specific location."""
    target_location_id = st.session_state.get('target_location_id')
    target_location_name = st.session_state.get('target_location_name')
    
    if not target_location_id:
        return
    
    with st.expander(f"➕ Add Item to {target_location_name}", expanded=True):
        api_client = APIClient()
        
        # Load unassigned items
        items = safe_api_call(
            lambda: api_client.get_items_with_inventory(),
            "Failed to load items"
        ) or []
        
        # Filter items that are not in the target location
        available_items = []
        for item in items:
            inventory_entries = item.get('inventory_entries', [])
            already_in_location = any(entry.get('location_id') == target_location_id 
                                    for entry in inventory_entries)
            if not already_in_location:
                available_items.append(item)
        
        with st.form("add_to_location_form"):
            if available_items:
                item_options = {item['id']: f"{item['name']} - {item.get('item_type', '').replace('_', ' ').title()}" 
                               for item in available_items}
                
                selected_item_id = st.selectbox(
                    "Select item to add:",
                    options=list(item_options.keys()),
                    format_func=lambda x: item_options[x]
                )
                
                quantity = st.number_input("Quantity:", min_value=1, value=1)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.form_submit_button("✅ Add to Location", type="primary"):
                        result = safe_api_call(
                            lambda: api_client.create_inventory_entry(
                                item_id=selected_item_id,
                                location_id=target_location_id,
                                quantity=quantity
                            ),
                            "Failed to add item to location"
                        )
                        
                        if result:
                            item_name = item_options.get(selected_item_id, "Unknown")
                            show_success(f"Successfully added {item_name} to {target_location_name}!")
                            _close_add_to_location_modal()
                            st.rerun()
                
                with col2:
                    if st.form_submit_button("❌ Cancel"):
                        _close_add_to_location_modal()
                        st.rerun()
            else:
                st.info("No available items to add to this location.")
                if st.form_submit_button("❌ Close"):
                    _close_add_to_location_modal()
                    st.rerun()


def _close_quick_move_modal():
    """Close the quick move modal."""
    if 'show_quick_move_modal' in st.session_state:
        del st.session_state.show_quick_move_modal
    if 'quick_move_item' in st.session_state:
        del st.session_state.quick_move_item
    if 'quick_move_from_location' in st.session_state:
        del st.session_state.quick_move_from_location


def _close_add_to_location_modal():
    """Close the add to location modal."""
    if 'show_add_to_location_modal' in st.session_state:
        del st.session_state.show_add_to_location_modal
    if 'target_location_id' in st.session_state:
        del st.session_state.target_location_id
    if 'target_location_name' in st.session_state:
        del st.session_state.target_location_name