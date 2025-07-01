"""
Test suite for error handling infrastructure components.

Tests error context, retry mechanisms, circuit breakers, error reporting,
graceful degradation, and core error handling utilities.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import logging
import hashlib

# Import components under test
from utils.error_handling import (
    ErrorSeverity, ErrorCategory, ErrorContext, RetryStrategy,
    RetryManager, CircuitBreaker, ErrorReporter, GracefulDegradation,
    ErrorBoundary, safe_execute, error_handler
)


class TestErrorContext:
    """Test ErrorContext class functionality."""
    
    def test_error_context_creation(self):
        """Test basic error context creation."""
        error = ValueError("Test error")
        context = ErrorContext(
            error=error,
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.DATA,
            user_message="User-friendly message",
            technical_message="Technical details"
        )
        
        assert context.error == error
        assert context.severity == ErrorSeverity.HIGH
        assert context.category == ErrorCategory.DATA
        assert context.user_message == "User-friendly message"
        assert context.technical_message == "Technical details"
        assert context.recoverable is True  # Default
        assert context.retry_strategy == RetryStrategy.EXPONENTIAL  # Default
        assert context.max_retries == 3  # Default
        assert isinstance(context.timestamp, datetime)
        assert len(context.error_id) == 8  # MD5 hash truncated
        assert context.stack_trace is not None
    
    def test_error_context_defaults(self):
        """Test error context with default values."""
        error = ConnectionError("Network error")
        context = ErrorContext(error=error)
        
        assert context.severity == ErrorSeverity.MEDIUM  # Default
        assert context.category == ErrorCategory.SYSTEM  # Default
        assert context.user_message is not None  # Auto-generated
        assert context.technical_message == str(error)
        assert context.context_data == {}  # Default empty dict
    
    def test_error_context_user_message_generation(self):
        """Test automatic user message generation based on category."""
        # Network error
        context = ErrorContext(
            error=ConnectionError("Network failed"),
            category=ErrorCategory.NETWORK
        )
        assert "connect to the server" in context.user_message.lower()
        
        # Data error
        context = ErrorContext(
            error=ValueError("Invalid data"),
            category=ErrorCategory.DATA
        )
        assert "processing your data" in context.user_message.lower()
        
        # Auth error
        context = ErrorContext(
            error=Exception("Auth failed"),
            category=ErrorCategory.AUTH
        )
        assert "authentication failed" in context.user_message.lower()
        
        # Session error
        context = ErrorContext(
            error=KeyError("Session key missing"),
            category=ErrorCategory.SESSION
        )
        assert "session has expired" in context.user_message.lower()
        
        # UI error
        context = ErrorContext(
            error=Exception("UI error"),
            category=ErrorCategory.UI
        )
        assert "display error" in context.user_message.lower()
        
        # User input error
        context = ErrorContext(
            error=ValueError("Invalid input"),
            category=ErrorCategory.USER_INPUT
        )
        assert "check your input" in context.user_message.lower()
        
        # Generic system error
        context = ErrorContext(
            error=Exception("System error"),
            category=ErrorCategory.SYSTEM
        )
        assert "unexpected error" in context.user_message.lower()
    
    def test_error_context_id_generation(self):
        """Test error ID generation for uniqueness and consistency."""
        error = ValueError("Test error")
        context1 = ErrorContext(error=error)
        time.sleep(0.001)  # Small delay to ensure different timestamp
        context2 = ErrorContext(error=error)
        
        # Should generate different IDs due to timestamp difference
        assert context1.error_id != context2.error_id
        
        # Same error at same time should generate same ID
        timestamp = datetime.now()
        with patch('utils.error_handling.datetime') as mock_datetime:
            mock_datetime.now.return_value = timestamp
            context3 = ErrorContext(error=error, category=ErrorCategory.DATA)
            context4 = ErrorContext(error=error, category=ErrorCategory.DATA)
            
            # Different categories should generate different IDs
            assert context3.error_id != context4.error_id
    
    def test_error_context_with_additional_data(self):
        """Test error context with additional context data."""
        context_data = {
            'user_id': 'test_user',
            'page': 'dashboard',
            'operation': 'load_data'
        }
        
        context = ErrorContext(
            error=Exception("Test"),
            context_data=context_data
        )
        
        assert context.context_data == context_data
        assert context.context_data['user_id'] == 'test_user'


class TestRetryManager:
    """Test RetryManager functionality."""
    
    def test_retry_delay_calculation_none(self):
        """Test no delay strategy."""
        delay = RetryManager.calculate_delay(1, RetryStrategy.NONE)
        assert delay == 0
        
        delay = RetryManager.calculate_delay(5, RetryStrategy.NONE)
        assert delay == 0
    
    def test_retry_delay_calculation_immediate(self):
        """Test immediate retry strategy."""
        delay = RetryManager.calculate_delay(1, RetryStrategy.IMMEDIATE)
        assert delay == 0
        
        delay = RetryManager.calculate_delay(3, RetryStrategy.IMMEDIATE)
        assert delay == 0
    
    def test_retry_delay_calculation_linear(self):
        """Test linear retry strategy."""
        delay = RetryManager.calculate_delay(1, RetryStrategy.LINEAR, base_delay=2.0)
        assert delay == 2.0
        
        delay = RetryManager.calculate_delay(3, RetryStrategy.LINEAR, base_delay=2.0)
        assert delay == 6.0
        
        delay = RetryManager.calculate_delay(5, RetryStrategy.LINEAR, base_delay=1.5)
        assert delay == 7.5
    
    def test_retry_delay_calculation_exponential(self):
        """Test exponential retry strategy."""
        delay = RetryManager.calculate_delay(0, RetryStrategy.EXPONENTIAL, base_delay=1.0)
        assert delay == 1.0  # 1 * 2^0
        
        delay = RetryManager.calculate_delay(1, RetryStrategy.EXPONENTIAL, base_delay=1.0)
        assert delay == 2.0  # 1 * 2^1
        
        delay = RetryManager.calculate_delay(3, RetryStrategy.EXPONENTIAL, base_delay=2.0)
        assert delay == 16.0  # 2 * 2^3
    
    def test_retry_delay_calculation_custom(self):
        """Test custom retry strategy (defaults to base delay)."""
        delay = RetryManager.calculate_delay(1, RetryStrategy.CUSTOM, base_delay=3.0)
        assert delay == 3.0
        
        delay = RetryManager.calculate_delay(5, RetryStrategy.CUSTOM, base_delay=1.5)
        assert delay == 1.5
    
    def test_should_retry_within_limit(self):
        """Test retry decision within retry limit."""
        # Should retry for retryable errors
        should_retry = RetryManager.should_retry(
            ConnectionError("Network error"), 
            attempt=2, 
            max_retries=5
        )
        assert should_retry is True
        
        should_retry = RetryManager.should_retry(
            TimeoutError("Timeout"), 
            attempt=1, 
            max_retries=3
        )
        assert should_retry is True
    
    def test_should_retry_exceeded_limit(self):
        """Test retry decision when limit exceeded."""
        should_retry = RetryManager.should_retry(
            ConnectionError("Network error"),
            attempt=5,
            max_retries=3
        )
        assert should_retry is False
        
        should_retry = RetryManager.should_retry(
            TimeoutError("Timeout"),
            attempt=3,
            max_retries=3
        )
        assert should_retry is False
    
    def test_should_retry_non_retryable_error(self):
        """Test retry decision for non-retryable errors."""
        should_retry = RetryManager.should_retry(
            ValueError("Invalid data"),
            attempt=1,
            max_retries=5
        )
        assert should_retry is False
        
        should_retry = RetryManager.should_retry(
            KeyError("Missing key"),
            attempt=0,
            max_retries=3
        )
        assert should_retry is False
    
    def test_should_retry_custom_retryable_errors(self):
        """Test retry decision with custom retryable error types."""
        custom_retryable = [ValueError, TypeError]
        
        should_retry = RetryManager.should_retry(
            ValueError("Retryable value error"),
            attempt=1,
            max_retries=3,
            retryable_errors=custom_retryable
        )
        assert should_retry is True
        
        should_retry = RetryManager.should_retry(
            ConnectionError("Non-retryable in custom list"),
            attempt=1,
            max_retries=3,
            retryable_errors=custom_retryable
        )
        assert should_retry is False


class TestCircuitBreaker:
    """Test CircuitBreaker functionality."""
    
    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker initial state."""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
        
        assert breaker.state == "CLOSED"
        assert breaker.failure_count == 0
        assert breaker.last_failure_time is None
        assert breaker.can_execute() is True
    
    def test_circuit_breaker_success_recording(self):
        """Test recording successful operations."""
        breaker = CircuitBreaker()
        breaker.failure_count = 2  # Set some failures
        breaker.state = "HALF_OPEN"
        
        breaker.record_success()
        
        assert breaker.failure_count == 0
        assert breaker.state == "CLOSED"
        assert breaker.can_execute() is True
    
    def test_circuit_breaker_failure_recording(self):
        """Test recording failed operations."""
        breaker = CircuitBreaker(failure_threshold=3)
        
        # Record failures below threshold
        breaker.record_failure()
        assert breaker.failure_count == 1
        assert breaker.state == "CLOSED"
        assert breaker.can_execute() is True
        
        breaker.record_failure()
        assert breaker.failure_count == 2
        assert breaker.state == "CLOSED"
        
        # Record failure that triggers circuit opening
        breaker.record_failure()
        assert breaker.failure_count == 3
        assert breaker.state == "OPEN"
        assert breaker.can_execute() is False
        assert breaker.last_failure_time is not None
    
    def test_circuit_breaker_recovery_transition(self):
        """Test circuit breaker recovery transition."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        # Trip the circuit
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == "OPEN"
        assert breaker.can_execute() is False
        
        # Wait for recovery timeout
        time.sleep(1.1)
        
        # Should transition to HALF_OPEN
        can_execute = breaker.can_execute()
        assert can_execute is True
        assert breaker.state == "HALF_OPEN"
    
    def test_circuit_breaker_half_open_state(self):
        """Test circuit breaker half-open state behavior."""
        breaker = CircuitBreaker()
        breaker.state = "HALF_OPEN"
        
        # Should allow execution in half-open state
        assert breaker.can_execute() is True
        
        # Success should close the circuit
        breaker.record_success()
        assert breaker.state == "CLOSED"
        
        # Reset to half-open for failure test
        breaker.state = "HALF_OPEN"
        breaker.record_failure()
        assert breaker.state == "OPEN"
    
    def test_circuit_breaker_open_state_timeout_not_reached(self):
        """Test circuit breaker remains open when timeout not reached."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        
        # Trip the circuit
        breaker.record_failure()
        assert breaker.state == "OPEN"
        
        # Should not allow execution before timeout
        assert breaker.can_execute() is False
        
        # Short wait should not change state
        time.sleep(0.1)
        assert breaker.can_execute() is False
        assert breaker.state == "OPEN"


