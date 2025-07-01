"""
Error Boundary Components for Streamlit Frontend.

Provides reusable error boundary components for different parts of the application,
including page-level, component-level, and form-level error handling.
"""

import streamlit as st
import traceback
import logging
from typing import Any, Dict, List, Optional, Callable, Union
from contextlib import contextmanager
from functools import wraps

from utils.error_handling import (
    ErrorBoundary, ErrorContext, ErrorSeverity, ErrorCategory, 
    ErrorReporter, safe_execute, RetryManager
)
from utils.notifications import (
    notification_manager, show_error, show_warning, show_success
)
from utils.helpers import safe_api_call

logger = logging.getLogger(__name__)


class PageErrorBoundary:
    """Page-level error boundary for comprehensive error handling."""
    
    def __init__(self, page_name: str, fallback_content: Optional[Callable] = None):
        self.page_name = page_name
        self.fallback_content = fallback_content
        self.error_count = 0
        self.max_errors = 5
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.error_count += 1
            
            # Create error context
            error_context = ErrorContext(
                error=exc_val,
                severity=self._determine_severity(exc_type),
                category=self._determine_category(exc_type),
                user_message=f"An error occurred while loading the {self.page_name} page",
                context_data={
                    'page': self.page_name,
                    'error_count': self.error_count
                }
            )
            
            # Report error
            ErrorReporter.report_error(error_context)
            
            # Show error to user
            self._display_page_error(error_context)
            
            # Show fallback content if available
            if self.fallback_content and self.error_count <= self.max_errors:
                try:
                    st.markdown("---")
                    st.subheader("🔧 Fallback Mode")
                    self.fallback_content()
                except Exception as fallback_error:
                    logger.error(f"Fallback content also failed: {fallback_error}")
                    self._show_minimal_recovery_options()
            else:
                self._show_minimal_recovery_options()
            
            # Suppress the exception to prevent app crash
            return True
    
    def _determine_severity(self, exc_type: type) -> ErrorSeverity:
        """Determine error severity based on exception type."""
        if issubclass(exc_type, (ConnectionError, TimeoutError)):
            return ErrorSeverity.HIGH
        elif issubclass(exc_type, (ValueError, TypeError, KeyError)):
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.HIGH  # Page-level errors are generally serious
    
    def _determine_category(self, exc_type: type) -> ErrorCategory:
        """Determine error category based on exception type."""
        if issubclass(exc_type, (ConnectionError, TimeoutError)):
            return ErrorCategory.NETWORK
        elif issubclass(exc_type, (ValueError, TypeError)):
            return ErrorCategory.DATA
        elif issubclass(exc_type, KeyError):
            return ErrorCategory.SESSION
        else:
            return ErrorCategory.UI
    
    def _display_page_error(self, error_context: ErrorContext):
        """Display page-level error with recovery options."""
        st.error(f"🚨 **Page Error**: {error_context.user_message}")
        
        # Show error details in expander
        with st.expander("🔍 Error Details", expanded=False):
            st.code(f"Error ID: {error_context.error_id}")
            st.code(f"Page: {self.page_name}")
            st.code(f"Category: {error_context.category.value}")
            st.code(f"Technical: {error_context.technical_message}")
            
            if st.button("📋 Copy Error Info", key=f"copy_error_{error_context.error_id}"):
                error_info = f"""
Error ID: {error_context.error_id}
Page: {self.page_name}
Time: {error_context.timestamp}
Category: {error_context.category.value}
Message: {error_context.technical_message}
                """.strip()
                st.code(error_info)
                st.success("Error information displayed above for copying")
    
    def _show_minimal_recovery_options(self):
        """Show minimal recovery options when everything else fails."""
        st.markdown("### 🛠️ Recovery Options")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Refresh Page", key="page_refresh"):
                st.rerun()
        
        with col2:
            if st.button("🏠 Go to Dashboard", key="go_dashboard"):
                st.switch_page("pages/01_📊_Dashboard.py")
        
        with col3:
            if st.button("🧹 Clear Session", key="clear_session"):
                # Clear session state
                for key in list(st.session_state.keys()):
                    if not key.startswith('_'):  # Keep internal streamlit keys
                        del st.session_state[key]
                st.success("Session cleared. Please refresh the page.")


