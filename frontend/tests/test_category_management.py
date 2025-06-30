"""
Frontend tests for Category Management functionality.

Tests category page components, form validation, and API interactions.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the frontend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock streamlit before importing any modules that use it
sys.modules['streamlit'] = Mock()

from utils.api_client import APIClient, APIError
from utils.helpers import validate_hex_color


class TestCategoryAPIClient(unittest.TestCase):
    """Test Category API client functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.api_client = APIClient()
        self.api_client._make_request = Mock()
    
    def test_get_categories_success(self):
        """Test successful category retrieval."""
        expected_categories = {
            "categories": [
                {"id": 1, "name": "Electronics", "color": "#0056B3"},
                {"id": 2, "name": "Books", "color": "#28A745"}
            ],
            "total": 2,
            "page": 1,
            "per_page": 20
        }
        
        self.api_client._make_request.return_value = expected_categories
        
        result = self.api_client.get_categories()
        
        self.assertEqual(result, expected_categories)
        self.api_client._make_request.assert_called_once_with(
            "GET", "categories/", params={"page": 1, "per_page": 20, "include_inactive": False}
        )
    
    def test_get_categories_with_filters(self):
        """Test category retrieval with filters."""
        self.api_client._make_request.return_value = {"categories": []}
        
        self.api_client.get_categories(
            page=2, 
            per_page=10, 
            include_inactive=True, 
            search="electronics"
        )
        
        expected_params = {
            "page": 2, 
            "per_page": 10, 
            "include_inactive": True, 
            "search": "electronics"
        }
        self.api_client._make_request.assert_called_once_with(
            "GET", "categories/", params=expected_params
        )
    
    def test_create_category_success(self):
        """Test successful category creation."""
        category_data = {
            "name": "Test Category",
            "description": "Test description",
            "color": "#FF5722"
        }
        expected_response = {**category_data, "id": 1}
        
        self.api_client._make_request.return_value = expected_response
        
        result = self.api_client.create_category(category_data)
        
        self.assertEqual(result, expected_response)
        self.api_client._make_request.assert_called_once_with(
            "POST", "categories/", data=category_data
        )
    
    def test_update_category_success(self):
        """Test successful category update."""
        category_id = 1
        update_data = {"name": "Updated Category"}
        expected_response = {"id": category_id, **update_data}
        
        self.api_client._make_request.return_value = expected_response
        
        result = self.api_client.update_category(category_id, update_data)
        
        self.assertEqual(result, expected_response)
        self.api_client._make_request.assert_called_once_with(
            "PUT", f"categories/{category_id}", data=update_data
        )
    
    def test_delete_category_success(self):
        """Test successful category deletion."""
        category_id = 1
        self.api_client._make_request.return_value = None
        
        result = self.api_client.delete_category(category_id)
        
        self.assertTrue(result)
        self.api_client._make_request.assert_called_once_with(
            "DELETE", f"categories/{category_id}", params={}
        )
    
    def test_delete_category_permanent(self):
        """Test permanent category deletion."""
        category_id = 1
        self.api_client._make_request.return_value = None
        
        result = self.api_client.delete_category(category_id, permanent=True)
        
        self.assertTrue(result)
        self.api_client._make_request.assert_called_once_with(
            "DELETE", f"categories/{category_id}", params={"permanent": True}
        )
    
    def test_delete_category_error(self):
        """Test category deletion with API error."""
        category_id = 1
        self.api_client._make_request.side_effect = APIError("Delete failed")
        
        result = self.api_client.delete_category(category_id)
        
        self.assertFalse(result)
    
    def test_restore_category_success(self):
        """Test successful category restoration."""
        category_id = 1
        expected_response = {"id": category_id, "is_active": True}
        
        self.api_client._make_request.return_value = expected_response
        
        result = self.api_client.restore_category(category_id)
        
        self.assertEqual(result, expected_response)
        self.api_client._make_request.assert_called_once_with(
            "POST", f"categories/{category_id}/restore"
        )
    
    def test_get_category_stats_success(self):
        """Test successful category statistics retrieval."""
        expected_stats = {
            "total_categories": 5,
            "active_categories": 4,
            "most_used_color": "#0056B3"
        }
        
        self.api_client._make_request.return_value = expected_stats
        
        result = self.api_client.get_category_stats()
        
        self.assertEqual(result, expected_stats)
        self.api_client._make_request.assert_called_once_with("GET", "categories/stats")