class TestErrorReporter:
    """Test ErrorReporter functionality."""
    
    @pytest.fixture
    def mock_streamlit_session(self):
        """Mock Streamlit session state."""
        with patch('streamlit.session_state', {}) as mock_session:
            yield mock_session
    
    @patch('logging.getLogger')
    def test_error_reporting_basic(self, mock_logger, mock_streamlit_session):
        """Test basic error reporting functionality."""
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        error_context = ErrorContext(
            error=ValueError("Test error"),
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.DATA
        )
        
        ErrorReporter.report_error(error_context)
        
        # Should store in session state
        assert 'error_history' in mock_streamlit_session
        assert len(mock_streamlit_session['error_history']) == 1
        
        stored_error = mock_streamlit_session['error_history'][0]
        assert stored_error['error_id'] == error_context.error_id
        assert stored_error['severity'] == ErrorSeverity.HIGH.value
        assert stored_error['category'] == ErrorCategory.DATA.value
        
        # Should log to system logger
        mock_logger_instance.log.assert_called()
    
    def test_error_reporting_history_limit(self, mock_streamlit_session):
        """Test error history limit enforcement."""
        # Fill history with 100 errors
        mock_streamlit_session['error_history'] = [
            {'error_id': f'error_{i}', 'timestamp': datetime.now().isoformat()}
            for i in range(100)
        ]
        
        # Add one more error
        error_context = ErrorContext(error=ValueError("New error"))
        ErrorReporter.report_error(error_context)
        
        # Should keep only 100 errors (99 old + 1 new)
        assert len(mock_streamlit_session['error_history']) == 100
        assert mock_streamlit_session['error_history'][-1]['error_id'] == error_context.error_id
    
    @patch('logging.getLogger')
    def test_error_reporting_log_levels(self, mock_logger, mock_streamlit_session):
        """Test different log levels for different severities."""
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        # Test each severity level
        severities_and_levels = [
            (ErrorSeverity.LOW, logging.INFO),
            (ErrorSeverity.MEDIUM, logging.WARNING),
            (ErrorSeverity.HIGH, logging.ERROR),
            (ErrorSeverity.CRITICAL, logging.CRITICAL)
        ]
        
        for severity, expected_level in severities_and_levels:
            mock_logger_instance.reset_mock()
            
            error_context = ErrorContext(
                error=Exception("Test"),
                severity=severity
            )
            
            ErrorReporter.report_error(error_context)
            
            # Should log at correct level
            mock_logger_instance.log.assert_called()
            call_args = mock_logger_instance.log.call_args
            assert call_args[0][0] == expected_level
    
    def test_error_analytics_empty_history(self, mock_streamlit_session):
        """Test error analytics with empty history."""
        analytics = ErrorReporter.get_error_analytics()
        
        assert analytics['total_errors'] == 0
    
    def test_error_analytics_with_data(self, mock_streamlit_session):
        """Test error analytics with error data."""
        # Create mock error history
        now = datetime.now()
        error_history = [
            {
                'error_id': 'error1',
                'timestamp': now.isoformat(),
                'category': 'network',
                'severity': 'high'
            },
            {
                'error_id': 'error2',
                'timestamp': (now - timedelta(minutes=30)).isoformat(),
                'category': 'data',
                'severity': 'medium'
            },
            {
                'error_id': 'error3',
                'timestamp': (now - timedelta(hours=2)).isoformat(),
                'category': 'network',
                'severity': 'high'
            }
        ]
        
        mock_streamlit_session['error_history'] = error_history
        
        analytics = ErrorReporter.get_error_analytics()
        
        assert analytics['total_errors'] == 3
        assert analytics['errors_by_category']['network'] == 2
        assert analytics['errors_by_category']['data'] == 1
        assert analytics['errors_by_severity']['high'] == 2
        assert analytics['errors_by_severity']['medium'] == 1
        assert analytics['recent_errors'] == 2  # Last hour
        assert analytics['most_common_category'] == 'network'
        assert analytics['most_common_severity'] == 'high'


