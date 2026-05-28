"""Tests for get_lines.py"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))

from get_lines import get_lines


class TestGetLines(unittest.TestCase):
    """Test get_lines function."""

    @patch('get_lines.make_api_call_with_retry')
    def test_success_returns_line_ids(self, mock_api_call):
        """Test successful retrieval of line IDs."""
        mock_api_call.return_value = [
            {"id": "bakerloo", "name": "Bakerloo"},
            {"id": "central", "name": "Central"},
            {"id": "circle", "name": "Circle"}
        ]

        result = get_lines()

        self.assertEqual(result, ["bakerloo", "central", "circle"])
        mock_api_call.assert_called_once_with(
            "https://api.tfl.gov.uk/Line/Mode/tube")

    @patch('get_lines.make_api_call_with_retry')
    def test_empty_list_response(self, mock_api_call):
        """Test API returns empty list."""
        mock_api_call.return_value = []

        result = get_lines()

        self.assertEqual(result, [])

    @patch('get_lines.make_api_call_with_retry')
    def test_api_returns_empty_dict_failure(self, mock_api_call):
        """Test API failure returns empty dict."""
        mock_api_call.return_value = {}

        result = get_lines()

        self.assertEqual(result, [])

    @patch('get_lines.make_api_call_with_retry')
    def test_api_returns_dict_wrong_format(self, mock_api_call):
        """Test API returns dict instead of list."""
        mock_api_call.return_value = {
            "error": "unexpected format",
            "data": [{"id": "line1"}]
        }

        result = get_lines()

        self.assertEqual(result, [])

    @patch('get_lines.make_api_call_with_retry')
    def test_custom_mode_parameter(self, mock_api_call):
        """Test custom mode parameter is used in URL."""
        mock_api_call.return_value = [
            {"id": "dlr-1", "name": "DLR Line 1"}
        ]

        result = get_lines(mode="dlr")

        self.assertEqual(result, ["dlr-1"])
        mock_api_call.assert_called_once_with(
            "https://api.tfl.gov.uk/Line/Mode/dlr")

    @patch('get_lines.make_api_call_with_retry')
    def test_elizabeth_line_mode(self, mock_api_call):
        """Test elizabeth-line mode parameter."""
        mock_api_call.return_value = [
            {"id": "elizabeth", "name": "Elizabeth Line"}
        ]

        result = get_lines(mode="elizabeth-line")

        self.assertEqual(result, ["elizabeth"])
        mock_api_call.assert_called_once_with(
            "https://api.tfl.gov.uk/Line/Mode/elizabeth-line")

    @patch('get_lines.make_api_call_with_retry')
    def test_list_with_missing_id_field(self, mock_api_call):
        """Test list items missing 'id' field raises KeyError."""
        mock_api_call.return_value = [
            {"name": "Line Without ID"}
        ]

        # This should raise KeyError since 'id' field is missing
        with self.assertRaises(KeyError):
            get_lines()

    @patch('get_lines.make_api_call_with_retry')
    def test_multiple_lines_extraction(self, mock_api_call):
        """Test extraction of multiple line IDs."""
        mock_api_call.return_value = [
            {"id": "bakerloo", "name": "Bakerloo", "colour": "Brown"},
            {"id": "central", "name": "Central", "colour": "Red"},
            {"id": "circle", "name": "Circle", "colour": "Yellow"},
            {"id": "district", "name": "District", "colour": "Green"},
            {"id": "hammersmith-city", "name": "Hammersmith & City", "colour": "Pink"},
        ]

        result = get_lines()

        self.assertEqual(len(result), 5)
        self.assertIn("bakerloo", result)
        self.assertIn("central", result)
        self.assertIn("hammersmith-city", result)


if __name__ == '__main__':
    unittest.main()
