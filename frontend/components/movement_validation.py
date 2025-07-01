"""
Movement Validation Components for the Streamlit frontend.

Provides UI components for movement validation, business rule display,
and validation feedback to ensure user operations comply with business rules.
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

from utils.api_client import APIClient, APIError
from utils.helpers import (
    safe_api_call, show_error, show_success, show_warning, show_info,
    handle_api_error, SessionManager, safe_strip
)

logger = logging.getLogger(__name__)


def validate_movement_before_execution(
    movement_data: Dict[str, Any],
    api_client: APIClient,
    enforce_strict: bool = True
) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate a movement operation before execution.
    
    Args:
        movement_data: Movement data to validate
        api_client: API client instance
        enforce_strict: Whether to enforce strict validation
        
    Returns:
        Tuple of (is_valid, validation_result)
    """
    try:
        validation_result = api_client.validate_movement(movement_data, enforce_strict)
        return validation_result.get("is_valid", False), validation_result
    except Exception as e:
        logger.error(f"Movement validation failed: {str(e)}")
        return False, {"errors": [f"Validation system error: {str(e)}"]}


def show_validation_result(validation_result: Dict[str, Any], prefix: str = "") -> None:
    """
    Display validation results in the UI.
    
    Args:
        validation_result: Validation result from API
        prefix: Optional prefix for UI element keys
    """
    if not validation_result:
        return
    
    is_valid = validation_result.get("is_valid", False)
    errors = validation_result.get("errors", [])
    warnings = validation_result.get("warnings", [])
    business_rules = validation_result.get("business_rules_applied", [])
    
    # Display validation status
    if is_valid:
        if warnings:
            show_warning(f"Validation passed with {len(warnings)} warning(s)")
        else:
            show_success("Validation passed - operation is allowed")
    else:
        show_error(f"Validation failed with {len(errors)} error(s)")
    
    # Display errors
    if errors:
        st.markdown("**❌ Validation Errors:**")
        for i, error in enumerate(errors):
            st.error(f"{i+1}. {error}")
    
    # Display warnings
    if warnings:
        st.markdown("**⚠️ Validation Warnings:**")
        for i, warning in enumerate(warnings):
            st.warning(f"{i+1}. {warning}")
    
    # Display applied business rules
    if business_rules:
        with st.expander("📋 Business Rules Applied", expanded=False):
            for rule in business_rules:
                st.info(f"✓ {rule}")


def create_movement_validation_widget(
    movement_data: Optional[Dict[str, Any]] = None,
    key_prefix: str = "validation"
) -> Optional[Dict[str, Any]]:
    """
    Create an interactive movement validation widget.
    
    Args:
        movement_data: Pre-filled movement data (optional)
        key_prefix: Prefix for widget keys
        
    Returns:
        Validation result if movement_data provided, None otherwise
    """
    st.markdown("### 🔍 Movement Validation")
    
    api_client = APIClient()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Movement data input form
        with st.form(f"{key_prefix}_validation_form"):
            st.markdown("**Movement Details**")
            
            item_id = st.number_input(
                "Item ID*", 
                min_value=1, 
                value=movement_data.get("item_id", 1) if movement_data else 1,
                help="ID of the item to move"
            )
            
            movement_type = st.selectbox(
                "Movement Type*",
                ["move", "create", "adjust", "split", "merge"],
                index=0 if not movement_data else ["move", "create", "adjust", "split", "merge"].index(movement_data.get("movement_type", "move")),
                help="Type of movement operation"
            )
            
            col1_form, col2_form = st.columns(2)
            
            with col1_form:
                from_location_id = st.number_input(
                    "From Location ID",
                    min_value=0,
                    value=movement_data.get("from_location_id", 0) if movement_data else 0,
                    help="Source location (0 for none)"
                )
                quantity_moved = st.number_input(
                    "Quantity*",
                    min_value=1,
                    value=movement_data.get("quantity_moved", 1) if movement_data else 1,
                    help="Quantity to move"
                )
            
            with col2_form:
                to_location_id = st.number_input(
                    "To Location ID",
                    min_value=0,
                    value=movement_data.get("to_location_id", 0) if movement_data else 0,
                    help="Destination location (0 for none)"
                )
                enforce_strict = st.checkbox(
                    "Strict Validation",
                    value=True,
                    help="Enforce all business rules strictly"
                )
            
            reason = st.text_input(
                "Reason",
                value=movement_data.get("reason", "") if movement_data else "",
                help="Optional reason for the movement"
            )
            
            # Form submission
            validate_button = st.form_submit_button("🔍 Validate Movement", type="primary")
            
            if validate_button:
                # Prepare movement data
                validation_movement_data = {
                    "item_id": item_id,
                    "movement_type": movement_type,
                    "quantity_moved": quantity_moved,
                    "from_location_id": from_location_id if from_location_id > 0 else None,
                    "to_location_id": to_location_id if to_location_id > 0 else None,
                    "reason": reason if safe_strip(reason) else None
                }
                
                # Perform validation
                with st.spinner("Validating movement..."):
                    is_valid, validation_result = validate_movement_before_execution(
                        validation_movement_data, api_client, enforce_strict
                    )
                
                # Store result in session state
                SessionManager.set(f"{key_prefix}_last_result", validation_result)
                st.rerun()
    
    with col2:
        st.markdown("**Quick Validation**")
        
        # Pre-filled validation buttons for common operations
        if st.button("🏠➡️📦 House to Container", help="Validate house to container move"):
            quick_validation_data = {
                "item_id": 1,
                "movement_type": "move",
                "from_location_id": 1,
                "to_location_id": 3,
                "quantity_moved": 1,
                "reason": "Quick validation test"
            }
            is_valid, validation_result = validate_movement_before_execution(
                quick_validation_data, api_client
            )
            SessionManager.set(f"{key_prefix}_last_result", validation_result)
            st.rerun()
        
        if st.button("➕ Create New Item", help="Validate item creation"):
            quick_validation_data = {
                "item_id": 999,  # Test ID
                "movement_type": "create",
                "to_location_id": 1,
                "quantity_moved": 1,
                "reason": "New item creation test"
            }
            is_valid, validation_result = validate_movement_before_execution(
                quick_validation_data, api_client
            )
            SessionManager.set(f"{key_prefix}_last_result", validation_result)
            st.rerun()
    
    # Display last validation result
    last_result = SessionManager.get(f"{key_prefix}_last_result")
    if last_result:
        st.markdown("---")
        st.markdown("### 📊 Validation Result")
        show_validation_result(last_result, key_prefix)
        
        return last_result
    
    return None