class TestGracefulDegradation:
    """Test GracefulDegradation utilities."""
    
    @pytest.fixture
    def mock_streamlit(self):
        """Mock Streamlit functions."""
        with patch.multiple(
            'streamlit',
            warning=Mock()
        ) as mocks:
            yield mocks
    
    @patch('logging.getLogger')
    def test_with_fallback_success(self, mock_logger, mock_streamlit):
        """Test fallback when primary function succeeds."""
        def primary_func():
            return "primary result"
        
        def fallback_func():
            return "fallback result"
        
        result = GracefulDegradation.with_fallback(
            primary_func, 
            fallback_func,
            "Test error message"
        )()
        
        assert result == "primary result"
        mock_streamlit['warning'].assert_not_called()
    
    @patch('logging.getLogger')
    def test_with_fallback_primary_fails(self, mock_logger, mock_streamlit):
        """Test fallback when primary function fails."""
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        def primary_func():
            raise ConnectionError("Primary failed")
        
        def fallback_func():
            return "fallback result"
        
        result = GracefulDegradation.with_fallback(
            primary_func,
            fallback_func,
            "Using backup data"
        )()
        
        assert result == "fallback result"
        mock_streamlit['warning'].assert_called_with("⚠️ Using backup data")
        mock_logger_instance.warning.assert_called()
    
    def test_cached_fallback_success_caches_result(self, mock_streamlit):
        """Test cached fallback caches successful results."""
        with patch('streamlit.session_state', {}) as mock_session:
            def primary_func():
                return {"data": "success"}
            
            result = GracefulDegradation.cached_fallback(
                "test_cache",
                primary_func,
                cache_duration=3600
            )
            
            assert result == {"data": "success"}
            assert mock_session["test_cache"] == {"data": "success"}
            assert "test_cache_timestamp" in mock_session
    
    def test_cached_fallback_uses_cache_on_failure(self, mock_streamlit):
        """Test cached fallback uses cache when primary fails."""
        cached_data = {"data": "cached"}
        cache_time = datetime.now()
        
        with patch('streamlit.session_state', {
            "test_cache": cached_data,
            "test_cache_timestamp": cache_time
        }) as mock_session:
            def failing_func():
                raise ConnectionError("Primary failed")
            
            result = GracefulDegradation.cached_fallback(
                "test_cache",
                failing_func,
                cache_duration=3600
            )
            
            assert result == cached_data
            mock_streamlit['warning'].assert_called()
    
    def test_cached_fallback_expired_cache_raises_error(self, mock_streamlit):
        """Test cached fallback re-raises error when cache expired."""
        cached_data = {"data": "old"}
        old_time = datetime.now() - timedelta(hours=2)
        
        with patch('streamlit.session_state', {
            "test_cache": cached_data,
            "test_cache_timestamp": old_time
        }):
            def failing_func():
                raise ConnectionError("Primary failed")
            
            with pytest.raises(ConnectionError):
                GracefulDegradation.cached_fallback(
                    "test_cache",
                    failing_func,
                    cache_duration=3600  # 1 hour, cache is 2 hours old
                )
    
    def test_cached_fallback_no_cache_raises_error(self, mock_streamlit):
        """Test cached fallback re-raises error when no cache available."""
        with patch('streamlit.session_state', {}):
            def failing_func():
                raise ConnectionError("Primary failed")
            
            with pytest.raises(ConnectionError):
                GracefulDegradation.cached_fallback(
                    "test_cache",
                    failing_func
                )


