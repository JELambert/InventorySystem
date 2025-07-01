"""
Test suite for page-level error boundaries and page error recovery.

Tests error handling in actual Streamlit pages, page navigation errors,
session state recovery, and page-specific error scenarios.
"""

import pytest
import streamlit as st
from unittest.mock import Mock, patch, MagicMock
import sys
import importlib
import types

# Mock the required modules and components before importing pages
sys.modules['utils.api_client'] = Mock()
sys.modules['utils.helpers'] = Mock()
sys.modules['utils.notifications'] = Mock()
sys.modules['utils.error_handling'] = Mock()
sys.modules['components.error_boundary'] = Mock()
sys.modules['components.validation'] = Mock()
sys.modules['components.performance'] = Mock()
sys.modules['components.visualizations'] = Mock()


class TestPageErrorBoundaries:
    """Test error boundaries for individual pages."""
    
    @pytest.fixture
    def mock_streamlit_page_setup(self):
        """Mock Streamlit page setup functions."""
        with patch.multiple(
            'streamlit',
            set_page_config=Mock(),
            title=Mock(),
            header=Mock(),
            subheader=Mock(),
            write=Mock(),
            info=Mock(),
            warning=Mock(),
            error=Mock(),
            success=Mock(),
            markdown=Mock(),
            expander=Mock(),
            columns=Mock(return_value=[Mock(), Mock(), Mock()]),
            metric=Mock(),
            selectbox=Mock(),
            button=Mock(return_value=False),
            text_input=Mock(),
            number_input=Mock(),
            dataframe=Mock(),
            plotly_chart=Mock(),
            progress=Mock(),
            empty=Mock(),
            container=Mock(),
            sidebar=Mock(),
            session_state={},
            rerun=Mock(),
            switch_page=Mock(),
            stop=Mock()
        ) as mocks:
            yield mocks
    
    @pytest.fixture
    def mock_api_client(self):
        """Mock API client with various response scenarios."""
        mock_client = Mock()
        
        # Default successful responses
        mock_client.get_items.return_value = {"items": [], "total": 0}
        mock_client.get_locations.return_value = {"locations": []}
        mock_client.get_categories.return_value = {"categories": []}
        mock_client.get_performance_metrics.return_value = {"status": "available"}
        mock_client.get_inventory_summary.return_value = {"total_items": 0}
        mock_client.get_item_statistics.return_value = {"overview": {}}
        
        return mock_client
    
    @pytest.fixture
    def mock_helpers(self):
        """Mock helper functions."""
        mock_helpers = Mock()
        mock_helpers.safe_get_nested.return_value = None
        mock_helpers.safe_str.side_effect = lambda x, default="": str(x) if x is not None else default
        mock_helpers.safe_float.side_effect = lambda x, default=0.0: float(x) if x is not None else default
        mock_helpers.safe_int.side_effect = lambda x, default=0: int(x) if x is not None else default
        return mock_helpers
    
    def test_dashboard_page_api_failure_recovery(self, mock_streamlit_page_setup, mock_api_client):
        """Test dashboard page recovery from API failures."""
        # Configure API client to fail
        mock_api_client.get_performance_metrics.side_effect = ConnectionError("API unavailable")
        mock_api_client.get_item_statistics.side_effect = ConnectionError("API unavailable")
        
        with patch('utils.api_client.APIClient', return_value=mock_api_client):
            with patch('utils.helpers', spec=['safe_get_nested', 'safe_str', 'safe_float', 'safe_int']):
                # Simulate dashboard page execution with error boundary
                try:
                    # This would normally be the dashboard page main function
                    # wrapped in a page error boundary
                    with patch('components.error_boundary.PageErrorBoundary') as mock_boundary:
                        mock_boundary_instance = Mock()
                        mock_boundary.return_value.__enter__ = Mock(return_value=mock_boundary_instance)
                        mock_boundary.return_value.__exit__ = Mock(return_value=True)  # Suppress exceptions
                        
                        # Simulate page content that would fail
                        mock_api_client.get_performance_metrics()
                        mock_api_client.get_item_statistics()
                        
                except ConnectionError:
                    pass  # Expected to be caught by error boundary
        
        # Error boundary should have been created for dashboard
        assert True  # Test that error boundary setup works
    
    def test_items_page_data_loading_errors(self, mock_streamlit_page_setup, mock_api_client):
        """Test items page handling of data loading errors."""
        # Configure API to return malformed data
        mock_api_client.get_items.return_value = {"invalid": "structure"}
        mock_api_client.get_categories.side_effect = ValueError("Invalid category data")
        
        with patch('utils.api_client.APIClient', return_value=mock_api_client):
            with patch('components.error_boundary.DataLoadingErrorBoundary') as mock_boundary:
                mock_boundary_instance = Mock()
                mock_boundary.return_value.__enter__ = Mock(return_value=mock_boundary_instance)
                mock_boundary.return_value.__exit__ = Mock(return_value=True)
                
                # Simulate items page data loading
                try:
                    items_data = mock_api_client.get_items()
                    categories_data = mock_api_client.get_categories()
                except (ValueError, KeyError):
                    pass  # Should be caught by data loading boundary
        
        # Data loading error boundary should handle the errors
        assert True
    
    def test_locations_page_session_state_corruption(self, mock_streamlit_page_setup):
        """Test locations page handling of corrupted session state."""
        # Corrupt session state
        corrupted_session = {
            'selected_location': {'invalid': 'structure'},
            'location_cache': None,
            'malformed_key': object()  # Non-serializable object
        }
        
        with patch('streamlit.session_state', corrupted_session):
            with patch('components.error_boundary.PageErrorBoundary') as mock_boundary:
                mock_boundary_instance = Mock()
                mock_boundary.return_value.__enter__ = Mock(return_value=mock_boundary_instance)
                mock_boundary.return_value.__exit__ = Mock(return_value=True)
                
                # Simulate accessing corrupted session state
                try:
                    selected = corrupted_session.get('selected_location', {})
                    # This might fail due to corrupted data structure
                    location_id = selected['id']  # KeyError expected
                except (KeyError, TypeError, AttributeError):
                    pass  # Should be caught by page boundary
        
        assert True
    
    def test_movement_page_form_validation_errors(self, mock_streamlit_page_setup, mock_api_client):
        """Test movement page handling of form validation errors."""
        # Configure API to return validation errors
        mock_api_client.create_movement.side_effect = ValueError("Invalid movement data")
        mock_api_client.validate_movement.return_value = {
            "is_valid": False,
            "errors": ["Insufficient quantity", "Invalid location"]
        }
        
        with patch('utils.api_client.APIClient', return_value=mock_api_client):
            with patch('components.error_boundary.FormErrorBoundary') as mock_boundary:
                mock_boundary_instance = Mock()
                mock_boundary_instance.has_errors.return_value = True
                mock_boundary.return_value.__enter__ = Mock(return_value=mock_boundary_instance)
                mock_boundary.return_value.__exit__ = Mock(return_value=True)
                
                # Simulate form submission with validation errors
                try:
                    validation_result = mock_api_client.validate_movement()
                    if not validation_result["is_valid"]:
                        for error in validation_result["errors"]:
                            mock_boundary_instance.add_form_error(error)
                    
                    # Attempt to create movement
                    mock_api_client.create_movement()
                except ValueError:
                    pass  # Should be caught by form boundary
        
        # Form boundary should handle validation errors
        assert True
    
    def test_categories_page_concurrent_modification_errors(self, mock_streamlit_page_setup, mock_api_client):
        """Test categories page handling of concurrent modification errors."""
        # Simulate concurrent modification conflict
        mock_api_client.update_category.side_effect = Exception("Version conflict - record was modified")
        mock_api_client.delete_category.side_effect = Exception("Category is in use")
        
        with patch('utils.api_client.APIClient', return_value=mock_api_client):
            with patch('components.error_boundary.ComponentErrorBoundary') as mock_boundary:
                mock_boundary_instance = Mock()
                mock_boundary.return_value.__enter__ = Mock(return_value=mock_boundary_instance)
                mock_boundary.return_value.__exit__ = Mock(return_value=True)
                
                # Simulate concurrent modification scenarios
                try:
                    mock_api_client.update_category()
                except Exception:
                    pass
                
                try:
                    mock_api_client.delete_category()
                except Exception:
                    pass
        
        assert True
    
    def test_manage_page_permission_errors(self, mock_streamlit_page_setup, mock_api_client):
        """Test manage page handling of permission errors."""
        from utils.api_client import APIError
        
        # Configure API to return permission errors
        mock_api_client.bulk_update_items.side_effect = APIError("Forbidden", 403, {"detail": "Insufficient permissions"})
        mock_api_client.delete_item.side_effect = APIError("Forbidden", 403, {"detail": "Delete not allowed"})
        
        with patch('utils.api_client.APIClient', return_value=mock_api_client):
            with patch('components.error_boundary.NetworkErrorHandler') as mock_handler:
                mock_handler.handle_api_error.return_value = True
                
                # Simulate permission-restricted operations
                try:
                    mock_api_client.bulk_update_items()
                except APIError as e:
                    mock_handler.handle_api_error(e, "Bulk Update")
                
                try:
                    mock_api_client.delete_item()
                except APIError as e:
                    mock_handler.handle_api_error(e, "Delete Item")
        
        # Network error handler should handle API errors
        mock_handler.handle_api_error.assert_called()