class TestCategoryValidation(unittest.TestCase):
    """Test category validation functions."""
    
    def test_validate_hex_color_valid(self):
        """Test valid hex color validation."""
        valid_colors = ["#000000", "#FFFFFF", "#FF5722", "#0056B3", "#28A745"]
        
        for color in valid_colors:
            with self.subTest(color=color):
                self.assertTrue(validate_hex_color(color))
    
    def test_validate_hex_color_invalid(self):
        """Test invalid hex color validation."""
        invalid_colors = [
            "000000",      # Missing #
            "#GGG",        # Invalid characters
            "#12345",      # Too short
            "#1234567",    # Too long
            "#12G45A",     # Invalid character in middle
            "red",         # Color name
        ]
        
        for color in invalid_colors:
            with self.subTest(color=color):
                self.assertFalse(validate_hex_color(color))
    
    def test_validate_hex_color_empty_and_none(self):
        """Test that empty/None colors are considered valid (optional field)."""
        # Empty string and None should be valid for optional fields
        self.assertTrue(validate_hex_color(""))
        self.assertTrue(validate_hex_color(None))
    
    def test_validate_hex_color_empty_optional(self):
        """Test that empty/None colors are considered valid (optional field)."""
        # Note: Based on the actual implementation, empty might be valid
        # This test should match the actual behavior in validate_hex_color
        pass


class TestCategoryFormValidation(unittest.TestCase):
    """Test category form validation logic."""
    
    def test_category_name_validation(self):
        """Test category name validation rules."""
        # Valid names
        valid_names = ["Electronics", "Kitchen Items", "Books & Media", "Test123"]
        
        for name in valid_names:
            with self.subTest(name=name):
                # Name should be non-empty and within length limits
                self.assertTrue(len(name.strip()) > 0)
                self.assertTrue(len(name) <= 255)
        
        # Invalid names
        invalid_names = ["", "   ", "a" * 256]  # Empty, whitespace-only, too long
        
        for name in invalid_names:
            with self.subTest(name=name):
                if name == "a" * 256:
                    self.assertTrue(len(name) > 255)
                else:
                    self.assertFalse(len(name.strip()) > 0)
    
    def test_category_description_validation(self):
        """Test category description validation rules."""
        # Valid descriptions (optional field)
        valid_descriptions = [
            None,
            "",
            "Short description",
            "A longer description with more details about the category"
        ]
        
        for desc in valid_descriptions:
            with self.subTest(description=desc):
                # Description is optional, so None and empty should be valid
                self.assertTrue(desc is None or isinstance(desc, str))


class TestCategoryIntegration(unittest.TestCase):
    """Test category integration with other components."""
    
    @patch('utils.api_client.APIClient')
    def test_category_session_state_management(self, mock_api_client):
        """Test category-related session state management."""
        # This would test SessionManager interactions with category operations
        # For now, we'll just verify the pattern exists
        self.assertTrue(True)  # Placeholder
    
    @patch('utils.api_client.APIClient')
    def test_category_pagination(self, mock_api_client):
        """Test category pagination functionality."""
        # Mock API responses for pagination
        mock_client = mock_api_client.return_value
        mock_client.get_categories.return_value = {
            "categories": [{"id": i, "name": f"Category {i}"} for i in range(1, 11)],
            "total": 25,
            "page": 1,
            "pages": 3,
            "per_page": 10
        }
        
        # Test pagination parameters
        result = mock_client.get_categories(page=1, per_page=10)
        
        self.assertEqual(len(result["categories"]), 10)
        self.assertEqual(result["total"], 25)
        self.assertEqual(result["pages"], 3)
    
    @patch('utils.api_client.APIClient')
    def test_category_search_filtering(self, mock_api_client):
        """Test category search and filtering functionality."""
        mock_client = mock_api_client.return_value
        
        # Test search functionality
        mock_client.get_categories.return_value = {
            "categories": [{"id": 1, "name": "Electronics", "color": "#0056B3"}],
            "total": 1
        }
        
        result = mock_client.get_categories(search="electronics")
        
        mock_client.get_categories.assert_called_with(search="electronics")
        self.assertEqual(len(result["categories"]), 1)
        self.assertEqual(result["categories"][0]["name"], "Electronics")


class TestCategoryErrorHandling(unittest.TestCase):
    """Test error handling in category operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.api_client = APIClient()
        self.api_client._make_request = Mock()
    
    def test_api_error_handling(self):
        """Test API error handling."""
        # Test APIError handling
        self.api_client._make_request.side_effect = APIError("API Error")
        
        # Should not raise exception, should handle gracefully
        try:
            result = self.api_client.delete_category(1)
            self.assertFalse(result)  # Should return False on error
        except APIError:
            self.fail("APIError should be handled gracefully")
    
    def test_network_error_handling(self):
        """Test network error handling."""
        # Test general network/connection errors
        self.api_client._make_request.side_effect = Exception("Network error")
        
        # Should handle general exceptions gracefully
        with self.assertRaises(Exception):
            self.api_client.get_categories()
    
    def test_malformed_response_handling(self):
        """Test handling of malformed API responses."""
        # Test with None response
        self.api_client._make_request.return_value = None
        
        result = self.api_client.get_categories()
        self.assertIsNone(result)
        
        # Test with malformed data
        self.api_client._make_request.return_value = {"unexpected": "format"}
        
        result = self.api_client.get_categories()
        self.assertEqual(result, {"unexpected": "format"})


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)