class TestErrorBoundaryClass:
    """Test ErrorBoundary class functionality."""
    
    @pytest.fixture
    def mock_streamlit(self):
        """Mock Streamlit functions."""
        with patch.multiple(
            'streamlit',
            warning=Mock(),
            error=Mock(),
            button=Mock(return_value=False),
            checkbox=Mock(return_value=False),
            columns=Mock(return_value=[Mock(), Mock()]),
            expander=Mock(),
            code=Mock(),
            json=Mock(),
            rerun=Mock()
        ) as mocks:
            yield mocks
    
    def test_error_boundary_success(self, mock_streamlit):
        """Test error boundary with successful execution."""
        with ErrorBoundary("TestComponent"):
            result = "success"
        
        # Should not trigger error display
        mock_streamlit['error'].assert_not_called()
        mock_streamlit['warning'].assert_not_called()
    
    def test_error_boundary_handles_error(self, mock_streamlit):
        """Test error boundary handles errors."""
        with ErrorBoundary("TestComponent"):
            raise ValueError("Test error")
        
        # Should display error based on severity
        assert mock_streamlit['warning'].called or mock_streamlit['error'].called
    
    def test_error_boundary_severity_determination(self):
        """Test error boundary severity determination."""
        boundary = ErrorBoundary("Test")
        
        # Network errors should be HIGH
        assert boundary._determine_severity(ConnectionError) == ErrorSeverity.HIGH
        assert boundary._determine_severity(TimeoutError) == ErrorSeverity.HIGH
        
        # Data errors should be MEDIUM
        assert boundary._determine_severity(ValueError) == ErrorSeverity.MEDIUM
        assert boundary._determine_severity(TypeError) == ErrorSeverity.MEDIUM
        
        # Session errors should be LOW
        assert boundary._determine_severity(KeyError) == ErrorSeverity.LOW
        
        # Others should be MEDIUM
        assert boundary._determine_severity(Exception) == ErrorSeverity.MEDIUM
    
    def test_error_boundary_category_determination(self):
        """Test error boundary category determination."""
        boundary = ErrorBoundary("Test")
        
        # Network categories
        assert boundary._determine_category(ConnectionError) == ErrorCategory.NETWORK
        assert boundary._determine_category(TimeoutError) == ErrorCategory.NETWORK
        
        # Data categories
        assert boundary._determine_category(ValueError) == ErrorCategory.DATA
        assert boundary._determine_category(TypeError) == ErrorCategory.DATA
        
        # Session categories
        assert boundary._determine_category(KeyError) == ErrorCategory.SESSION
        
        # System categories
        assert boundary._determine_category(Exception) == ErrorCategory.SYSTEM
    
    @patch('utils.error_handling.ErrorReporter.report_error')
    def test_error_boundary_error_reporting(self, mock_report, mock_streamlit):
        """Test error boundary error reporting."""
        with ErrorBoundary("TestComponent"):
            raise ValueError("Test error")
        
        # Should report error
        mock_report.assert_called_once()
        error_context = mock_report.call_args[0][0]
        assert error_context.context_data['component'] == 'TestComponent'
    
    def test_error_boundary_recovery_options(self, mock_streamlit):
        """Test error boundary recovery options."""
        with ErrorBoundary("TestComponent"):
            raise ValueError("Test error")
        
        # Should create retry and details buttons
        mock_streamlit['button'].assert_called()
    
    def test_error_boundary_show_details(self, mock_streamlit):
        """Test error boundary technical details display."""
        boundary = ErrorBoundary("TestComponent", show_details=True)
        
        with boundary:
            raise ValueError("Test error")
        
        # Should show technical details
        mock_streamlit['expander'].assert_called()