def create_bulk_validation_widget(key_prefix: str = "bulk_validation") -> None:
    """
    Create a widget for bulk movement validation.
    
    Args:
        key_prefix: Prefix for widget keys
    """
    st.markdown("### 📦 Bulk Movement Validation")
    
    api_client = APIClient()
    
    # CSV upload for bulk movements
    uploaded_file = st.file_uploader(
        "Upload CSV with movement data",
        type=['csv'],
        help="CSV should have columns: item_id, movement_type, from_location_id, to_location_id, quantity_moved, reason",
        key=f"{key_prefix}_upload"
    )
    
    movements_data = []
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.markdown("**📋 Uploaded Movements:**")
            st.dataframe(df)
            
            # Convert to movement data
            movements_data = df.to_dict('records')
            
            # Clean up the data
            for movement in movements_data:
                # Handle NaN values
                for key, value in movement.items():
                    if pd.isna(value):
                        movement[key] = None
                
                # Ensure required types
                if movement.get('item_id'):
                    movement['item_id'] = int(movement['item_id'])
                if movement.get('from_location_id') and movement['from_location_id'] != '':
                    movement['from_location_id'] = int(movement['from_location_id'])
                else:
                    movement['from_location_id'] = None
                if movement.get('to_location_id') and movement['to_location_id'] != '':
                    movement['to_location_id'] = int(movement['to_location_id'])
                else:
                    movement['to_location_id'] = None
                if movement.get('quantity_moved'):
                    movement['quantity_moved'] = int(movement['quantity_moved'])
            
        except Exception as e:
            show_error(f"Failed to process CSV file: {str(e)}")
            return
    
    # Manual entry for bulk movements
    with st.expander("➕ Add Movements Manually", expanded=not uploaded_file):
        if f"{key_prefix}_movements" not in st.session_state:
            st.session_state[f"{key_prefix}_movements"] = []
        
        with st.form(f"{key_prefix}_add_movement"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                item_id = st.number_input("Item ID", min_value=1, value=1)
                movement_type = st.selectbox("Type", ["move", "create", "adjust", "split", "merge"])
            
            with col2:
                from_location_id = st.number_input("From Location", min_value=0, value=0)
                to_location_id = st.number_input("To Location", min_value=0, value=0)
            
            with col3:
                quantity_moved = st.number_input("Quantity", min_value=1, value=1)
                reason = st.text_input("Reason", placeholder="Optional reason")
            
            if st.form_submit_button("Add Movement"):
                new_movement = {
                    "item_id": item_id,
                    "movement_type": movement_type,
                    "from_location_id": from_location_id if from_location_id > 0 else None,
                    "to_location_id": to_location_id if to_location_id > 0 else None,
                    "quantity_moved": quantity_moved,
                    "reason": reason if safe_strip(reason) else None
                }
                st.session_state[f"{key_prefix}_movements"].append(new_movement)
                st.rerun()
        
        # Show current movements
        if st.session_state[f"{key_prefix}_movements"]:
            st.markdown("**Current Movements:**")
            movements_df = pd.DataFrame(st.session_state[f"{key_prefix}_movements"])
            st.dataframe(movements_df)
            
            if st.button("🗑️ Clear All Movements"):
                st.session_state[f"{key_prefix}_movements"] = []
                st.rerun()
            
            movements_data = st.session_state[f"{key_prefix}_movements"]
    
    # Bulk validation controls
    if movements_data:
        col1, col2 = st.columns(2)
        
        with col1:
            enforce_atomic = st.checkbox(
                "Atomic Validation",
                value=True,
                help="All movements must pass validation"
            )
        
        with col2:
            if st.button("🔍 Validate All Movements", type="primary"):
                with st.spinner("Performing bulk validation..."):
                    try:
                        bulk_result = api_client.validate_bulk_movement(movements_data, enforce_atomic)
                        SessionManager.set(f"{key_prefix}_bulk_result", bulk_result)
                        st.rerun()
                    except Exception as e:
                        show_error(f"Bulk validation failed: {str(e)}")
        
        # Display bulk validation results
        bulk_result = SessionManager.get(f"{key_prefix}_bulk_result")
        if bulk_result:
            st.markdown("---")
            st.markdown("### 📊 Bulk Validation Results")
            
            overall = bulk_result.get("overall_result", {})
            individual = bulk_result.get("individual_results", [])
            
            # Overall summary
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Movements", bulk_result.get("total_movements", 0))
            
            with col2:
                st.metric("Valid Movements", bulk_result.get("valid_movements", 0))
            
            with col3:
                st.metric("Failed Movements", bulk_result.get("failed_movements", 0))
            
            # Overall result
            if overall.get("is_valid", False):
                show_success("✅ All movements passed validation")
            else:
                show_error("❌ Bulk validation failed")
            
            # Display overall errors and warnings
            if overall.get("errors"):
                st.markdown("**🔍 Overall Issues:**")
                for error in overall["errors"]:
                    st.error(error)
            
            if overall.get("warnings"):
                for warning in overall["warnings"]:
                    st.warning(warning)
            
            # Individual results
            if individual:
                st.markdown("**📋 Individual Movement Results:**")
                
                for i, result in enumerate(individual):
                    with st.expander(f"Movement {i+1} - {'✅ Valid' if result['is_valid'] else '❌ Invalid'}"):
                        if result.get("errors"):
                            st.markdown("**Errors:**")
                            for error in result["errors"]:
                                st.error(error)
                        
                        if result.get("warnings"):
                            st.markdown("**Warnings:**")
                            for warning in result["warnings"]:
                                st.warning(warning)
                        
                        if result.get("business_rules_applied"):
                            st.markdown("**Business Rules Applied:**")
                            for rule in result["business_rules_applied"]:
                                st.info(f"✓ {rule}")


def show_validation_report_widget(key_prefix: str = "validation_report") -> None:
    """
    Display validation system report widget.
    
    Args:
        key_prefix: Prefix for widget keys
    """
    st.markdown("### 📊 Validation System Report")
    
    api_client = APIClient()
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown("**Report Options**")
        
        item_id_filter = st.number_input(
            "Filter by Item ID",
            min_value=0,
            value=0,
            help="0 for all items"
        )
        
        if st.button("📊 Generate Report", type="primary"):
            with st.spinner("Generating validation report..."):
                try:
                    item_filter = item_id_filter if item_id_filter > 0 else None
                    report = api_client.get_validation_report(item_filter)
                    SessionManager.set(f"{key_prefix}_report", report)
                    st.rerun()
                except Exception as e:
                    show_error(f"Failed to generate report: {str(e)}")
    
    with col2:
        report = SessionManager.get(f"{key_prefix}_report")
        if report:
            st.markdown("**📋 Validation Report**")
            
            # Business rules status
            business_rules = report.get("business_rules", {})
            if business_rules:
                st.markdown("**🔧 Business Rules Status:**")
                
                for rule_name, rule_config in business_rules.items():
                    enabled = rule_config.get("enabled", False)
                    status_icon = "✅" if enabled else "❌"
                    description = rule_config.get("description", "No description")
                    
                    st.markdown(f"{status_icon} **{rule_name.replace('_', ' ').title()}**: {description}")
            
            # System health
            system_health = report.get("system_health", {})
            if system_health:
                st.markdown("**🏥 System Health:**")
                
                col1_health, col2_health = st.columns(2)
                
                with col1_health:
                    st.metric(
                        "Movements (24h)", 
                        system_health.get("movements_last_24h", 0)
                    )
                
                with col2_health:
                    st.metric(
                        "Active Rules", 
                        system_health.get("validation_rules_active", 0)
                    )
            
            # Validation statistics
            validation_stats = report.get("validation_statistics", {})
            if validation_stats:
                movement_types = validation_stats.get("movement_types", {})
                if movement_types:
                    st.markdown("**📈 Movement Type Statistics:**")
                    
                    # Create a chart
                    chart_data = pd.DataFrame(
                        list(movement_types.items()),
                        columns=["Movement Type", "Count"]
                    )
                    st.bar_chart(chart_data.set_index("Movement Type"))


def create_business_rules_override_widget(key_prefix: str = "rules_override") -> None:
    """
    Create widget for managing business rule overrides.
    
    Args:
        key_prefix: Prefix for widget keys
    """
    st.markdown("### ⚙️ Business Rules Management")
    
    api_client = APIClient()
    
    st.warning("⚠️ **Warning:** Business rule overrides are temporary and will reset on server restart.")
    
    # Get current rules first
    if st.button("🔄 Load Current Rules"):
        with st.spinner("Loading current business rules..."):
            try:
                report = api_client.get_validation_report()
                current_rules = report.get("business_rules", {})
                SessionManager.set(f"{key_prefix}_current_rules", current_rules)
                st.rerun()
            except Exception as e:
                show_error(f"Failed to load rules: {str(e)}")
    
    current_rules = SessionManager.get(f"{key_prefix}_current_rules", {})
    
    if current_rules:
        st.markdown("**🔧 Current Business Rules:**")
        
        overrides = {}
        
        for rule_name, rule_config in current_rules.items():
            with st.expander(f"📋 {rule_name.replace('_', ' ').title()}", expanded=False):
                description = rule_config.get("description", "No description")
                st.markdown(f"**Description:** {description}")
                
                # Current status
                current_enabled = rule_config.get("enabled", False)
                st.markdown(f"**Current Status:** {'✅ Enabled' if current_enabled else '❌ Disabled'}")
                
                # Override options
                override_enabled = st.selectbox(
                    "Override Status",
                    options=["No Change", "Enable", "Disable"],
                    key=f"{key_prefix}_{rule_name}_enabled"
                )
                
                if override_enabled != "No Change":
                    if rule_name not in overrides:
                        overrides[rule_name] = {}
                    overrides[rule_name]["enabled"] = override_enabled == "Enable"
                
                # Rule-specific overrides
                if rule_name == "max_concurrent_movements":
                    limit_override = st.number_input(
                        "Max Movements Limit",
                        min_value=1,
                        value=rule_config.get("limit", 100),
                        key=f"{key_prefix}_{rule_name}_limit"
                    )
                    if limit_override != rule_config.get("limit", 100):
                        if rule_name not in overrides:
                            overrides[rule_name] = {}
                        overrides[rule_name]["limit"] = limit_override
                
                elif rule_name == "location_hierarchy_validation":
                    max_depth_override = st.number_input(
                        "Max Location Depth",
                        min_value=1,
                        value=rule_config.get("max_depth", 4),
                        key=f"{key_prefix}_{rule_name}_max_depth"
                    )
                    if max_depth_override != rule_config.get("max_depth", 4):
                        if rule_name not in overrides:
                            overrides[rule_name] = {}
                        overrides[rule_name]["max_depth"] = max_depth_override
        
        # Apply overrides
        if overrides:
            if st.button("🚀 Apply Overrides", type="primary"):
                with st.spinner("Applying business rule overrides..."):
                    try:
                        result = api_client.apply_business_rule_overrides(overrides)
                        show_success("Business rule overrides applied successfully!")
                        
                        # Show result
                        with st.expander("📋 Override Result", expanded=True):
                            st.json(result)
                        
                        # Refresh current rules
                        SessionManager.clear(f"{key_prefix}_current_rules")
                        
                    except Exception as e:
                        show_error(f"Failed to apply overrides: {str(e)}")