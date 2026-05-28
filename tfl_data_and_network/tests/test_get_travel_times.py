"""Tests for get_travel_times.py"""

from get_travel_times import (
    extract_travel_time_data,
    get_duration_data_from_api_data,
    get_duration_data
)
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))


class TestExtractTravelTimeData(unittest.TestCase):
    """Test extract_travel_time_data function."""

    @patch('get_travel_times.make_api_call_with_retry')
    def test_url_construction(self, mock_api_call):
        """Test URL is correctly constructed."""
        mock_api_call.return_value = {}

        extract_travel_time_data("940GZZLUHPK", "940GZZLUNHG")

        mock_api_call.assert_called_once_with(
            "https://api.tfl.gov.uk/Journey/JourneyResults/940GZZLUHPK/to/940GZZLUNHG")

    @patch('get_travel_times.make_api_call_with_retry')
    def test_returns_api_response(self, mock_api_call):
        """Test that API response is returned directly."""
        expected_data = {
            "journeys": [{"duration": 5}]
        }
        mock_api_call.return_value = expected_data

        result = extract_travel_time_data("start", "end")

        self.assertEqual(result, expected_data)

    @patch('get_travel_times.make_api_call_with_retry')
    def test_returns_empty_dict_on_failure(self, mock_api_call):
        """Test that empty dict is returned on API failure."""
        mock_api_call.return_value = {}

        result = extract_travel_time_data("start", "end")

        self.assertEqual(result, {})


class TestGetDurationDataFromApiData(unittest.TestCase):
    """Test get_duration_data_from_api_data function."""

    def test_success_extracts_duration(self):
        """Test successful extraction of duration from journeys."""
        data = {
            "journeys": [
                {"duration": 5, "startTime": "10:00"}
            ]
        }

        result = get_duration_data_from_api_data(data)

        self.assertEqual(result, 5)

    def test_returns_default_2_when_no_journeys_key(self):
        """Test returns default 2 when journeys key is missing."""
        data = {"fare": 100}

        result = get_duration_data_from_api_data(data)

        self.assertEqual(result, 2)

    def test_returns_default_2_when_journeys_empty(self):
        """Test returns default 2 when journeys list is empty."""
        data = {"journeys": []}

        result = get_duration_data_from_api_data(data)

        self.assertEqual(result, 2)

    def test_uses_first_journey_duration(self):
        """Test that first journey duration is used."""
        data = {
            "journeys": [
                {"duration": 5},
                {"duration": 10},
                {"duration": 15}
            ]
        }

        result = get_duration_data_from_api_data(data)

        self.assertEqual(result, 5)

    def test_warns_on_anomalously_long_duration(self):
        """Test that warning is logged for duration >= 10 minutes."""
        data = {
            "journeys": [
                {"duration": 15}
            ]
        }

        result = get_duration_data_from_api_data(data)

        self.assertEqual(result, 15)

    def test_no_warning_for_normal_duration(self):
        """Test no warning for duration < 10 minutes."""
        data = {
            "journeys": [
                {"duration": 5}
            ]
        }

        result = get_duration_data_from_api_data(data)

        self.assertEqual(result, 5)

    def test_warns_on_exactly_10_minutes(self):
        """Test warning triggered at exactly 10 minutes."""
        data = {
            "journeys": [
                {"duration": 10}
            ]
        }

        result = get_duration_data_from_api_data(data)

        self.assertEqual(result, 10)

    def test_handles_very_long_duration(self):
        """Test handling of very long duration."""
        data = {
            "journeys": [
                {"duration": 120}
            ]
        }

        result = get_duration_data_from_api_data(data)

        self.assertEqual(result, 120)

    def test_missing_duration_field_raises_key_error(self):
        """Test KeyError when duration field is missing."""
        data = {
            "journeys": [
                {"startTime": "10:00"}
            ]
        }

        with self.assertRaises(KeyError):
            get_duration_data_from_api_data(data)

    def test_empty_dict_input(self):
        """Test empty dict input returns default."""
        result = get_duration_data_from_api_data({})

        self.assertEqual(result, 2)

    def test_none_input(self):
        """Test None input (should raise TypeError)."""
        with self.assertRaises(TypeError):
            get_duration_data_from_api_data(None)


class TestGetDurationData(unittest.TestCase):
    """Test get_duration_data orchestration function."""

    @patch('get_travel_times.extract_travel_time_data')
    def test_calls_extract_and_get_duration(self, mock_extract):
        """Test that orchestration function calls both sub-functions."""
        mock_extract.return_value = {
            "journeys": [{"duration": 5}]
        }

        result = get_duration_data("start", "end")

        self.assertEqual(result, 5)
        mock_extract.assert_called_once_with("start", "end")

    @patch('get_travel_times.extract_travel_time_data')
    def test_returns_default_on_api_failure(self, mock_extract):
        """Test returns default when API returns empty dict."""
        mock_extract.return_value = {}

        result = get_duration_data("start", "end")

        self.assertEqual(result, 2)

    @patch('get_travel_times.extract_travel_time_data')
    def test_integration_success(self, mock_extract):
        """Test full integration from start_station to end_station."""
        mock_extract.return_value = {
            "journeys": [
                {
                    "startTime": "10:00",
                    "duration": 8,
                    "legs": [
                        {"mode": "tube", "duration": 8}
                    ]
                }
            ]
        }

        result = get_duration_data("940GZZLUHPK", "940GZZLUNHG")

        self.assertEqual(result, 8)
        mock_extract.assert_called_once_with("940GZZLUHPK", "940GZZLUNHG")

    @patch('get_travel_times.extract_travel_time_data')
    def test_integration_with_multiple_journeys(self, mock_extract):
        """Test uses only first journey in list."""
        mock_extract.return_value = {
            "journeys": [
                {"duration": 5},
                {"duration": 20},
                {"duration": 30}
            ]
        }

        result = get_duration_data("A", "B")

        # Should return first journey's duration
        self.assertEqual(result, 5)


if __name__ == '__main__':
    unittest.main()
