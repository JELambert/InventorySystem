"""
Enhanced Error Handling for FastAPI Backend.

Provides structured error responses, correlation ID tracking,
and comprehensive error logging with analytics.
"""

import logging
import traceback
import time
import uuid
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.exc import IntegrityError, OperationalError
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """Standardized error codes for consistent error handling."""
    
    # General errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    
    # Database errors
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
    DATABASE_CONSTRAINT_VIOLATION = "DATABASE_CONSTRAINT_VIOLATION"
    DATABASE_INTEGRITY_ERROR = "DATABASE_INTEGRITY_ERROR"
    
    # Business logic errors
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    INVALID_OPERATION = "INVALID_OPERATION"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    
    # External service errors
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"


class ErrorSeverity(Enum):
    """Error severity levels for logging and alerting."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class StructuredError:
    """Structured error container with comprehensive context."""
    
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None
    ):
        self.error_code = error_code
        self.message = message
        self.severity = severity
        self.details = details or {}
        self.user_message = user_message or self._generate_user_message()
        self.correlation_id = correlation_id or str(uuid.uuid4())[:8]
        self.context = context or {}
        self.suggestions = suggestions or []
        self.timestamp = datetime.utcnow()
        
    def _generate_user_message(self) -> str:
        """Generate user-friendly error message based on error code."""
        user_messages = {
            ErrorCode.INTERNAL_SERVER_ERROR: "An unexpected error occurred. Please try again later.",
            ErrorCode.VALIDATION_ERROR: "Please check your input and try again.",
            ErrorCode.NOT_FOUND: "The requested resource was not found.",
            ErrorCode.UNAUTHORIZED: "Authentication is required to access this resource.",
            ErrorCode.FORBIDDEN: "You don't have permission to access this resource.",
            ErrorCode.DATABASE_CONNECTION_ERROR: "Unable to connect to the database. Please try again later.",
            ErrorCode.DATABASE_CONSTRAINT_VIOLATION: "This operation violates data constraints.",
            ErrorCode.DATABASE_INTEGRITY_ERROR: "Data integrity error. Please check your input.",
            ErrorCode.BUSINESS_RULE_VIOLATION: "This operation violates business rules.",
            ErrorCode.INVALID_OPERATION: "This operation is not allowed in the current state.",
            ErrorCode.RESOURCE_CONFLICT: "This resource is in use and cannot be modified.",
            ErrorCode.EXTERNAL_SERVICE_ERROR: "External service is unavailable. Please try again later.",
            ErrorCode.TIMEOUT_ERROR: "The operation timed out. Please try again.",
            ErrorCode.RATE_LIMIT_EXCEEDED: "Too many requests. Please wait before trying again."
        }
        return user_messages.get(self.error_code, self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON response."""
        return {
            "error": {
                "code": self.error_code.value,
                "message": self.message,
                "user_message": self.user_message,
                "severity": self.severity.value,
                "correlation_id": self.correlation_id,
                "timestamp": self.timestamp.isoformat(),
                "details": self.details,
                "context": self.context,
                "suggestions": self.suggestions
            }
        }
    
    def to_http_exception(self, status_code: int = 500) -> HTTPException:
        """Convert to FastAPI HTTPException."""
        return HTTPException(
            status_code=status_code,
            detail=self.to_dict()["error"]
        )


