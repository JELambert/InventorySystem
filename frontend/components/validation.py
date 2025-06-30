"""
Advanced data validation components for the Home Inventory System.

This module provides comprehensive validation for location data,
including real-time validation, business rules, and data integrity checks.
"""

import streamlit as st
import re
from typing import List, Dict, Any, Optional, Tuple, Callable
from datetime import datetime
import logging

from utils.api_client import APIClient
from utils.helpers import show_error, show_warning, show_success

logger = logging.getLogger(__name__)

class ValidationRule:
    """Represents a single validation rule."""
    
    def __init__(self, 
                 field: str,
                 validator: Callable,
                 message: str,
                 severity: str = "error"):
        self.field = field
        self.validator = validator
        self.message = message
        self.severity = severity  # "error", "warning", "info"
    
    def validate(self, value: Any, context: Dict[str, Any] = None) -> Tuple[bool, str]:
        """Validate the value and return (is_valid, message)."""
        try:
            is_valid = self.validator(value, context or {})
            return is_valid, self.message if not is_valid else ""
        except Exception as e:
            logger.error(f"Validation rule error for {self.field}: {e}")
            return False, f"Validation error: {str(e)}"

class LocationValidator:
    """Comprehensive location data validator."""
    
    def __init__(self, api_client: Optional[APIClient] = None):
        self.api_client = api_client
        self.rules = self._create_validation_rules()
    
    def _create_validation_rules(self) -> List[ValidationRule]:
        """Create all validation rules."""
        return [
            # Name validation
            ValidationRule(
                "name",
                self._validate_name_required,
                "Location name is required"
            ),
            ValidationRule(
                "name",
                self._validate_name_length,
                "Location name must be between 1 and 255 characters"
            ),
            ValidationRule(
                "name",
                self._validate_name_characters,
                "Location name contains invalid characters",
                "warning"
            ),
            ValidationRule(
                "name",
                self._validate_name_uniqueness,
                "A location with this name already exists in the same parent",
                "warning"
            ),
            
            # Location type validation
            ValidationRule(
                "location_type",
                self._validate_type_required,
                "Location type is required"
            ),
            ValidationRule(
                "location_type",
                self._validate_type_valid,
                "Invalid location type"
            ),
            ValidationRule(
                "location_type",
                self._validate_hierarchy_rules,
                "Location type doesn't follow hierarchy rules"
            ),
            
            # Description validation
            ValidationRule(
                "description",
                self._validate_description_length,
                "Description must be less than 500 characters",
                "warning"
            ),
            
            # Parent validation
            ValidationRule(
                "parent_id",
                self._validate_parent_hierarchy,
                "Parent location type doesn't support this child type"
            ),
            ValidationRule(
                "parent_id",
                self._validate_no_circular_reference,
                "Cannot set a location as its own parent or descendant"
            ),
        ]
    
    # Validation methods
    def _validate_name_required(self, value: str, context: Dict) -> bool:
        return bool(value and value.strip())
    
    def _validate_name_length(self, value: str, context: Dict) -> bool:
        if not value:
            return True  # Handled by required validation
        return 1 <= len(value.strip()) <= 255
    
    def _validate_name_characters(self, value: str, context: Dict) -> bool:
        if not value:
            return True
        # Allow alphanumeric, spaces, hyphens, underscores, parentheses
        pattern = r'^[a-zA-Z0-9\s\-_()]+$'
        return bool(re.match(pattern, value))
    
    def _validate_name_uniqueness(self, value: str, context: Dict) -> bool:
        if not value or not self.api_client:
            return True
        
        try:
            # Search for existing locations with same name
            existing = self.api_client.search_locations({'pattern': value})
            
            # Filter by parent if specified
            parent_id = context.get('parent_id')
            location_id = context.get('location_id')  # For editing
            
            for loc in existing:
                # Skip self when editing
                if location_id and loc['id'] == location_id:
                    continue
                
                # Check if same parent
                if loc.get('parent_id') == parent_id and loc['name'].lower() == value.lower():
                    return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Name uniqueness check failed: {e}")
            return True  # Don't block on API errors
    
    def _validate_type_required(self, value: str, context: Dict) -> bool:
        return bool(value)
    
    def _validate_type_valid(self, value: str, context: Dict) -> bool:
        if not value:
            return True
        return value in ['house', 'room', 'container', 'shelf']
    
    def _validate_hierarchy_rules(self, value: str, context: Dict) -> bool:
        if not value:
            return True
        
        parent_id = context.get('parent_id')
        parent_type = context.get('parent_type')
        
        # If no parent, only houses are allowed at root level
        if not parent_id:
            return value == 'house'
        
        # Hierarchy rules
        valid_children = {
            'house': ['room'],
            'room': ['container'], 
            'container': ['shelf'],
            'shelf': []  # Shelves can't have children
        }
        
        if parent_type:
            return value in valid_children.get(parent_type, [])
        
        return True
    
    def _validate_description_length(self, value: str, context: Dict) -> bool:
        if not value:
            return True
        return len(value) <= 500
    
    def _validate_parent_hierarchy(self, value: Any, context: Dict) -> bool:
        if not value:
            return True
        
        location_type = context.get('location_type')
        parent_type = context.get('parent_type')
        
        if not location_type or not parent_type:
            return True
        
        # Same as hierarchy rules validation
        valid_children = {
            'house': ['room'],
            'room': ['container'],
            'container': ['shelf'],
            'shelf': []
        }
        
        return location_type in valid_children.get(parent_type, [])
    
    def _validate_no_circular_reference(self, value: Any, context: Dict) -> bool:
        if not value or not self.api_client:
            return True
        
        location_id = context.get('location_id')
        if not location_id:
            return True  # New location, can't be circular
        
        try:
            # Check if parent is a descendant of this location
            descendants = self.api_client.get_location_children(location_id)
            descendant_ids = [d['id'] for d in descendants]
            
            return value not in descendant_ids
            
        except Exception as e:
            logger.warning(f"Circular reference check failed: {e}")
            return True
    
    def validate_location_data(self, data: Dict[str, Any]) -> Dict[str, List[Dict[str, str]]]:
        """Validate complete location data."""
        results = {
            'errors': [],
            'warnings': [],
            'info': []
        }
        
        # Enhance context with additional data
        context = data.copy()
        
        # Get parent type if parent_id is specified
        if data.get('parent_id') and self.api_client:
            try:
                parent = self.api_client.get_location(data['parent_id'])
                context['parent_type'] = parent.get('location_type')
            except Exception:
                pass
        
        # Run all validation rules
        for rule in self.rules:
            field_value = data.get(rule.field)
            is_valid, message = rule.validate(field_value, context)
            
            if not is_valid and message:
                validation_result = {
                    'field': rule.field,
                    'message': message
                }
                
                if rule.severity == 'error':
                    results['errors'].append(validation_result)
                elif rule.severity == 'warning':
                    results['warnings'].append(validation_result)
                else:
                    results['info'].append(validation_result)
        
        return results

