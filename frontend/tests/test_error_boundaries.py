"""
Comprehensive test suite for error boundary components and error handling infrastructure.

Tests error boundaries, recovery mechanisms, error reporting, and user feedback
across all frontend components and error scenarios.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, call
from contextlib import contextmanager
import logging
import sys

# Mock problematic imports before importing components
sys.modules['streamlit'] = Mock()

# Now import components under test with mocked dependencies
with patch.dict('sys.modules', {
    'streamlit': Mock(),
    'utils.api_client': Mock(),
    'utils.notifications': Mock(),
    'utils.helpers': Mock()
}):
    from components.error_boundary import (
        PageErrorBoundary, ComponentErrorBoundary, FormErrorBoundary,
        DataLoadingErrorBoundary, NetworkErrorHandler, safe_component,
        error_boundary_decorator, with_page_error_boundary, 
        with_component_error_boundary, safe_data_loader
    )
    from utils.error_handling import (
        ErrorSeverity, ErrorCategory, ErrorContext, RetryStrategy,
        RetryManager, CircuitBreaker, ErrorReporter, GracefulDegradation,
        ErrorBoundary, safe_execute, error_handler
    )


class TestPageErrorBoundary:
    """Test page-level error boundary functionality."""
    
    @pytest.fixture
    def page_boundary(self):
        """Create PageErrorBoundary instance for testing."""
        return PageErrorBoundary("TestPage")
    
    @pytest.fixture
    def mock_streamlit(self):
        """Mock Streamlit functions."""
        with patch('streamlit.error') as mock_error, \
             patch('streamlit.warning') as mock_warning, \
             patch('streamlit.info') as mock_info, \
             patch('streamlit.success') as mock_success, \
             patch('streamlit.markdown') as mock_markdown, \
             patch('streamlit.subheader') as mock_subheader, \
             patch('streamlit.expander') as mock_expander, \
             patch('streamlit.code') as mock_code, \
             patch('streamlit.button') as mock_button, \
             patch('streamlit.columns') as mock_columns, \
             patch('streamlit.rerun') as mock_rerun, \
             patch('streamlit.switch_page') as mock_switch_page, \
             patch('streamlit.session_state', {}) as mock_session_state:
            
            mock_button.return_value = False
            mock_columns.return_value = [Mock(), Mock(), Mock()]
            
            yield {
                'error': mock_error,
                'warning': mock_warning,
                'info': mock_info,
                'success': mock_success,
                'markdown': mock_markdown,
                'subheader': mock_subheader,
                'expander': mock_expander,
                'code': mock_code,
                'button': mock_button,
                'columns': mock_columns,
                'rerun': mock_rerun,
                'switch_page': mock_switch_page,
                'session_state': mock_session_state
            }
    
    def test_page_boundary_context_manager_success(self, page_boundary, mock_streamlit):
        """Test page boundary context manager with successful execution."""
        with page_boundary:
            # Simulate successful page rendering
            result = "success"
        
        # Should not trigger error handling
        mock_streamlit['error'].assert_not_called()
        mock_streamlit['warning'].assert_not_called()
    
    def test_page_boundary_handles_value_error(self, page_boundary, mock_streamlit):
        """Test page boundary handling ValueError."""
        with page_boundary:
            raise ValueError("Test value error")
        
        # Should display error message
        mock_streamlit['error'].assert_called()
        error_call = mock_streamlit['error'].call_args[0][0]
        assert "Page Error" in error_call
        assert "TestPage" in error_call
    
    def test_page_boundary_handles_connection_error(self, page_boundary, mock_streamlit):
        """Test page boundary handling network errors."""
        with page_boundary:
            raise ConnectionError("Network connection failed")
        
        # Should display error and handle as high severity
        mock_streamlit['error'].assert_called()
    
    def test_page_boundary_with_fallback_content(self, mock_streamlit):
        """Test page boundary with fallback content."""
        fallback_called = Mock()
        page_boundary = PageErrorBoundary("TestPage", fallback_content=fallback_called)
        
        with page_boundary:
            raise ValueError("Test error")
        
        # Should call fallback content
        fallback_called.assert_called_once()
        mock_streamlit['markdown'].assert_any_call("---")
        mock_streamlit['subheader'].assert_any_call("🔧 Fallback Mode")
    
    def test_page_boundary_fallback_also_fails(self, mock_streamlit):
        """Test page boundary when fallback content also fails."""
        def failing_fallback():
            raise Exception("Fallback also failed")
        
        page_boundary = PageErrorBoundary("TestPage", fallback_content=failing_fallback)
        
        with page_boundary:
            raise ValueError("Primary error")
        
        # Should show minimal recovery options
        mock_streamlit['markdown'].assert_any_call("### 🛠️ Recovery Options")
    
    def test_page_boundary_max_errors_exceeded(self, mock_streamlit):
        """Test page boundary when max errors are exceeded."""
        page_boundary = PageErrorBoundary("TestPage", fallback_content=Mock())
        page_boundary.error_count = 10  # Exceed max_errors (5)
        
        with page_boundary:
            raise ValueError("Too many errors")
        
        # Should show minimal recovery instead of fallback
        mock_streamlit['markdown'].assert_any_call("### 🛠️ Recovery Options")
    
    def test_page_boundary_error_severity_determination(self, page_boundary):
        """Test error severity determination logic."""
        # Connection errors should be HIGH severity
        severity = page_boundary._determine_severity(ConnectionError)
        assert severity == ErrorSeverity.HIGH
        
        # Value errors should be MEDIUM severity
        severity = page_boundary._determine_severity(ValueError)
        assert severity == ErrorSeverity.MEDIUM
        
        # Generic errors should be HIGH severity (page-level)
        severity = page_boundary._determine_severity(Exception)
        assert severity == ErrorSeverity.HIGH
    
    def test_page_boundary_error_category_determination(self, page_boundary):
        """Test error category determination logic."""
        # Network errors
        category = page_boundary._determine_category(ConnectionError)
        assert category == ErrorCategory.NETWORK
        
        # Data errors
        category = page_boundary._determine_category(ValueError)
        assert category == ErrorCategory.DATA
        
        # Session errors
        category = page_boundary._determine_category(KeyError)
        assert category == ErrorCategory.SESSION
    
    @patch('components.error_boundary.ErrorReporter.report_error')
    def test_page_boundary_error_reporting(self, mock_report, page_boundary, mock_streamlit):
        """Test that errors are properly reported."""
        with page_boundary:
            raise ValueError("Test reporting error")
        
        # Should report error with proper context
        mock_report.assert_called_once()
        error_context = mock_report.call_args[0][0]
        assert error_context.context_data['page'] == 'TestPage'
        assert error_context.context_data['error_count'] == 1
    
    def test_page_boundary_recovery_button_interactions(self, page_boundary, mock_streamlit):
        """Test recovery button interactions."""
        mock_streamlit['button'].return_value = True  # Simulate button click
        
        with page_boundary:
            raise ValueError("Test recovery")
        
        # Should create recovery buttons
        button_calls = mock_streamlit['button'].call_args_list
        button_texts = [call[0][0] for call in button_calls]
        
        # Should have refresh, dashboard, and clear session buttons
        assert any("Refresh Page" in text for text in button_texts)
        assert any("Go to Dashboard" in text for text in button_texts)
        assert any("Clear Session" in text for text in button_texts)


class TestComponentErrorBoundary:
    """Test component-level error boundary functionality."""
    
    @pytest.fixture
    def component_boundary(self):
        """Create ComponentErrorBoundary instance for testing."""
        return ComponentErrorBoundary("TestComponent")
    
    @pytest.fixture
    def mock_streamlit(self):
        """Mock Streamlit functions."""
        with patch.multiple(
            'streamlit',
            warning=Mock(),
            info=Mock(),
            expander=Mock(),
            code=Mock(),
            button=Mock(return_value=False),
            columns=Mock(return_value=[Mock(), Mock()]),
            rerun=Mock(),
            markdown=Mock()
        ) as mocks:
            yield mocks
    
    def test_component_boundary_success(self, component_boundary, mock_streamlit):
        """Test component boundary with successful execution."""
        with component_boundary:
            result = "component success"
        
        # Should not trigger error handling
        mock_streamlit['warning'].assert_not_called()
    
    def test_component_boundary_handles_error(self, component_boundary, mock_streamlit):
        """Test component boundary handling errors."""
        with component_boundary:
            raise ValueError("Component error")
        
        # Should display warning message
        mock_streamlit['warning'].assert_called()
        warning_call = mock_streamlit['warning'].call_args[0][0]
        assert "Error in TestComponent component" in warning_call
    
    def test_component_boundary_with_fallback(self, mock_streamlit):
        """Test component boundary with fallback component."""
        fallback_component = Mock()
        component_boundary = ComponentErrorBoundary(
            "TestComponent", 
            fallback_component=fallback_component
        )
        
        with component_boundary:
            raise ValueError("Component error")
        
        # Should call fallback component
        fallback_component.assert_called_once()
        mock_streamlit['markdown'].assert_any_call("*Showing fallback content:*")
    
    def test_component_boundary_fallback_also_fails(self, mock_streamlit):
        """Test component boundary when fallback also fails."""
        def failing_fallback():
            raise Exception("Fallback failed")
        
        component_boundary = ComponentErrorBoundary(
            "TestComponent",
            fallback_component=failing_fallback
        )
        
        with component_boundary:
            raise ValueError("Primary error")
        
        # Should show fallback unavailable warning
        mock_streamlit['warning'].assert_any_call("⚠️ Fallback content is also unavailable")
    
    def test_component_boundary_with_details(self, mock_streamlit):
        """Test component boundary with details enabled."""
        component_boundary = ComponentErrorBoundary("TestComponent", show_details=True)
        
        with component_boundary:
            raise ValueError("Component error with details")
        
        # Should show technical details
        mock_streamlit['expander'].assert_called_with("Technical Details", expanded=False)
    
    @patch('components.error_boundary.ErrorReporter.report_error')
    def test_component_boundary_error_reporting(self, mock_report, component_boundary, mock_streamlit):
        """Test component error reporting."""
        with component_boundary:
            raise ValueError("Component reporting test")
        
        # Should report error
        mock_report.assert_called_once()
        error_context = mock_report.call_args[0][0]
        assert error_context.context_data['component'] == 'TestComponent'
    
    def test_component_boundary_retry_button(self, component_boundary, mock_streamlit):
        """Test component retry functionality."""
        mock_streamlit['button'].return_value = True  # Simulate retry click
        
        with component_boundary:
            raise ValueError("Component retry test")
        
        # Should create retry button and call rerun
        mock_streamlit['button'].assert_called()
        mock_streamlit['rerun'].assert_called()


class TestFormErrorBoundary:
    """Test form-specific error boundary functionality."""
    
    @pytest.fixture
    def form_boundary(self):
        """Create FormErrorBoundary instance for testing."""
        return FormErrorBoundary("TestForm")
    
    @pytest.fixture
    def mock_streamlit(self):
        """Mock Streamlit functions."""
        with patch.multiple(
            'streamlit',
            error=Mock(),
            markdown=Mock()
        ) as mocks:
            yield mocks
    
    def test_form_boundary_validation_errors(self, form_boundary, mock_streamlit):
        """Test form boundary validation error handling."""
        form_boundary.add_validation_error("email", "Invalid email format")
        form_boundary.add_validation_error("password", "Password too short")
        
        assert form_boundary.has_errors() is True
        
        form_boundary.display_errors()
        
        # Should display validation errors
        mock_streamlit['error'].assert_called_with("❌ **Please correct the following errors:**")
        mock_streamlit['markdown'].assert_any_call("• **email**: Invalid email format")
        mock_streamlit['markdown'].assert_any_call("• **password**: Password too short")
    
    def test_form_boundary_form_errors(self, form_boundary, mock_streamlit):
        """Test form boundary form-level error handling."""
        form_boundary.add_form_error("Server validation failed")
        form_boundary.add_form_error("Database connection lost")
        
        assert form_boundary.has_errors() is True
        
        form_boundary.display_errors()
        
        # Should display form errors
        mock_streamlit['error'].assert_any_call("❌ Server validation failed")
        mock_streamlit['error'].assert_any_call("❌ Database connection lost")
    
    def test_form_boundary_clear_errors(self, form_boundary):
        """Test clearing form errors."""
        form_boundary.add_validation_error("field", "error")
        form_boundary.add_form_error("form error")
        
        assert form_boundary.has_errors() is True
        
        form_boundary.clear_errors()
        
        assert form_boundary.has_errors() is False
        assert len(form_boundary.validation_errors) == 0
        assert len(form_boundary.form_errors) == 0
    
    def test_form_boundary_context_manager(self, form_boundary, mock_streamlit):
        """Test form boundary as context manager."""
        form_boundary.add_validation_error("test", "test error")
        
        with form_boundary:
            raise ValueError("Form processing error")
        
        # Should display form error and existing validation errors
        mock_streamlit['error'].assert_called()
        error_calls = mock_streamlit['error'].call_args_list
        assert any("Error processing TestForm form" in str(call) for call in error_calls)
    
    @patch('components.error_boundary.ErrorReporter.report_error')
    def test_form_boundary_error_context(self, mock_report, form_boundary, mock_streamlit):
        """Test form boundary error context creation."""
        form_boundary.add_validation_error("email", "Invalid")
        
        with form_boundary:
            raise ValueError("Form error")
        
        # Should report error with form context
        mock_report.assert_called_once()
        error_context = mock_report.call_args[0][0]
        assert error_context.category == ErrorCategory.USER_INPUT
        assert error_context.context_data['form'] == 'TestForm'
        assert 'validation_errors' in error_context.context_data


class TestDataLoadingErrorBoundary:
    """Test data loading error boundary functionality."""
    
    @pytest.fixture
    def data_boundary(self):
        """Create DataLoadingErrorBoundary instance for testing."""
        return DataLoadingErrorBoundary("API Endpoint")
    
    @pytest.fixture
    def mock_streamlit(self):
        """Mock Streamlit functions."""
        with patch.multiple(
            'streamlit',
            error=Mock(),
            info=Mock(),
            success=Mock(),
            columns=Mock(return_value=[Mock(), Mock(), Mock()]),
            button=Mock(return_value=False),
            expander=Mock(),
            code=Mock(),
            rerun=Mock(),
            switch_page=Mock()
        ) as mocks:
            yield mocks
    
    def test_data_boundary_success(self, data_boundary, mock_streamlit):
        """Test data boundary with successful data loading."""
        with data_boundary:
            data = {"items": [1, 2, 3]}
        
        # Should not trigger error handling
        mock_streamlit['error'].assert_not_called()
    
    def test_data_boundary_connection_error(self, data_boundary, mock_streamlit):
        """Test data boundary with connection error."""
        with data_boundary:
            raise ConnectionError("API connection failed")
        
        # Should display data loading error
        mock_streamlit['error'].assert_called()
        error_call = mock_streamlit['error'].call_args[0][0]
        assert "Unable to load data from API Endpoint" in error_call
    
    def test_data_boundary_recovery_options(self, data_boundary, mock_streamlit):
        """Test data boundary recovery options."""
        with data_boundary:
            raise ConnectionError("API failure")
        
        # Should create recovery buttons
        mock_streamlit['button'].assert_called()
        button_calls = mock_streamlit['button'].call_args_list
        button_texts = [call[0][0] for call in button_calls]
        
        assert any("Retry" in text for text in button_texts)
        assert any("Use Cached Data" in text for text in button_texts)
        assert any("Go Back" in text for text in button_texts)
    
    def test_data_boundary_no_retry_button(self, mock_streamlit):
        """Test data boundary without retry button."""
        data_boundary = DataLoadingErrorBoundary("API", retry_button=False)
        
        with data_boundary:
            raise ValueError("Data error")
        
        # Should not create retry button
        button_calls = mock_streamlit['button'].call_args_list
        button_texts = [call[0][0] for call in button_calls if call]
        retry_buttons = [text for text in button_texts if "Retry" in text]
        assert len(retry_buttons) == 0
    
    def test_data_boundary_no_cache_fallback(self, mock_streamlit):
        """Test data boundary without cache fallback."""
        data_boundary = DataLoadingErrorBoundary("API", cache_fallback=False)
        
        with data_boundary:
            raise ValueError("Data error")
        
        # Should not create cache button
        button_calls = mock_streamlit['button'].call_args_list
        button_texts = [call[0][0] for call in button_calls if call]
        cache_buttons = [text for text in button_texts if "Cached Data" in text]
        assert len(cache_buttons) == 0
    
    @patch('components.error_boundary.ErrorReporter.report_error')
    def test_data_boundary_error_reporting(self, mock_report, data_boundary, mock_streamlit):
        """Test data boundary error reporting."""
        with data_boundary:
            raise ConnectionError("Data loading failed")
        
        # Should report error with data source context
        mock_report.assert_called_once()
        error_context = mock_report.call_args[0][0]
        assert error_context.context_data['data_source'] == 'API Endpoint'
        assert error_context.category == ErrorCategory.NETWORK


class TestNetworkErrorHandler:
    """Test network error handling functionality."""
    
    @pytest.fixture
    def mock_streamlit(self):
        """Mock Streamlit functions."""
        with patch.multiple(
            'streamlit',
            warning=Mock(),
            error=Mock(),
            info=Mock(),
            button=Mock(return_value=False),
            expander=Mock(),
            json=Mock(),
            rerun=Mock()
        ) as mocks:
            yield mocks
    
    def test_handle_404_error(self, mock_streamlit):
        """Test handling 404 API errors."""
        from utils.api_client import APIError
        
        api_error = APIError("Not found", 404, {"detail": "Resource not found"})
        result = NetworkErrorHandler.handle_api_error(api_error)
        
        assert result is True  # Error was handled
        mock_streamlit['warning'].assert_called()
        warning_call = mock_streamlit['warning'].call_args[0][0]
        assert "not found" in warning_call.lower()
    
    def test_handle_403_error(self, mock_streamlit):
        """Test handling 403 permission errors."""
        from utils.api_client import APIError
        
        api_error = APIError("Forbidden", 403, {"detail": "Access denied"})
        result = NetworkErrorHandler.handle_api_error(api_error)
        
        assert result is True
        mock_streamlit['error'].assert_called()
        error_call = mock_streamlit['error'].call_args[0][0]
        assert "Access denied" in error_call
    
    def test_handle_500_error(self, mock_streamlit):
        """Test handling 500 server errors."""
        from utils.api_client import APIError
        
        api_error = APIError("Internal Server Error", 500, {"detail": "Server error"})
        result = NetworkErrorHandler.handle_api_error(api_error)
        
        assert result is True
        mock_streamlit['error'].assert_called()
        mock_streamlit['button'].assert_called()  # Retry button
    
    def test_handle_503_error(self, mock_streamlit):
        """Test handling 503 service unavailable errors."""
        from utils.api_client import APIError
        
        api_error = APIError("Service Unavailable", 503, {"detail": "Maintenance"})
        result = NetworkErrorHandler.handle_api_error(api_error)
        
        assert result is True
        mock_streamlit['error'].assert_called()
        mock_streamlit['info'].assert_called()  # Maintenance message
    
    def test_handle_non_api_error(self, mock_streamlit):
        """Test handling non-API errors."""
        regular_error = ValueError("Not an API error")
        result = NetworkErrorHandler.handle_api_error(regular_error)
        
        assert result is False  # Error was not handled
        mock_streamlit['warning'].assert_not_called()
        mock_streamlit['error'].assert_not_called()
    
    def test_api_error_technical_details(self, mock_streamlit):
        """Test API error technical details display."""
        from utils.api_client import APIError
        
        api_error = APIError("Bad Request", 400, {"validation_errors": ["Invalid field"]})
        NetworkErrorHandler.handle_api_error(api_error, "Create Item")
        
        # Should show technical details
        mock_streamlit['expander'].assert_called_with("Technical Details", expanded=False)
        mock_streamlit['json'].assert_called()


class TestSafeComponentDecorator:
    """Test safe component context manager and decorator."""
    
    @pytest.fixture
    def mock_streamlit(self):
        """Mock Streamlit functions."""
        with patch.multiple(
            'streamlit',
            error=Mock(),
            info=Mock(),
            button=Mock(return_value=False),
            rerun=Mock()
        ) as mocks:
            yield mocks
    
    def test_safe_component_success(self, mock_streamlit):
        """Test safe component with successful execution."""
        with safe_component("TestComponent"):
            result = "success"
        
        # Should not trigger error handling
        mock_streamlit['error'].assert_not_called()
    
    def test_safe_component_with_error(self, mock_streamlit):
        """Test safe component with error."""
        with safe_component("TestComponent"):
            raise ValueError("Component failed")
        
        # Should display error
        mock_streamlit['error'].assert_called()
        error_call = mock_streamlit['error'].call_args[0][0]
        assert "Error loading TestComponent" in error_call
    
    def test_safe_component_with_fallback(self, mock_streamlit):
        """Test safe component with fallback content."""
        with safe_component("TestComponent", fallback_content="Fallback message"):
            raise ValueError("Component failed")
        
        # Should show fallback content
        mock_streamlit['info'].assert_called_with("Fallback message")
    
    def test_safe_component_retry_button(self, mock_streamlit):
        """Test safe component retry functionality."""
        mock_streamlit['button'].return_value = True  # Simulate retry
        
        with safe_component("TestComponent"):
            raise ValueError("Component failed")
        
        # Should create retry button and call rerun
        mock_streamlit['button'].assert_called()
        mock_streamlit['rerun'].assert_called()
    
    @patch('logging.getLogger')
    def test_safe_component_logging(self, mock_logger, mock_streamlit):
        """Test safe component error logging."""
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        with safe_component("TestComponent"):
            raise ValueError("Test logging")
        
        # Should log error
        mock_logger_instance.error.assert_called()


class TestErrorBoundaryDecorator:
    """Test error boundary decorator functionality."""
    
    @pytest.fixture
    def mock_streamlit(self):
        """Mock Streamlit functions."""
        with patch.multiple(
            'streamlit',
            error=Mock(),
            info=Mock(),
            warning=Mock(),
            expander=Mock(),
            code=Mock(),
            button=Mock(return_value=False),
            rerun=Mock()
        ) as mocks:
            yield mocks
    
    def test_decorator_success(self, mock_streamlit):
        """Test error boundary decorator with successful function."""
        @error_boundary_decorator("TestComponent")
        def successful_function():
            return "success"
        
        result = successful_function()
        assert result == "success"
        
        # Should not trigger error handling
        mock_streamlit['error'].assert_not_called()
    
    def test_decorator_with_error(self, mock_streamlit):
        """Test error boundary decorator with error."""
        @error_boundary_decorator("TestComponent")
        def failing_function():
            raise ValueError("Function failed")
        
        result = failing_function()
        assert result is None  # Should return None on error
        
        # Should display error
        mock_streamlit['error'].assert_called()
    
    def test_decorator_with_fallback(self, mock_streamlit):
        """Test error boundary decorator with fallback function."""
        def fallback_function():
            return "fallback result"
        
        @error_boundary_decorator("TestComponent", fallback_func=fallback_function)
        def failing_function():
            raise ValueError("Function failed")
        
        result = failing_function()
        assert result == "fallback result"
        
        # Should show fallback info
        mock_streamlit['info'].assert_called()
    
    def test_decorator_fallback_also_fails(self, mock_streamlit):
        """Test decorator when fallback function also fails."""
        def failing_fallback():
            raise Exception("Fallback failed")
        
        @error_boundary_decorator("TestComponent", fallback_func=failing_fallback)
        def failing_function():
            raise ValueError("Function failed")
        
        result = failing_function()
        assert result is None
        
        # Should show fallback unavailable warning
        mock_streamlit['warning'].assert_called()
    
    def test_decorator_with_details(self, mock_streamlit):
        """Test decorator with error details enabled."""
        @error_boundary_decorator("TestComponent", show_details=True)
        def failing_function():
            raise ValueError("Function failed")
        
        result = failing_function()
        
        # Should show technical details
        mock_streamlit['expander'].assert_called_with("Error Details", expanded=False)
    
    @patch('components.error_boundary.ErrorReporter.report_error')
    def test_decorator_error_reporting(self, mock_report, mock_streamlit):
        """Test decorator error reporting."""
        @error_boundary_decorator("TestComponent")
        def failing_function():
            raise ValueError("Function failed")
        
        failing_function()
        
        # Should report error
        mock_report.assert_called_once()
        error_context = mock_report.call_args[0][0]
        assert error_context.context_data['component'] == 'TestComponent'
        assert error_context.context_data['function'] == 'failing_function'


class TestErrorBoundaryDecorators:
    """Test convenience decorator functions."""
    
    @pytest.fixture
    def mock_streamlit(self):
        """Mock Streamlit functions."""
        with patch.multiple(
            'streamlit',
            error=Mock(),
            warning=Mock(),
            info=Mock(),
            markdown=Mock(),
            subheader=Mock(),
            expander=Mock(),
            code=Mock(),
            button=Mock(return_value=False),
            columns=Mock(return_value=[Mock(), Mock(), Mock()]),
            rerun=Mock(),
            switch_page=Mock()
        ) as mocks:
            yield mocks
    
    def test_with_page_error_boundary_decorator(self, mock_streamlit):
        """Test with_page_error_boundary decorator."""
        @with_page_error_boundary("TestPage")
        def page_function():
            raise ValueError("Page error")
        
        page_function()
        
        # Should handle as page error
        mock_streamlit['error'].assert_called()
    
    def test_with_component_error_boundary_decorator(self, mock_streamlit):
        """Test with_component_error_boundary decorator."""
        @with_component_error_boundary("TestComponent")
        def component_function():
            raise ValueError("Component error")
        
        component_function()
        
        # Should handle as component error
        mock_streamlit['warning'].assert_called()
    
    def test_page_decorator_with_fallback(self, mock_streamlit):
        """Test page decorator with fallback content."""
        def fallback_content():
            mock_streamlit['info']("Fallback content")
        
        @with_page_error_boundary("TestPage", fallback_content=fallback_content)
        def page_function():
            raise ValueError("Page error")
        
        page_function()
        
        # Should show fallback content
        mock_streamlit['subheader'].assert_any_call("🔧 Fallback Mode")
    
    def test_component_decorator_with_fallback(self, mock_streamlit):
        """Test component decorator with fallback."""
        def fallback_component():
            mock_streamlit['info']("Fallback component")
        
        @with_component_error_boundary("TestComponent", fallback_component=fallback_component)
        def component_function():
            raise ValueError("Component error")
        
        component_function()
        
        # Should show fallback content
        mock_streamlit['markdown'].assert_any_call("*Showing fallback content:*")


class TestSafeDataLoader:
    """Test safe data loader decorator."""
    
    @pytest.fixture
    def mock_streamlit(self):
        """Mock Streamlit functions."""
        with patch.multiple(
            'streamlit',
            session_state={},
            error=Mock(),
            info=Mock(),
            warning=Mock(),
            success=Mock(),
            columns=Mock(return_value=[Mock(), Mock(), Mock()]),
            button=Mock(return_value=False),
            expander=Mock(),
            code=Mock(),
            rerun=Mock(),
            switch_page=Mock()
        ) as mocks:
            yield mocks
    
    @patch('time.time', return_value=1234567890)
    def test_safe_data_loader_success(self, mock_time, mock_streamlit):
        """Test safe data loader with successful data loading."""
        @safe_data_loader("API", cache_key="test_data")
        def load_data():
            return {"items": [1, 2, 3]}
        
        result = load_data()
        
        assert result == {"items": [1, 2, 3]}
        # Should cache the data
        assert mock_streamlit['session_state']['cached_test_data'] == {"items": [1, 2, 3]}
        assert mock_streamlit['session_state']['cached_test_data_timestamp'] == 1234567890
    
    def test_safe_data_loader_with_error(self, mock_streamlit):
        """Test safe data loader with error."""
        @safe_data_loader("API")
        def failing_load():
            raise ConnectionError("API failed")
        
        result = failing_load()
        
        # Should handle error with DataLoadingErrorBoundary
        mock_streamlit['error'].assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])