class ErrorAnalytics:
    """Error analytics and tracking system."""
    
    def __init__(self):
        self.error_stats = {}
        self.error_history = []
        self.max_history = 1000  # Keep last 1000 errors
    
    def record_error(self, structured_error: StructuredError, context: Dict[str, Any] = None):
        """Record error for analytics tracking."""
        error_record = {
            "timestamp": structured_error.timestamp,
            "error_code": structured_error.error_code.value,
            "severity": structured_error.severity.value,
            "correlation_id": structured_error.correlation_id,
            "message": structured_error.message,
            "context": context or {}
        }
        
        # Add to history
        self.error_history.append(error_record)
        
        # Trim history if too long
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history:]
        
        # Update statistics
        error_key = structured_error.error_code.value
        if error_key not in self.error_stats:
            self.error_stats[error_key] = {
                "count": 0,
                "first_seen": structured_error.timestamp,
                "last_seen": structured_error.timestamp,
                "severity_distribution": {}
            }
        
        stats = self.error_stats[error_key]
        stats["count"] += 1
        stats["last_seen"] = structured_error.timestamp
        
        severity_key = structured_error.severity.value
        if severity_key not in stats["severity_distribution"]:
            stats["severity_distribution"][severity_key] = 0
        stats["severity_distribution"][severity_key] += 1
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for the specified time period."""
        cutoff_time = datetime.utcnow().replace(hour=datetime.utcnow().hour - hours)
        
        recent_errors = [
            error for error in self.error_history
            if error["timestamp"] > cutoff_time
        ]
        
        # Calculate statistics
        total_errors = len(recent_errors)
        error_counts = {}
        severity_counts = {}
        
        for error in recent_errors:
            error_code = error["error_code"]
            severity = error["severity"]
            
            error_counts[error_code] = error_counts.get(error_code, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Find most common errors
        most_common_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "time_period_hours": hours,
            "total_errors": total_errors,
            "error_rate": round(total_errors / hours, 2) if hours > 0 else 0,
            "most_common_errors": most_common_errors,
            "severity_distribution": severity_counts,
            "recent_errors": recent_errors[-10:] if recent_errors else []  # Last 10 errors
        }


# Global error analytics instance
error_analytics = ErrorAnalytics()


class ErrorHandler:
    """Central error handler with context-aware error processing."""
    
    @staticmethod
    def handle_database_error(error: Exception, context: Dict[str, Any] = None) -> StructuredError:
        """Handle database-related errors."""
        if isinstance(error, IntegrityError):
            # Extract constraint information
            constraint_info = str(error.orig) if hasattr(error, 'orig') else str(error)
            
            if "UNIQUE constraint" in constraint_info or "duplicate key" in constraint_info.lower():
                return StructuredError(
                    error_code=ErrorCode.DATABASE_CONSTRAINT_VIOLATION,
                    message="Duplicate entry detected",
                    user_message="This item already exists. Please check for duplicates.",
                    details={"constraint_violation": constraint_info},
                    context=context,
                    suggestions=[
                        "Check if the item already exists",
                        "Verify unique fields like serial number or barcode",
                        "Try using different values for unique fields"
                    ]
                )
            elif "FOREIGN KEY constraint" in constraint_info:
                return StructuredError(
                    error_code=ErrorCode.DATABASE_CONSTRAINT_VIOLATION,
                    message="Referenced item does not exist",
                    user_message="The referenced item or location does not exist.",
                    details={"constraint_violation": constraint_info},
                    context=context,
                    suggestions=[
                        "Verify that all referenced items exist",
                        "Check location and category IDs",
                        "Ensure items haven't been deleted"
                    ]
                )
            else:
                return StructuredError(
                    error_code=ErrorCode.DATABASE_INTEGRITY_ERROR,
                    message="Database integrity constraint violated",
                    details={"constraint_violation": constraint_info},
                    context=context
                )
        
        elif isinstance(error, OperationalError):
            return StructuredError(
                error_code=ErrorCode.DATABASE_CONNECTION_ERROR,
                message="Database connection failed",
                severity=ErrorSeverity.CRITICAL,
                details={"database_error": str(error)},
                context=context,
                suggestions=[
                    "Check database server status",
                    "Verify database connection settings",
                    "Try again in a few moments"
                ]
            )
        
        else:
            return StructuredError(
                error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=f"Database error: {str(error)}",
                details={"database_error": str(error)},
                context=context
            )
    
    @staticmethod
    def handle_validation_error(error: ValidationError, context: Dict[str, Any] = None) -> StructuredError:
        """Handle Pydantic validation errors."""
        error_details = []
        field_errors = {}
        
        for validation_error in error.errors():
            field_path = " -> ".join(str(loc) for loc in validation_error["loc"])
            error_message = validation_error["msg"]
            error_type = validation_error["type"]
            
            error_details.append({
                "field": field_path,
                "message": error_message,
                "type": error_type
            })
            
            field_errors[field_path] = error_message
        
        return StructuredError(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Input validation failed",
            user_message="Please check your input and correct any errors.",
            details={
                "validation_errors": error_details,
                "field_errors": field_errors
            },
            context=context,
            suggestions=[
                "Check all required fields are filled",
                "Verify data types and formats",
                "Review field constraints and limits"
            ]
        )
    
    @staticmethod
    def handle_business_rule_error(message: str, context: Dict[str, Any] = None,
                                 suggestions: List[str] = None) -> StructuredError:
        """Handle business rule violations."""
        return StructuredError(
            error_code=ErrorCode.BUSINESS_RULE_VIOLATION,
            message=message,
            context=context,
            suggestions=suggestions or [
                "Review business rules and constraints",
                "Check current system state",
                "Contact administrator if needed"
            ]
        )
    
    @staticmethod
    def handle_not_found_error(resource_type: str, resource_id: Union[int, str],
                             context: Dict[str, Any] = None) -> StructuredError:
        """Handle resource not found errors."""
        return StructuredError(
            error_code=ErrorCode.NOT_FOUND,
            message=f"{resource_type} with ID {resource_id} not found",
            user_message=f"The requested {resource_type.lower()} was not found.",
            details={
                "resource_type": resource_type,
                "resource_id": resource_id
            },
            context=context,
            suggestions=[
                f"Verify the {resource_type.lower()} ID is correct",
                f"Check if the {resource_type.lower()} was deleted",
                "Try searching for the resource"
            ]
        )
    
    @staticmethod
    def handle_generic_error(error: Exception, context: Dict[str, Any] = None) -> StructuredError:
        """Handle generic unexpected errors."""
        return StructuredError(
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            message=f"Unexpected error: {str(error)}",
            severity=ErrorSeverity.ERROR,
            details={
                "exception_type": type(error).__name__,
                "exception_message": str(error),
                "traceback": traceback.format_exc()
            },
            context=context,
            suggestions=[
                "Try the operation again",
                "Check if all required data is available",
                "Contact support if the problem persists"
            ]
        )


class ErrorMiddleware(BaseHTTPMiddleware):
    """Middleware for handling errors and adding correlation IDs."""
    
    async def dispatch(self, request: Request, call_next):
        """Process request with error handling and correlation ID tracking."""
        # Generate correlation ID if not present
        correlation_id = request.headers.get("x-correlation-id", str(uuid.uuid4())[:8])
        
        # Add correlation ID to request state
        request.state.correlation_id = correlation_id
        
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add correlation ID to response headers
            response.headers["x-correlation-id"] = correlation_id
            
            return response
            
        except Exception as error:
            # Calculate request duration
            duration = time.time() - start_time
            
            # Create request context
            context = {
                "method": request.method,
                "url": str(request.url),
                "correlation_id": correlation_id,
                "duration_ms": round(duration * 1000, 2),
                "user_agent": request.headers.get("user-agent"),
                "client_ip": request.client.host if request.client else None
            }
            
            # Handle different error types
            if isinstance(error, HTTPException):
                # Re-raise HTTP exceptions as-is
                raise error
            elif isinstance(error, (IntegrityError, OperationalError)):
                structured_error = ErrorHandler.handle_database_error(error, context)
            elif isinstance(error, ValidationError):
                structured_error = ErrorHandler.handle_validation_error(error, context)
            else:
                structured_error = ErrorHandler.handle_generic_error(error, context)
            
            # Set correlation ID
            structured_error.correlation_id = correlation_id
            
            # Record error for analytics
            error_analytics.record_error(structured_error, context)
            
            # Log error
            log_level = {
                ErrorSeverity.INFO: logging.INFO,
                ErrorSeverity.WARNING: logging.WARNING,
                ErrorSeverity.ERROR: logging.ERROR,
                ErrorSeverity.CRITICAL: logging.CRITICAL
            }.get(structured_error.severity, logging.ERROR)
            
            logger.log(
                log_level,
                f"Error {structured_error.correlation_id}: {structured_error.message}",
                extra={
                    "correlation_id": correlation_id,
                    "error_code": structured_error.error_code.value,
                    "context": context,
                    "details": structured_error.details
                }
            )
            
            # Return structured error response
            error_dict = structured_error.to_dict()
            status_code = 500
            
            # Map error codes to HTTP status codes
            status_code_mapping = {
                ErrorCode.VALIDATION_ERROR: 400,
                ErrorCode.NOT_FOUND: 404,
                ErrorCode.UNAUTHORIZED: 401,
                ErrorCode.FORBIDDEN: 403,
                ErrorCode.BUSINESS_RULE_VIOLATION: 422,
                ErrorCode.RESOURCE_CONFLICT: 409,
                ErrorCode.RATE_LIMIT_EXCEEDED: 429,
                ErrorCode.DATABASE_CONSTRAINT_VIOLATION: 422
            }
            
            status_code = status_code_mapping.get(structured_error.error_code, 500)
            
            return JSONResponse(
                status_code=status_code,
                content=error_dict,
                headers={"x-correlation-id": correlation_id}
            )


# Convenience functions for raising structured errors

def raise_not_found(resource_type: str, resource_id: Union[int, str],
                   context: Dict[str, Any] = None):
    """Raise a structured not found error."""
    structured_error = ErrorHandler.handle_not_found_error(resource_type, resource_id, context)
    raise structured_error.to_http_exception(404)


def raise_validation_error(message: str, field_errors: Dict[str, str] = None,
                         context: Dict[str, Any] = None):
    """Raise a structured validation error."""
    structured_error = StructuredError(
        error_code=ErrorCode.VALIDATION_ERROR,
        message=message,
        details={"field_errors": field_errors or {}},
        context=context
    )
    raise structured_error.to_http_exception(400)


def raise_business_rule_error(message: str, suggestions: List[str] = None,
                            context: Dict[str, Any] = None):
    """Raise a structured business rule error."""
    structured_error = ErrorHandler.handle_business_rule_error(message, context, suggestions)
    raise structured_error.to_http_exception(422)


def raise_conflict_error(message: str, context: Dict[str, Any] = None):
    """Raise a structured conflict error."""
    structured_error = StructuredError(
        error_code=ErrorCode.RESOURCE_CONFLICT,
        message=message,
        context=context
    )
    raise structured_error.to_http_exception(409)


# Error analytics endpoints helpers

def get_error_analytics_summary(hours: int = 24) -> Dict[str, Any]:
    """Get error analytics summary."""
    return error_analytics.get_error_summary(hours)


def get_error_statistics() -> Dict[str, Any]:
    """Get comprehensive error statistics."""
    return {
        "total_unique_errors": len(error_analytics.error_stats),
        "total_error_instances": len(error_analytics.error_history),
        "error_types": error_analytics.error_stats,
        "recent_summary": error_analytics.get_error_summary(24)
    }