class TestSafeExecute:
    """Test safe_execute function."""
    
    @pytest.fixture
    def mock_streamlit(self):
        """Mock Streamlit functions."""
        with patch.multiple(
            'streamlit',
            error=Mock(),
            warning=Mock(),
            checkbox=Mock(return_value=False),
            code=Mock()
        ) as mocks:
            yield mocks
    
    def test_safe_execute_success(self, mock_streamlit):
        """Test safe_execute with successful function."""
        def successful_func(x, y):
            return x + y
        
        result = safe_execute(successful_func, 2, 3)
        assert result == 5
        
        # Should not show error
        mock_streamlit['error'].assert_not_called()
    
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_safe_execute_with_retries(self, mock_sleep, mock_streamlit):
        """Test safe_execute with retry logic."""
        call_count = 0
        
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return "success after retries"
        
        result = safe_execute(
            failing_func,
            retry_strategy=RetryStrategy.IMMEDIATE,
            max_retries=3
        )
        
        assert result == "success after retries"
        assert call_count == 3
    
    @patch('time.sleep')
    def test_safe_execute_exhausted_retries(self, mock_sleep, mock_streamlit):
        """Test safe_execute when retries are exhausted."""
        def always_failing_func():
            raise ConnectionError("Always fails")
        
        result = safe_execute(
            always_failing_func,
            error_message="Custom error message",
            max_retries=2
        )
        
        assert result is None
        mock_streamlit['error'].assert_called_with("❌ Custom error message")
    
    def test_safe_execute_with_fallback(self, mock_streamlit):
        """Test safe_execute with fallback function."""
        def failing_func():
            raise ValueError("Primary failed")
        
        def fallback_func():
            return "fallback result"
        
        result = safe_execute(
            failing_func,
            fallback_func=fallback_func,
            max_retries=1
        )
        
        assert result == "fallback result"
        mock_streamlit['warning'].assert_called()
    
    def test_safe_execute_fallback_also_fails(self, mock_streamlit):
        """Test safe_execute when fallback also fails."""
        def failing_func():
            raise ValueError("Primary failed")
        
        def failing_fallback():
            raise Exception("Fallback also failed")
        
        result = safe_execute(
            failing_func,
            fallback_func=failing_fallback,
            max_retries=1
        )
        
        assert result is None
        mock_streamlit['error'].assert_called()
    
    @patch('utils.error_handling.ErrorReporter.report_error')
    def test_safe_execute_error_reporting(self, mock_report, mock_streamlit):
        """Test safe_execute error reporting."""
        def failing_func():
            raise ValueError("Test error")
        
        safe_execute(failing_func, max_retries=1)
        
        # Should report error
        mock_report.assert_called_once()
    
    def test_safe_execute_technical_details(self, mock_streamlit):
        """Test safe_execute technical details display."""
        mock_streamlit['checkbox'].return_value = True  # Show details
        
        def failing_func():
            raise ValueError("Test error details")
        
        safe_execute(failing_func, max_retries=0)
        
        # Should show technical details
        mock_streamlit['code'].assert_called()