def create_real_time_validator(
    field_name: str,
    validator: LocationValidator,
    current_data: Dict[str, Any],
    key_suffix: str = ""
) -> None:
    """Create real-time validation display for a field."""
    
    validation_key = f"validation_{field_name}_{key_suffix}"
    
    if validation_key in st.session_state:
        results = st.session_state[validation_key]
        
        # Display errors
        for error in results.get('errors', []):
            if error['field'] == field_name:
                st.error(f"❌ {error['message']}")
        
        # Display warnings
        for warning in results.get('warnings', []):
            if warning['field'] == field_name:
                st.warning(f"⚠️ {warning['message']}")
        
        # Display info
        for info in results.get('info', []):
            if info['field'] == field_name:
                st.info(f"ℹ️ {info['message']}")

def validate_and_show_results(
    data: Dict[str, Any],
    validator: LocationValidator,
    key_suffix: str = ""
) -> bool:
    """Validate data and show results, return True if valid."""
    
    validation_key = f"validation_results_{key_suffix}"
    
    # Run validation
    results = validator.validate_location_data(data)
    st.session_state[validation_key] = results
    
    # Show summary
    error_count = len(results['errors'])
    warning_count = len(results['warnings'])
    
    if error_count > 0:
        st.error(f"❌ {error_count} validation error(s) found. Please fix before proceeding.")
        
        with st.expander("View Errors"):
            for error in results['errors']:
                st.write(f"• **{error['field']}**: {error['message']}")
    
    if warning_count > 0:
        st.warning(f"⚠️ {warning_count} warning(s). You can proceed but consider addressing these.")
        
        with st.expander("View Warnings"):
            for warning in results['warnings']:
                st.write(f"• **{warning['field']}**: {warning['message']}")
    
    if error_count == 0 and warning_count == 0:
        st.success("✅ All validation checks passed!")
    
    return error_count == 0

def create_validation_summary_widget(api_client: Optional[APIClient] = None):
    """Create a widget showing overall data validation status."""
    
    if not api_client:
        st.info("API client not available for validation checks")
        return
    
    with st.expander("🔍 Data Validation Summary"):
        try:
            # Get all locations for validation
            locations = api_client.get_locations(limit=1000)
            
            validator = LocationValidator(api_client)
            
            total_errors = 0
            total_warnings = 0
            
            # Validate each location
            for location in locations:
                results = validator.validate_location_data(location)
                total_errors += len(results['errors'])
                total_warnings += len(results['warnings'])
            
            # Show summary metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Locations", len(locations))
            
            with col2:
                st.metric("Validation Errors", total_errors)
            
            with col3:
                st.metric("Validation Warnings", total_warnings)
            
            # Show status
            if total_errors == 0:
                st.success("✅ No validation errors found!")
            else:
                st.error(f"❌ {total_errors} validation errors need attention")
            
            if total_warnings > 0:
                st.warning(f"⚠️ {total_warnings} warnings to consider")
            
        except Exception as e:
            st.error(f"Failed to run validation summary: {e}")

def create_enhanced_form_validation(form_data: Dict[str, Any], 
                                  api_client: Optional[APIClient] = None,
                                  location_id: Optional[int] = None) -> bool:
    """Enhanced form validation with real-time feedback."""
    
    if not api_client:
        st.warning("Real-time validation unavailable - API client not found")
        return True
    
    # Create validator
    validator = LocationValidator(api_client)
    
    # Add location_id to context for editing scenarios
    validation_data = form_data.copy()
    if location_id:
        validation_data['location_id'] = location_id
    
    # Run validation
    is_valid = validate_and_show_results(validation_data, validator, "form")
    
    return is_valid