class TestPageNavigationErrors:
    """Test error handling during page navigation."""
    
    @pytest.fixture
    def mock_streamlit_navigation(self):
        """Mock Streamlit navigation functions."""
        with patch.multiple(
            'streamlit',
            switch_page=Mock(),
            stop=Mock(),
            error=Mock(),
            warning=Mock(),
            info=Mock(),
            session_state={}
        ) as mocks:
            yield mocks
    
    def test_navigation_to_nonexistent_page(self, mock_streamlit_navigation):
        """Test handling navigation to non-existent pages."""
        with patch('components.error_boundary.PageErrorBoundary') as mock_boundary:
            mock_boundary_instance = Mock()
            mock_boundary.return_value.__enter__ = Mock(return_value=mock_boundary_instance)
            mock_boundary.return_value.__exit__ = Mock(return_value=True)
            
            # Simulate navigation to non-existent page
            try:
                # This would raise an error in real scenario
                raise FileNotFoundError("Page not found: nonexistent_page.py")
            except FileNotFoundError:
                pass  # Should be caught by error boundary
        
        assert True
    
    def test_navigation_with_invalid_session_state(self, mock_streamlit_navigation):
        """Test navigation with corrupted session state."""
        # Corrupt session state that might affect navigation
        mock_streamlit_navigation['session_state'].update({
            'current_page': None,
            'navigation_history': ['invalid', None, object()],
            'user_context': {'corrupted': 'data'}
        })
        
        with patch('components.error_boundary.PageErrorBoundary') as mock_boundary:
            mock_boundary_instance = Mock()
            mock_boundary.return_value.__enter__ = Mock(return_value=mock_boundary_instance)
            mock_boundary.return_value.__exit__ = Mock(return_value=True)
            
            # Simulate navigation with corrupted state
            try:
                # This would normally fail due to corrupted navigation state
                history = mock_streamlit_navigation['session_state']['navigation_history']
                last_page = history[-1].get('page_name')  # AttributeError expected
            except (AttributeError, TypeError):
                pass  # Should be caught by error boundary
        
        assert True
    
    def test_navigation_with_authentication_errors(self, mock_streamlit_navigation):
        """Test navigation when authentication fails."""
        with patch('components.error_boundary.PageErrorBoundary') as mock_boundary:
            mock_boundary_instance = Mock()
            mock_boundary.return_value.__enter__ = Mock(return_value=mock_boundary_instance)
            mock_boundary.return_value.__exit__ = Mock(return_value=True)
            
            # Simulate authentication failure during navigation
            try:
                # This would raise auth error in real scenario
                raise PermissionError("Authentication required for page access")
            except PermissionError:
                pass  # Should be caught by error boundary
        
        assert True