class TestErrorHandlerDecorator:
    """Test error_handler decorator functionality."""
    
    @pytest.fixture
    def mock_streamlit(self):
        """Mock Streamlit functions."""
        with patch.multiple(
            'streamlit',
            error=Mock(),
            warning=Mock(),
            checkbox=Mock(return_value=False),
            code=Mock()
        ) as mocks:
            yield mocks
    
    def test_error_handler_decorator_success(self, mock_streamlit):
        """Test error handler decorator with successful function."""
        @error_handler(category=ErrorCategory.DATA, severity=ErrorSeverity.HIGH)
        def successful_func(x):
            return x * 2
        
        result = successful_func(5)
        assert result == 10
        
        mock_streamlit['error'].assert_not_called()
    
    def test_error_handler_decorator_with_error(self, mock_streamlit):
        """Test error handler decorator with error."""
        @error_handler(
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.HIGH,
            user_message="Network operation failed"
        )
        def failing_func():
            raise ConnectionError("Network error")
        
        result = failing_func()
        assert result is None
        
        mock_streamlit['error'].assert_called_with("❌ Network operation failed")
    
    def test_error_handler_decorator_default_message(self, mock_streamlit):
        """Test error handler decorator with default error message."""
        @error_handler()
        def failing_func():
            raise ValueError("Test error")
        
        result = failing_func()
        assert result is None
        
        # Should use function name in default message
        error_call = mock_streamlit['error'].call_args[0][0]
        assert "failing_func" in error_call
    
    @patch('time.sleep')
    def test_error_handler_decorator_with_retries(self, mock_sleep, mock_streamlit):
        """Test error handler decorator with retry configuration."""
        call_count = 0
        
        @error_handler(
            retry_strategy=RetryStrategy.IMMEDIATE,
            max_retries=2
        )
        def eventually_successful_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Temporary failure")
            return "success"
        
        result = eventually_successful_func()
        assert result == "success"
        assert call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])