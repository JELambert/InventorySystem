"""
Comprehensive Error Handling System for Streamlit Frontend.

Provides error boundaries, retry mechanisms, graceful degradation,
and user-friendly error reporting capabilities.
"""

import streamlit as st
import time
import traceback
import logging
from typing import Any, Dict, List, Optional, Callable, Union
from functools import wraps
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import json

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for categorization and response."""
    LOW = "low"           # Minor issues, system continues normally
    MEDIUM = "medium"     # Moderate issues, some functionality affected
    HIGH = "high"         # Major issues, significant functionality lost
    CRITICAL = "critical" # Critical issues, system largely unusable


class ErrorCategory(Enum):
    """Error categories for better classification and handling."""
    NETWORK = "network"           # API calls, network connectivity
    DATA = "data"                # Data validation, processing errors
    AUTH = "authentication"      # Authentication and authorization
    SESSION = "session"          # Session state issues
    UI = "ui"                   # User interface errors
    SYSTEM = "system"           # System-level errors
    USER_INPUT = "user_input"   # User input validation


class RetryStrategy(Enum):
    """Retry strategy types."""
    NONE = "none"
    IMMEDIATE = "immediate"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    CUSTOM = "custom"


class ErrorContext:
    """Container for error context information."""
    
    def __init__(
        self,
        error: Exception,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        user_message: Optional[str] = None,
        technical_message: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
        recoverable: bool = True,
        retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        max_retries: int = 3
    ):
        self.error = error
        self.severity = severity
        self.category = category
        self.user_message = user_message or self._generate_user_message()
        self.technical_message = technical_message or str(error)
        self.context_data = context_data or {}
        self.recoverable = recoverable
        self.retry_strategy = retry_strategy
        self.max_retries = max_retries
        self.timestamp = datetime.now()
        self.error_id = self._generate_error_id()
        self.stack_trace = traceback.format_exc()
    
    def _generate_user_message(self) -> str:
        """Generate user-friendly error message based on category and error type."""
        if self.category == ErrorCategory.NETWORK:
            return "Unable to connect to the server. Please check your internet connection and try again."
        elif self.category == ErrorCategory.DATA:
            return "There was an issue processing your data. Please verify your input and try again."
        elif self.category == ErrorCategory.AUTH:
            return "Authentication failed. Please log in again."
        elif self.category == ErrorCategory.SESSION:
            return "Your session has expired. Please refresh the page."
        elif self.category == ErrorCategory.UI:
            return "A display error occurred. Please refresh the page."
        elif self.category == ErrorCategory.USER_INPUT:
            return "Please check your input and try again."
        else:
            return "An unexpected error occurred. Please try again or contact support if the problem persists."
    
    def _generate_error_id(self) -> str:
        """Generate unique error ID for tracking."""
        error_string = f"{self.timestamp.isoformat()}{str(self.error)}{self.category.value}"
        return hashlib.md5(error_string.encode()).hexdigest()[:8]


class RetryManager:
    """Manages retry logic for failed operations."""
    
    @staticmethod
    def calculate_delay(attempt: int, strategy: RetryStrategy, base_delay: float = 1.0) -> float:
        """Calculate delay for retry attempt based on strategy."""
        if strategy == RetryStrategy.NONE:
            return 0
        elif strategy == RetryStrategy.IMMEDIATE:
            return 0
        elif strategy == RetryStrategy.LINEAR:
            return base_delay * attempt
        elif strategy == RetryStrategy.EXPONENTIAL:
            return base_delay * (2 ** attempt)
        else:
            return base_delay
    
    @staticmethod
    def should_retry(error: Exception, attempt: int, max_retries: int, 
                    retryable_errors: Optional[List[type]] = None) -> bool:
        """Determine if operation should be retried."""
        if attempt >= max_retries:
            return False
        
        # Default retryable errors
        if retryable_errors is None:
            retryable_errors = [ConnectionError, TimeoutError, OSError]
        
        return any(isinstance(error, error_type) for error_type in retryable_errors)


class CircuitBreaker:
    """Circuit breaker pattern implementation for API calls."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_execute(self) -> bool:
        """Check if operation can be executed based on circuit state."""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if self.last_failure_time and \
               datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        """Record successful operation."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class ErrorReporter:
    """Centralized error reporting and analytics."""
    
    @staticmethod
    def report_error(error_context: ErrorContext):
        """Report error to centralized logging and analytics."""
        # Store in session state for tracking
        if 'error_history' not in st.session_state:
            st.session_state.error_history = []
        
        # Keep only last 100 errors to prevent memory issues
        if len(st.session_state.error_history) >= 100:
            st.session_state.error_history = st.session_state.error_history[-99:]
        
        error_record = {
            'error_id': error_context.error_id,
            'timestamp': error_context.timestamp.isoformat(),
            'severity': error_context.severity.value,
            'category': error_context.category.value,
            'user_message': error_context.user_message,
            'technical_message': error_context.technical_message,
            'recoverable': error_context.recoverable,
            'context_data': error_context.context_data
        }
        
        st.session_state.error_history.append(error_record)
        
        # Log to system logger
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(error_context.severity, logging.ERROR)
        
        logger.log(
            log_level,
            f"Error {error_context.error_id}: {error_context.technical_message}",
            extra={
                'error_id': error_context.error_id,
                'category': error_context.category.value,
                'severity': error_context.severity.value,
                'context': error_context.context_data
            }
        )
    
    @staticmethod
    def get_error_analytics() -> Dict[str, Any]:
        """Get error analytics from session history."""
        if 'error_history' not in st.session_state:
            return {'total_errors': 0}
        
        errors = st.session_state.error_history
        
        # Calculate analytics
        total_errors = len(errors)
        errors_by_category = {}
        errors_by_severity = {}
        recent_errors = []
        
        for error in errors:
            # Category breakdown
            category = error['category']
            errors_by_category[category] = errors_by_category.get(category, 0) + 1
            
            # Severity breakdown
            severity = error['severity']
            errors_by_severity[severity] = errors_by_severity.get(severity, 0) + 1
            
            # Recent errors (last hour)
            error_time = datetime.fromisoformat(error['timestamp'])
            if datetime.now() - error_time < timedelta(hours=1):
                recent_errors.append(error)
        
        return {
            'total_errors': total_errors,
            'errors_by_category': errors_by_category,
            'errors_by_severity': errors_by_severity,
            'recent_errors': len(recent_errors),
            'most_common_category': max(errors_by_category.items(), key=lambda x: x[1])[0] if errors_by_category else None,
            'most_common_severity': max(errors_by_severity.items(), key=lambda x: x[1])[0] if errors_by_severity else None
        }


class GracefulDegradation:
    """Utilities for graceful degradation when services are unavailable."""
    
    @staticmethod
    def with_fallback(primary_func: Callable, fallback_func: Callable, 
                     error_message: str = "Primary service unavailable, using fallback") -> Callable:
        """Decorator to provide fallback functionality."""
        def decorator(*args, **kwargs):
            try:
                return primary_func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Primary function failed, using fallback: {e}")
                st.warning(f"⚠️ {error_message}")
                return fallback_func(*args, **kwargs)
        return decorator
    
    @staticmethod
    def cached_fallback(cache_key: str, primary_func: Callable, 
                       cache_duration: int = 3600) -> Any:
        """Use cached data as fallback when primary function fails."""
        cache_timestamp_key = f"{cache_key}_timestamp"
        
        try:
            result = primary_func()
            # Cache successful result
            st.session_state[cache_key] = result
            st.session_state[cache_timestamp_key] = datetime.now()
            return result
        except Exception as e:
            # Try to use cached data
            if cache_key in st.session_state and cache_timestamp_key in st.session_state:
                cache_time = st.session_state[cache_timestamp_key]
                if datetime.now() - cache_time < timedelta(seconds=cache_duration):
                    st.warning("⚠️ Using cached data due to service unavailability")
                    return st.session_state[cache_key]
            
            # No cache available, re-raise error
            raise e


class ErrorBoundary:
    """Error boundary implementation for Streamlit components."""
    
    def __init__(self, component_name: str, show_details: bool = False):
        self.component_name = component_name
        self.show_details = show_details
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Create error context
            error_context = ErrorContext(
                error=exc_val,
                severity=self._determine_severity(exc_type),
                category=self._determine_category(exc_type),
                context_data={'component': self.component_name}
            )
            
            # Report error
            ErrorReporter.report_error(error_context)
            
            # Show user-friendly error
            self._display_error(error_context)
            
            # Suppress the exception to prevent app crash
            return True
    
    def _determine_severity(self, exc_type: type) -> ErrorSeverity:
        """Determine error severity based on exception type."""
        if issubclass(exc_type, (ConnectionError, TimeoutError)):
            return ErrorSeverity.HIGH
        elif issubclass(exc_type, (ValueError, TypeError)):
            return ErrorSeverity.MEDIUM
        elif issubclass(exc_type, KeyError):
            return ErrorSeverity.LOW
        else:
            return ErrorSeverity.MEDIUM
    
    def _determine_category(self, exc_type: type) -> ErrorCategory:
        """Determine error category based on exception type."""
        if issubclass(exc_type, (ConnectionError, TimeoutError)):
            return ErrorCategory.NETWORK
        elif issubclass(exc_type, (ValueError, TypeError)):
            return ErrorCategory.DATA
        elif issubclass(exc_type, KeyError):
            return ErrorCategory.SESSION
        else:
            return ErrorCategory.SYSTEM
    
    def _display_error(self, error_context: ErrorContext):
        """Display user-friendly error message."""
        severity_icons = {
            ErrorSeverity.LOW: "ℹ️",
            ErrorSeverity.MEDIUM: "⚠️", 
            ErrorSeverity.HIGH: "❌",
            ErrorSeverity.CRITICAL: "🚨"
        }
        
        icon = severity_icons.get(error_context.severity, "❌")
        
        if error_context.severity in [ErrorSeverity.LOW, ErrorSeverity.MEDIUM]:
            st.warning(f"{icon} {error_context.user_message}")
        else:
            st.error(f"{icon} {error_context.user_message}")
        
        # Show recovery options if available
        if error_context.recoverable:
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button(f"🔄 Retry {self.component_name}", key=f"retry_{error_context.error_id}"):
                    st.rerun()
            with col2:
                if st.button("📊 View Error Details", key=f"details_{error_context.error_id}"):
                    self.show_details = True
        
        # Show technical details if requested
        if self.show_details:
            with st.expander("🔧 Technical Details", expanded=False):
                st.code(f"Error ID: {error_context.error_id}")
                st.code(f"Category: {error_context.category.value}")
                st.code(f"Severity: {error_context.severity.value}")
                st.code(f"Technical Message: {error_context.technical_message}")
                if error_context.context_data:
                    st.json(error_context.context_data)


def safe_execute(
    func: Callable,
    *args,
    error_message: str = "Operation failed",
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    max_retries: int = 3,
    fallback_func: Optional[Callable] = None,
    **kwargs
) -> Any:
    """
    Safely execute a function with comprehensive error handling.
    
    Args:
        func: Function to execute
        error_message: User-friendly error message
        retry_strategy: Retry strategy to use
        max_retries: Maximum number of retry attempts
        fallback_func: Fallback function if primary fails
        
    Returns:
        Function result or fallback result
    """
    attempt = 0
    last_error = None
    
    while attempt <= max_retries:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            
            # Check if we should retry
            if attempt < max_retries and RetryManager.should_retry(e, attempt, max_retries):
                delay = RetryManager.calculate_delay(attempt, retry_strategy)
                if delay > 0:
                    time.sleep(delay)
                attempt += 1
                continue
            else:
                break
    
    # All retries exhausted, try fallback
    if fallback_func:
        try:
            st.warning(f"⚠️ Primary operation failed, using fallback")
            return fallback_func(*args, **kwargs)
        except Exception as fallback_error:
            logger.error(f"Fallback also failed: {fallback_error}")
    
    # Create error context and report
    error_context = ErrorContext(
        error=last_error,
        user_message=error_message,
        context_data={'function': func.__name__, 'attempts': attempt + 1}
    )
    
    ErrorReporter.report_error(error_context)
    
    # Show error to user
    st.error(f"❌ {error_message}")
    if st.checkbox("Show technical details", key=f"error_details_{error_context.error_id}"):
        st.code(str(last_error))
    
    return None


def error_handler(
    category: ErrorCategory = ErrorCategory.SYSTEM,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    user_message: Optional[str] = None,
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    max_retries: int = 3
):
    """
    Decorator for comprehensive error handling.
    
    Args:
        category: Error category
        severity: Error severity level  
        user_message: Custom user message
        retry_strategy: Retry strategy
        max_retries: Maximum retry attempts
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return safe_execute(
                func,
                *args,
                error_message=user_message or f"Error in {func.__name__}",
                retry_strategy=retry_strategy,
                max_retries=max_retries,
                **kwargs
            )
        return wrapper
    return decorator