"""Tests for api_utils.py"""

from api_utils import setup_logger, make_api_call_with_retry
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

import requests

# Add parent directory to path to import api_utils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestSetupLogger(unittest.TestCase):
    """Test setup_logger function."""

    def test_setup_logger_default_info(self):
        """Test setup_logger with default INFO level."""
        # Should not raise
        setup_logger()

    def test_setup_logger_debug(self):
        """Test setup_logger with DEBUG level."""
        setup_logger(log_level="DEBUG")

    def test_setup_logger_error(self):
        """Test setup_logger with ERROR level."""
        setup_logger(log_level="ERROR")

    def test_setup_logger_invalid_level(self):
        """Test setup_logger with invalid log level."""
        with self.assertRaises(AttributeError):
            setup_logger(log_level="INVALID")


class TestMakeApiCallWithRetry(unittest.TestCase):
    """Test make_api_call_with_retry function."""

    @patch('requests.get')
    def test_success_200_with_json(self, mock_get):
        """Test successful API call returning 200 with JSON."""
        expected_data = {"key": "value", "number": 42}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_data
        mock_get.return_value = mock_response

        result = make_api_call_with_retry("http://example.com/api")

        self.assertEqual(result, expected_data)
        mock_get.assert_called_once_with("http://example.com/api", timeout=10)

    @patch('requests.get')
    def test_success_returns_list(self, mock_get):
        """Test successful API call returning list data."""
        expected_data = [{"id": 1}, {"id": 2}]
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = expected_data
        mock_get.return_value = mock_response

        result = make_api_call_with_retry("http://example.com/api")

        self.assertEqual(result, expected_data)
        self.assertIsInstance(result, list)

    @patch('requests.get')
    def test_non_200_non_429_error(self, mock_get):
        """Test API call with error status code (500) returns empty dict."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = make_api_call_with_retry("http://example.com/api")

        self.assertEqual(result, {})
        mock_get.assert_called_once()

    @patch('time.sleep')
    @patch('requests.get')
    def test_rate_limit_429_then_success(self, mock_get, mock_sleep):
        """Test rate limit (429) on first attempt, success on retry."""
        # First call returns 429, second call returns 200
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 429

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": "success"}

        mock_get.side_effect = [rate_limit_response, success_response]

        result = make_api_call_with_retry("http://example.com/api")

        self.assertEqual(result, {"data": "success"})
        self.assertEqual(mock_get.call_count, 2)
        mock_sleep.assert_called_once_with(1)  # 2^0 = 1 second

    @patch('time.sleep')
    @patch('requests.get')
    def test_rate_limit_exhausted(self, mock_get, mock_sleep):
        """Test rate limit (429) on all retry attempts returns empty dict."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        result = make_api_call_with_retry(
            "http://example.com/api", max_retries=3)

        self.assertEqual(result, {})
        self.assertEqual(mock_get.call_count, 3)
        # Should sleep 3 times (after each 429 response)
        self.assertEqual(mock_sleep.call_count, 3)

    @patch('time.sleep')
    @patch('requests.get')
    def test_request_exception_then_success(self, mock_get, mock_sleep):
        """Test RequestException on first attempt, success on retry."""
        mock_get.side_effect = [
            requests.exceptions.Timeout("timeout"),
            MagicMock(status_code=200, json=MagicMock(
                return_value={"data": "ok"}))
        ]

        result = make_api_call_with_retry("http://example.com/api")

        self.assertEqual(result, {"data": "ok"})
        self.assertEqual(mock_get.call_count, 2)
        mock_sleep.assert_called_once_with(1)

    @patch('time.sleep')
    @patch('requests.get')
    def test_request_exception_exhausted(self, mock_get, mock_sleep):
        """Test RequestException on all retry attempts returns empty dict."""
        mock_get.side_effect = requests.exceptions.ConnectionError(
            "connection failed")

        result = make_api_call_with_retry(
            "http://example.com/api", max_retries=2)

        self.assertEqual(result, {})
        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(mock_sleep.call_count, 1)

    @patch('time.sleep')
    @patch('requests.get')
    def test_exponential_backoff_timing(self, mock_get, mock_sleep):
        """Test exponential backoff timing (1, 2, 4, 8, 16, 32, 64 seconds)."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        make_api_call_with_retry("http://example.com/api", max_retries=7)

        # Should call sleep with 1, 2, 4, 8, 16, 32, 64 (7 times for 7 attempts)
        expected_sleep_calls = [1, 2, 4, 8, 16, 32, 64]
        actual_sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        self.assertEqual(actual_sleep_calls, expected_sleep_calls)

    @patch('time.sleep')
    @patch('requests.get')
    def test_backoff_capped_at_64(self, mock_get, mock_sleep):
        """Test that backoff is capped at 64 seconds."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        # 8 retries would normally require 128 seconds (2^7), but should cap at 64
        make_api_call_with_retry("http://example.com/api", max_retries=8)

        actual_sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        self.assertTrue(all(call <= 64 for call in actual_sleep_calls))
        self.assertIn(64, actual_sleep_calls)

    @patch('time.sleep')
    @patch('requests.get')
    def test_custom_max_retries(self, mock_get, _mock_sleep):
        """Test custom max_retries parameter."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response

        result = make_api_call_with_retry(
            "http://example.com/api", max_retries=3)

        self.assertEqual(result, {})
        self.assertEqual(mock_get.call_count, 3)

    @patch('requests.get')
    def test_timeout_parameter_passed(self, mock_get):
        """Test that timeout=10 is always passed to requests.get()."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        make_api_call_with_retry("http://example.com/api")

        mock_get.assert_called_with("http://example.com/api", timeout=10)

    @patch('time.sleep')
    @patch('requests.get')
    def test_mixed_failures_429_then_exception(self, mock_get, _mock_sleep):
        """Test mixed failure types: 429 then RequestException."""
        mock_get.side_effect = [
            MagicMock(status_code=429),
            requests.exceptions.Timeout("timeout"),
            MagicMock(status_code=200, json=MagicMock(
                return_value={"success": True}))
        ]

        result = make_api_call_with_retry("http://example.com/api")

        self.assertEqual(result, {"success": True})
        self.assertEqual(mock_get.call_count, 3)


if __name__ == '__main__':
    unittest.main()