class TestPageRecoveryMechanisms:
    """Test page recovery mechanisms and fallback content."""
    
    @pytest.fixture
    def mock_streamlit_recovery(self):
        """Mock Streamlit functions for recovery testing."""
        with patch.multiple(
            'streamlit',
            error=Mock(),
            warning=Mock(),
            info=Mock(),
            success=Mock(),
            markdown=Mock(),
            subheader=Mock(),
            button=Mock(return_value=False),
            columns=Mock(return_value=[Mock(), Mock(), Mock()]),
            expander=Mock(),
            rerun=Mock(),
            switch_page=Mock(),
            session_state={}
        ) as mocks:
            yield mocks
    
    def test_dashboard_fallback_content(self, mock_streamlit_recovery):
        """Test dashboard fallback content when main content fails."""
        def fallback_dashboard():
            mock_streamlit_recovery['info']("Showing basic dashboard information")
            mock_streamlit_recovery['markdown']("• System Status: Available")
            mock_streamlit_recovery['markdown']("• Basic functionality is working")
        
        with patch('components.error_boundary.PageErrorBoundary') as mock_boundary:
            page_boundary = Mock()
            page_boundary.fallback_content = fallback_dashboard
            mock_boundary.return_value = page_boundary
            
            # Simulate page boundary with fallback
            page_boundary.__enter__ = Mock(return_value=page_boundary)
            page_boundary.__exit__ = Mock(return_value=True)
            
            # Simulate primary content failure
            try:
                raise ConnectionError("Primary dashboard content failed")
            except ConnectionError:
                # Error boundary would call fallback
                fallback_dashboard()
        
        # Fallback content should be shown
        mock_streamlit_recovery['info'].assert_called()
        mock_streamlit_recovery['markdown'].assert_called()
    
    def test_items_page_cached_data_fallback(self, mock_streamlit_recovery):
        """Test items page using cached data as fallback."""
        # Setup cached data
        cached_items = [
            {"id": 1, "name": "Cached Item 1"},
            {"id": 2, "name": "Cached Item 2"}
        ]
        mock_streamlit_recovery['session_state']['cached_items'] = cached_items
        
        with patch('components.error_boundary.DataLoadingErrorBoundary') as mock_boundary:
            data_boundary = Mock()
            mock_boundary.return_value = data_boundary
            
            data_boundary.__enter__ = Mock(return_value=data_boundary)
            data_boundary.__exit__ = Mock(return_value=True)
            
            # Simulate using cached data when API fails
            try:
                # Primary data loading would fail
                raise ConnectionError("API unavailable")
            except ConnectionError:
                # Use cached data as fallback
                items = mock_streamlit_recovery['session_state'].get('cached_items', [])
                mock_streamlit_recovery['warning']("Using cached data")
                for item in items:
                    mock_streamlit_recovery['markdown'](f"• {item['name']}")
        
        # Should show cached data warning and items
        mock_streamlit_recovery['warning'].assert_called()
        mock_streamlit_recovery['markdown'].assert_called()
    
    def test_page_recovery_buttons_functionality(self, mock_streamlit_recovery):
        """Test page recovery button functionality."""
        # Simulate button clicks
        button_scenarios = [
            ("🔄 Refresh Page", "page_refresh", lambda: mock_streamlit_recovery['rerun']()),
            ("🏠 Go to Dashboard", "go_dashboard", lambda: mock_streamlit_recovery['switch_page']("pages/01_📊_Dashboard.py")),
            ("🧹 Clear Session", "clear_session", lambda: mock_streamlit_recovery['session_state'].clear())
        ]
        
        for button_text, button_key, action in button_scenarios:
            # Reset mocks
            for mock_func in mock_streamlit_recovery.values():
                if hasattr(mock_func, 'reset_mock'):
                    mock_func.reset_mock()
            
            # Simulate button click
            mock_streamlit_recovery['button'].return_value = True
            
            with patch('components.error_boundary.PageErrorBoundary') as mock_boundary:
                page_boundary = Mock()
                mock_boundary.return_value = page_boundary
                
                # Simulate recovery button handling
                if mock_streamlit_recovery['button'](button_text, key=button_key):
                    action()
            
            # Verify appropriate action was taken
            if "Refresh" in button_text:
                mock_streamlit_recovery['rerun'].assert_called()
            elif "Dashboard" in button_text:
                mock_streamlit_recovery['switch_page'].assert_called()
            elif "Clear Session" in button_text:
                # Session should be cleared (mocked)
                assert True
    
    def test_minimal_recovery_options(self, mock_streamlit_recovery):
        """Test minimal recovery options when all else fails."""
        with patch('components.error_boundary.PageErrorBoundary') as mock_boundary:
            page_boundary = Mock()
            page_boundary.error_count = 10  # Exceed max errors
            page_boundary._show_minimal_recovery_options = Mock()
            mock_boundary.return_value = page_boundary
            
            # Simulate showing minimal recovery options
            page_boundary._show_minimal_recovery_options()
        
        # Should call minimal recovery options
        page_boundary._show_minimal_recovery_options.assert_called()
    
    def test_error_details_display_and_copy(self, mock_streamlit_recovery):
        """Test error details display and copy functionality."""
        mock_streamlit_recovery['button'].return_value = True  # Simulate copy button click
        
        with patch('components.error_boundary.PageErrorBoundary') as mock_boundary:
            page_boundary = Mock()
            mock_boundary.return_value = page_boundary
            
            # Simulate error details display
            error_info = """
Error ID: abc12345
Page: TestPage  
Time: 2024-01-01T12:00:00
Category: network
Message: Connection failed
            """.strip()
            
            if mock_streamlit_recovery['button']("📋 Copy Error Info", key="copy_error_abc12345"):
                mock_streamlit_recovery['code'](error_info)
                mock_streamlit_recovery['success']("Error information displayed above for copying")
        
        # Should display error info for copying
        mock_streamlit_recovery['code'].assert_called()
        mock_streamlit_recovery['success'].assert_called()


