"""
Test suite for the enhanced error handling system.

Tests structured errors, correlation IDs, error analytics, and middleware functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, OperationalError
from pydantic import ValidationError

from app.core.error_handler import (
    ErrorCode,
    ErrorSeverity,
    StructuredError,
    ErrorHandler,
    ErrorAnalytics,
    ErrorMiddleware,
    error_analytics,
    raise_not_found,
    raise_validation_error,
    raise_business_rule_error,
    raise_conflict_error,
    get_error_analytics_summary,
    get_error_statistics
)


class TestStructuredError:
    """Test the StructuredError class functionality."""
    
    def test_structured_error_creation(self):
        """Test basic structured error creation."""
        error = Exception("Test error")
        structured_error = StructuredError(
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            message="Test message",
            severity=ErrorSeverity.ERROR,
            details={"key": "value"},
            context={"request_id": "123"}
        )
        
        assert structured_error.error_code == ErrorCode.INTERNAL_SERVER_ERROR
        assert structured_error.message == "Test message"
        assert structured_error.severity == ErrorSeverity.ERROR
        assert structured_error.details["key"] == "value"
        assert structured_error.context["request_id"] == "123"
        assert structured_error.correlation_id is not None
        assert isinstance(structured_error.timestamp, datetime)
    
    def test_user_message_generation(self):
        """Test automatic user message generation."""
        test_cases = [
            (ErrorCode.NOT_FOUND, "The requested resource was not found."),
            (ErrorCode.VALIDATION_ERROR, "Please check your input and try again."),
            (ErrorCode.UNAUTHORIZED, "Authentication is required to access this resource."),
            (ErrorCode.DATABASE_CONNECTION_ERROR, "Unable to connect to the database. Please try again later."),
            (ErrorCode.BUSINESS_RULE_VIOLATION, "This operation violates business rules."),
        ]
        
        for error_code, expected_message in test_cases:
            structured_error = StructuredError(
                error_code=error_code,
                message="Technical message"
            )
            assert structured_error.user_message == expected_message
    
    def test_to_dict_conversion(self):
        """Test conversion to dictionary format."""
        structured_error = StructuredError(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Test validation error",
            details={"field": "test_field"},
            suggestions=["Check field format", "Verify required fields"]
        )
        
        error_dict = structured_error.to_dict()
        
        assert "error" in error_dict
        error_data = error_dict["error"]
        assert error_data["code"] == ErrorCode.VALIDATION_ERROR.value
        assert error_data["message"] == "Test validation error"
        assert error_data["severity"] == ErrorSeverity.ERROR.value
        assert error_data["details"]["field"] == "test_field"
        assert "Check field format" in error_data["suggestions"]
        assert "correlation_id" in error_data
        assert "timestamp" in error_data
    
    def test_to_http_exception(self):
        """Test conversion to HTTPException."""
        structured_error = StructuredError(
            error_code=ErrorCode.NOT_FOUND,
            message="Resource not found"
        )
        
        http_exception = structured_error.to_http_exception(404)
        
        assert isinstance(http_exception, HTTPException)
        assert http_exception.status_code == 404
        assert http_exception.detail["code"] == ErrorCode.NOT_FOUND.value
        assert http_exception.detail["message"] == "Resource not found"


class TestErrorHandler:
    """Test the ErrorHandler static methods."""
    
    def test_handle_database_integrity_error(self):
        """Test handling of database integrity errors."""
        # Test unique constraint violation
        integrity_error = IntegrityError(
            "UNIQUE constraint failed",
            None,
            Mock(args=["UNIQUE constraint failed: items.serial_number"])
        )
        integrity_error.orig = Mock()
        integrity_error.orig.__str__ = lambda: "UNIQUE constraint failed: items.serial_number"
        
        structured_error = ErrorHandler.handle_database_error(integrity_error)
        
        assert structured_error.error_code == ErrorCode.DATABASE_CONSTRAINT_VIOLATION
        assert "Duplicate entry detected" in structured_error.message
        assert "This item already exists" in structured_error.user_message
        assert "Check if the item already exists" in structured_error.suggestions
    
    def test_handle_database_foreign_key_error(self):
        """Test handling of foreign key constraint violations."""
        integrity_error = IntegrityError(
            "FOREIGN KEY constraint failed",
            None,
            Mock(args=["FOREIGN KEY constraint failed"])
        )
        integrity_error.orig = Mock()
        integrity_error.orig.__str__ = lambda: "FOREIGN KEY constraint failed"
        
        structured_error = ErrorHandler.handle_database_error(integrity_error)
        
        assert structured_error.error_code == ErrorCode.DATABASE_CONSTRAINT_VIOLATION
        assert "Referenced item does not exist" in structured_error.message
        assert "referenced item or location does not exist" in structured_error.user_message
        assert "Verify that all referenced items exist" in structured_error.suggestions
    
    def test_handle_database_operational_error(self):
        """Test handling of database operational errors."""
        operational_error = OperationalError(
            "Connection failed",
            None,
            None
        )
        
        structured_error = ErrorHandler.handle_database_error(operational_error)
        
        assert structured_error.error_code == ErrorCode.DATABASE_CONNECTION_ERROR
        assert structured_error.severity == ErrorSeverity.CRITICAL
        assert "Database connection failed" in structured_error.message
        assert "Check database server status" in structured_error.suggestions
    
    def test_handle_validation_error(self):
        """Test handling of Pydantic validation errors."""
        # Create a mock ValidationError
        validation_error = ValidationError.from_exception_data(
            "ValidationError",
            [
                {
                    "type": "missing",
                    "loc": ("name",),
                    "msg": "Field required",
                    "input": {}
                },
                {
                    "type": "string_too_short",
                    "loc": ("description",),
                    "msg": "String should have at least 1 character",
                    "input": ""
                }
            ]
        )
        
        structured_error = ErrorHandler.handle_validation_error(validation_error)
        
        assert structured_error.error_code == ErrorCode.VALIDATION_ERROR
        assert "Input validation failed" in structured_error.message
        assert len(structured_error.details["validation_errors"]) == 2
        assert "name" in structured_error.details["field_errors"]
        assert "description" in structured_error.details["field_errors"]
        assert "Check all required fields are filled" in structured_error.suggestions
    
    def test_handle_business_rule_error(self):
        """Test handling of business rule violations."""
        structured_error = ErrorHandler.handle_business_rule_error(
            "Cannot move item to full location",
            context={"location_id": 123, "current_capacity": 100},
            suggestions=["Choose a different location", "Clear space in target location"]
        )
        
        assert structured_error.error_code == ErrorCode.BUSINESS_RULE_VIOLATION
        assert "Cannot move item to full location" in structured_error.message
        assert structured_error.context["location_id"] == 123
        assert "Choose a different location" in structured_error.suggestions
    
    def test_handle_not_found_error(self):
        """Test handling of resource not found errors."""
        structured_error = ErrorHandler.handle_not_found_error("Item", 42)
        
        assert structured_error.error_code == ErrorCode.NOT_FOUND
        assert "Item with ID 42 not found" in structured_error.message
        assert "requested item was not found" in structured_error.user_message
        assert structured_error.details["resource_type"] == "Item"
        assert structured_error.details["resource_id"] == 42
        assert "Verify the item ID is correct" in structured_error.suggestions
    
    def test_handle_generic_error(self):
        """Test handling of generic unexpected errors."""
        generic_error = RuntimeError("Unexpected runtime error")
        
        structured_error = ErrorHandler.handle_generic_error(generic_error)
        
        assert structured_error.error_code == ErrorCode.INTERNAL_SERVER_ERROR
        assert structured_error.severity == ErrorSeverity.ERROR
        assert "Unexpected error: Unexpected runtime error" in structured_error.message
        assert structured_error.details["exception_type"] == "RuntimeError"
        assert "Try the operation again" in structured_error.suggestions


class TestErrorAnalytics:
    """Test the ErrorAnalytics class functionality."""
    
    def setup_method(self):
        """Set up fresh error analytics for each test."""
        self.analytics = ErrorAnalytics()
    
    def test_record_error(self):
        """Test error recording functionality."""
        structured_error = StructuredError(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Test validation error",
            severity=ErrorSeverity.MEDIUM
        )
        
        context = {"endpoint": "test_endpoint", "user_id": "test_user"}
        self.analytics.record_error(structured_error, context)
        
        assert len(self.analytics.error_history) == 1
        assert ErrorCode.VALIDATION_ERROR.value in self.analytics.error_stats
        
        stats = self.analytics.error_stats[ErrorCode.VALIDATION_ERROR.value]
        assert stats["count"] == 1
        assert stats["severity_distribution"][ErrorSeverity.MEDIUM.value] == 1
    
    def test_error_history_limit(self):
        """Test that error history respects maximum size limit."""
        # Set a small limit for testing
        self.analytics.max_history = 5
        
        # Record more errors than the limit
        for i in range(10):
            error = StructuredError(
                error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=f"Error {i}"
            )
            self.analytics.record_error(error)
        
        # Should only keep the last 5 errors
        assert len(self.analytics.error_history) == 5
        assert self.analytics.error_history[-1]["message"] == "Error 9"
    
    def test_get_error_summary(self):
        """Test error summary generation."""
        # Record some test errors
        current_time = datetime.utcnow()
        
        # Recent error (within last hour)
        recent_error = StructuredError(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Recent error"
        )
        recent_error.timestamp = current_time - timedelta(minutes=30)
        self.analytics.record_error(recent_error)
        
        # Old error (more than 24 hours ago)
        old_error = StructuredError(
            error_code=ErrorCode.NOT_FOUND,
            message="Old error"
        )
        old_error.timestamp = current_time - timedelta(hours=25)
        self.analytics.record_error(old_error)
        
        summary = self.analytics.get_error_summary(hours=24)
        
        assert summary["time_period_hours"] == 24
        assert summary["total_errors"] == 1  # Only recent error should be included
        assert ErrorCode.VALIDATION_ERROR.value in dict(summary["most_common_errors"])
        assert summary["severity_distribution"][ErrorSeverity.ERROR.value] == 1


class TestErrorMiddleware:
    """Test the ErrorMiddleware functionality."""
    
    @pytest.fixture
    def mock_request(self):
        """Create a mock FastAPI request."""
        request = Mock()
        request.method = "POST"
        request.url = Mock()
        request.url.__str__ = lambda: "http://localhost/api/v1/test"
        request.headers = {"user-agent": "test-agent"}
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.state = Mock()
        return request
    
    @pytest.fixture
    def middleware(self):
        """Create ErrorMiddleware instance."""
        return ErrorMiddleware(Mock())
    
    @pytest.mark.asyncio
    async def test_middleware_success_case(self, middleware, mock_request):
        """Test middleware behavior with successful request."""
        async def call_next(request):
            response = Mock()
            response.headers = {}
            return response
        
        response = await middleware.dispatch(mock_request, call_next)
        
        # Should add correlation ID to response
        assert "x-correlation-id" in response.headers
        assert hasattr(mock_request.state, "correlation_id")
    
    @pytest.mark.asyncio
    async def test_middleware_error_handling(self, middleware, mock_request):
        """Test middleware error handling."""
        async def call_next(request):
            raise ValueError("Test error")
        
        # Mock the error analytics to avoid side effects
        with patch('app.core.error_handler.error_analytics') as mock_analytics:
            try:
                await middleware.dispatch(mock_request, call_next)
                assert False, "Should have raised an exception"
            except Exception:
                # Should have recorded the error
                mock_analytics.record_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_middleware_http_exception_passthrough(self, middleware, mock_request):
        """Test that HTTP exceptions are passed through unchanged."""
        http_exception = HTTPException(status_code=404, detail="Not found")
        
        async def call_next(request):
            raise http_exception
        
        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(mock_request, call_next)
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Not found"


class TestConvenienceFunctions:
    """Test the convenience functions for raising structured errors."""
    
    def test_raise_not_found(self):
        """Test raise_not_found convenience function."""
        with pytest.raises(HTTPException) as exc_info:
            raise_not_found("Item", 42)
        
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["code"] == ErrorCode.NOT_FOUND.value
        assert "Item with ID 42 not found" in exc_info.value.detail["message"]
    
    def test_raise_validation_error(self):
        """Test raise_validation_error convenience function."""
        field_errors = {"name": "Name is required", "email": "Invalid email format"}
        
        with pytest.raises(HTTPException) as exc_info:
            raise_validation_error("Validation failed", field_errors)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == ErrorCode.VALIDATION_ERROR.value
        assert exc_info.value.detail["details"]["field_errors"] == field_errors
    
    def test_raise_business_rule_error(self):
        """Test raise_business_rule_error convenience function."""
        suggestions = ["Check business rules", "Contact administrator"]
        
        with pytest.raises(HTTPException) as exc_info:
            raise_business_rule_error("Business rule violated", suggestions)
        
        assert exc_info.value.status_code == 422
        assert exc_info.value.detail["code"] == ErrorCode.BUSINESS_RULE_VIOLATION.value
        assert exc_info.value.detail["suggestions"] == suggestions
    
    def test_raise_conflict_error(self):
        """Test raise_conflict_error convenience function."""
        with pytest.raises(HTTPException) as exc_info:
            raise_conflict_error("Resource conflict")
        
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail["code"] == ErrorCode.RESOURCE_CONFLICT.value


class TestGlobalAnalyticsFunctions:
    """Test the global error analytics functions."""
    
    def setup_method(self):
        """Clear global error analytics before each test."""
        error_analytics.error_history.clear()
        error_analytics.error_stats.clear()
    
    def test_get_error_analytics_summary(self):
        """Test global error analytics summary."""
        # Record a test error
        structured_error = StructuredError(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Test error"
        )
        error_analytics.record_error(structured_error)
        
        summary = get_error_analytics_summary(hours=24)
        
        assert summary["total_errors"] == 1
        assert summary["time_period_hours"] == 24
        assert len(summary["most_common_errors"]) > 0
    
    def test_get_error_statistics(self):
        """Test global error statistics."""
        # Record multiple test errors
        for i in range(3):
            error = StructuredError(
                error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=f"Test error {i}"
            )
            error_analytics.record_error(error)
        
        stats = get_error_statistics()
        
        assert stats["total_unique_errors"] == 1  # Same error code
        assert stats["total_error_instances"] == 3  # Three instances
        assert ErrorCode.INTERNAL_SERVER_ERROR.value in stats["error_types"]
        assert "recent_summary" in stats


if __name__ == "__main__":
    pytest.main([__file__])