class ComponentErrorBoundary:
    """Component-level error boundary for specific UI components."""
    
    def __init__(self, component_name: str, show_details: bool = False, 
                 fallback_component: Optional[Callable] = None):
        self.component_name = component_name
        self.show_details = show_details
        self.fallback_component = fallback_component
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Create error context
            error_context = ErrorContext(
                error=exc_val,
                severity=ErrorSeverity.MEDIUM,
                category=self._determine_category(exc_type),
                user_message=f"Error in {self.component_name} component",
                context_data={'component': self.component_name}
            )
            
            # Report error
            ErrorReporter.report_error(error_context)
            
            # Show error with recovery options
            self._display_component_error(error_context)
            
            # Try fallback component
            if self.fallback_component:
                try:
                    st.markdown("*Showing fallback content:*")
                    self.fallback_component()
                except Exception as fallback_error:
                    logger.error(f"Fallback component also failed: {fallback_error}")
                    st.warning("⚠️ Fallback content is also unavailable")
            
            # Suppress the exception
            return True
    
    def _determine_category(self, exc_type: type) -> ErrorCategory:
        """Determine error category based on exception type."""
        if issubclass(exc_type, (ConnectionError, TimeoutError)):
            return ErrorCategory.NETWORK
        elif issubclass(exc_type, (ValueError, TypeError)):
            return ErrorCategory.DATA
        elif issubclass(exc_type, KeyError):
            return ErrorCategory.SESSION
        else:
            return ErrorCategory.UI
    
    def _display_component_error(self, error_context: ErrorContext):
        """Display component error with recovery options."""
        st.warning(f"⚠️ {error_context.user_message}")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if self.show_details:
                with st.expander("Technical Details", expanded=False):
                    st.code(f"Error ID: {error_context.error_id}")
                    st.code(f"Component: {self.component_name}")
                    st.code(f"Technical: {error_context.technical_message}")
        
        with col2:
            if st.button("🔄 Retry", key=f"retry_component_{error_context.error_id}"):
                st.rerun()


class FormErrorBoundary:
    """Specialized error boundary for form components with validation."""
    
    def __init__(self, form_name: str):
        self.form_name = form_name
        self.validation_errors = []
        self.form_errors = []
    
    def add_validation_error(self, field: str, message: str):
        """Add a field validation error."""
        self.validation_errors.append({'field': field, 'message': message})
    
    def add_form_error(self, message: str):
        """Add a form-level error."""
        self.form_errors.append(message)
    
    def has_errors(self) -> bool:
        """Check if form has any errors."""
        return len(self.validation_errors) > 0 or len(self.form_errors) > 0
    
    def display_errors(self):
        """Display all form errors."""
        if self.form_errors:
            for error in self.form_errors:
                st.error(f"❌ {error}")
        
        if self.validation_errors:
            st.error("❌ **Please correct the following errors:**")
            for error in self.validation_errors:
                st.markdown(f"• **{error['field']}**: {error['message']}")
    
    def clear_errors(self):
        """Clear all form errors."""
        self.validation_errors.clear()
        self.form_errors.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Create error context
            error_context = ErrorContext(
                error=exc_val,
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.USER_INPUT,
                user_message=f"Error processing {self.form_name} form",
                context_data={
                    'form': self.form_name,
                    'validation_errors': self.validation_errors,
                    'form_errors': self.form_errors
                }
            )
            
            # Report error
            ErrorReporter.report_error(error_context)
            
            # Show form error
            st.error(f"❌ Error processing {self.form_name} form: {error_context.technical_message}")
            
            # Show existing form errors
            self.display_errors()
            
            # Suppress the exception
            return True


@contextmanager
def safe_component(component_name: str, fallback_content: Optional[str] = None):
    """Context manager for safe component rendering."""
    try:
        yield
    except Exception as e:
        logger.error(f"Error in component {component_name}: {e}")
        st.error(f"⚠️ Error loading {component_name}")
        
        if fallback_content:
            st.info(fallback_content)
        
        if st.button(f"🔄 Retry {component_name}", key=f"retry_{component_name}"):
            st.rerun()