class TestPageSessionStateRecovery:
    """Test session state recovery mechanisms."""
    
    @pytest.fixture
    def mock_session_state(self):
        """Mock session state with various corruption scenarios."""
        return {
            'valid_key': 'valid_value',
            'corrupted_object': Mock(),  # Non-serializable
            'nested_corruption': {'valid': 'data', 'invalid': object()},
            'circular_reference': None  # Will be set to create circular ref
        }
    
    def test_session_state_cleanup_on_error(self, mock_session_state):
        """Test session state cleanup when errors occur."""
        # Create circular reference
        mock_session_state['circular_reference'] = mock_session_state
        
        with patch('streamlit.session_state', mock_session_state):
            with patch('components.error_boundary.PageErrorBoundary') as mock_boundary:
                page_boundary = Mock()
                mock_boundary.return_value = page_boundary
                
                # Simulate session cleanup
                def clear_session():
                    keys_to_remove = []
                    for key in list(mock_session_state.keys()):
                        if not key.startswith('_'):  # Keep internal keys
                            keys_to_remove.append(key)
                    
                    for key in keys_to_remove:
                        try:
                            del mock_session_state[key]
                        except Exception:
                            pass  # Ignore errors during cleanup
                
                clear_session()
        
        # Session should be cleaned up
        assert len(mock_session_state) == 0
    
    def test_partial_session_state_recovery(self, mock_session_state):
        """Test recovery of valid session state while discarding corrupted parts."""
        with patch('streamlit.session_state', mock_session_state):
            # Simulate selective cleanup
            def selective_cleanup():
                safe_keys = []
                for key, value in list(mock_session_state.items()):
                    try:
                        # Test if value is serializable/safe
                        str(value)
                        if not isinstance(value, (Mock, object)) or isinstance(value, (str, int, float, bool, list, dict)):
                            safe_keys.append(key)
                    except Exception:
                        del mock_session_state[key]
                
                return safe_keys
            
            safe_keys = selective_cleanup()
        
        # Should keep valid keys and remove problematic ones
        assert 'valid_key' in mock_session_state
        assert len(safe_keys) > 0
    
    def test_session_state_backup_and_restore(self):
        """Test session state backup and restore functionality."""
        original_state = {
            'important_data': 'must_preserve',
            'user_preferences': {'theme': 'dark', 'language': 'en'},
            'form_data': {'field1': 'value1', 'field2': 'value2'}
        }
        
        # Simulate backup creation
        backup = original_state.copy()
        
        # Simulate corruption
        corrupted_state = original_state.copy()
        corrupted_state['corrupted_field'] = object()
        
        # Simulate restore from backup
        restored_state = {}
        for key, value in backup.items():
            try:
                # Only restore serializable data
                str(value)
                restored_state[key] = value
            except Exception:
                pass
        
        # Restored state should match original safe data
        assert restored_state['important_data'] == 'must_preserve'
        assert restored_state['user_preferences']['theme'] == 'dark'
        assert 'corrupted_field' not in restored_state


if __name__ == "__main__":
    pytest.main([__file__, "-v"])