def error_boundary_decorator(
    component_name: str,
    fallback_func: Optional[Callable] = None,
    show_details: bool = False
):
    """Decorator to wrap functions with error boundary."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_context = ErrorContext(
                    error=e,
                    severity=ErrorSeverity.MEDIUM,
                    category=ErrorCategory.UI,
                    user_message=f"Error in {component_name}",
                    context_data={'component': component_name, 'function': func.__name__}
                )
                
                ErrorReporter.report_error(error_context)
                
                st.error(f"⚠️ Error in {component_name}: {error_context.user_message}")
                
                if show_details:
                    with st.expander("Error Details", expanded=False):
                        st.code(f"Error ID: {error_context.error_id}")
                        st.code(f"Function: {func.__name__}")
                        st.code(f"Technical: {error_context.technical_message}")
                
                if fallback_func:
                    try:
                        st.info("Showing fallback content:")
                        return fallback_func(*args, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"Fallback function also failed: {fallback_error}")
                        st.warning("Fallback content is also unavailable")
                
                if st.button(f"🔄 Retry {component_name}", key=f"retry_{func.__name__}"):
                    st.rerun()
                
                return None
        return wrapper
    return decorator


class DataLoadingErrorBoundary:
    """Specialized error boundary for data loading operations."""
    
    def __init__(self, data_source: str, retry_button: bool = True, 
                 cache_fallback: bool = True):
        self.data_source = data_source
        self.retry_button = retry_button
        self.cache_fallback = cache_fallback
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Create error context
            error_context = ErrorContext(
                error=exc_val,
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.NETWORK if isinstance(exc_val, ConnectionError) else ErrorCategory.DATA,
                user_message=f"Failed to load data from {self.data_source}",
                context_data={'data_source': self.data_source}
            )
            
            # Report error
            ErrorReporter.report_error(error_context)
            
            # Show data loading error
            st.error(f"❌ Unable to load data from {self.data_source}")
            
            # Show recovery options
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if self.retry_button and st.button("🔄 Retry", key=f"retry_data_{error_context.error_id}"):
                    st.rerun()
            
            with col2:
                if self.cache_fallback and st.button("📱 Use Cached Data", key=f"cache_data_{error_context.error_id}"):
                    st.info("Attempting to use cached data...")
                    st.rerun()
            
            with col3:
                if st.button("🏠 Go Back", key=f"back_data_{error_context.error_id}"):
                    st.switch_page("pages/01_📊_Dashboard.py")
            
            # Show technical details
            with st.expander("Technical Details", expanded=False):
                st.code(f"Error ID: {error_context.error_id}")
                st.code(f"Data Source: {self.data_source}")
                st.code(f"Error: {error_context.technical_message}")
            
            # Suppress the exception
            return True


def safe_data_loader(data_source: str, cache_key: Optional[str] = None):
    """Decorator for safe data loading with caching and error handling."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with DataLoadingErrorBoundary(data_source):
                # Try to load data
                data = func(*args, **kwargs)
                
                # Cache successful data if cache_key provided
                if cache_key and data is not None:
                    st.session_state[f"cached_{cache_key}"] = data
                    st.session_state[f"cached_{cache_key}_timestamp"] = time.time()
                
                return data
        return wrapper
    return decorator


class NetworkErrorHandler:
    """Specialized handler for network-related errors."""
    
    @staticmethod
    def handle_api_error(error: Exception, operation: str = "API call") -> bool:
        """
        Handle API errors with user-friendly messages and recovery options.
        
        Returns:
            True if error was handled, False if it should be re-raised
        """
        from utils.api_client import APIError
        
        if isinstance(error, APIError):
            if error.status_code == 404:
                st.warning(f"⚠️ The requested resource was not found")
            elif error.status_code == 403:
                st.error(f"❌ Access denied. Please check your permissions.")
            elif error.status_code == 500:
                st.error(f"❌ Server error. Please try again later.")
                if st.button("🔄 Retry Operation"):
                    st.rerun()
            elif error.status_code == 503:
                st.error(f"❌ Service temporarily unavailable")
                st.info("The service may be under maintenance. Please try again in a few minutes.")
            else:
                st.error(f"❌ {operation} failed: {error.message}")
            
            # Show technical details
            with st.expander("Technical Details", expanded=False):
                st.json({
                    'status_code': error.status_code,
                    'message': error.message,
                    'response_data': error.response_data
                })
            
            return True
        
        return False


# Convenience functions for quick error boundary usage

def with_page_error_boundary(page_name: str, fallback_content: Optional[Callable] = None):
    """Decorator for page-level error boundary."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with PageErrorBoundary(page_name, fallback_content):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def with_component_error_boundary(component_name: str, fallback_component: Optional[Callable] = None):
    """Decorator for component-level error boundary."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with ComponentErrorBoundary(component_name, fallback_component=fallback_component):
                return func(*args, **kwargs)
        return wrapper
    return decorator