"""Tests for get_sequenced_stops.py"""

import unittest
from unittest.mock import patch

from get_sequenced_stops import get_line_stops_data, get_sequenced_stops


class TestGetLineStopsData(unittest.TestCase):
    """Test get_line_stops_data function."""

    @patch('get_sequenced_stops.make_api_call_with_retry')
    def test_returns_api_response(self, mock_api_call):
        """Test that API response is returned directly."""
        expected_data = {
            "orderedLineRoutes": [
                {"naptanIds": ["940GZZLUHPK", "940GZZLUNHG"]}
            ]
        }
        mock_api_call.return_value = expected_data

        result = get_line_stops_data("bakerloo", "all")

        self.assertEqual(result, expected_data)
        mock_api_call.assert_called_once_with(
            "https://api.tfl.gov.uk/Line/bakerloo/Route/Sequence/all")

    @patch('get_sequenced_stops.make_api_call_with_retry')
    def test_url_construction_with_line_id_and_direction(self, mock_api_call):
        """Test URL is correctly constructed with line_id and direction."""
        mock_api_call.return_value = {}

        get_line_stops_data("central", "inbound")

        mock_api_call.assert_called_once_with(
            "https://api.tfl.gov.uk/Line/central/Route/Sequence/inbound")

    @patch('get_sequenced_stops.make_api_call_with_retry')
    def test_returns_empty_dict_on_api_failure(self, mock_api_call):
        """Test that empty dict from API is returned."""
        mock_api_call.return_value = {}

        result = get_line_stops_data("circle", "outbound")

        self.assertEqual(result, {})


class TestGetSequencedStops(unittest.TestCase):
    """Test get_sequenced_stops function."""

    def test_success_single_route(self):
        """Test successful extraction of single route stops."""
        data = {
            "orderedLineRoutes": [
                {"naptanIds": ["940GZZLUHPK", "940GZZLUNHG", "940GZZLULVT"]}
            ]
        }

        result = get_sequenced_stops(data)

        self.assertEqual(
            result, [["940GZZLUHPK", "940GZZLUNHG", "940GZZLULVT"]])

    def test_success_multiple_routes(self):
        """Test extraction of multiple route stops."""
        data = {
            "orderedLineRoutes": [
                {"naptanIds": ["940GZZLUHPK", "940GZZLUNHG"]},
                {"naptanIds": ["940GZZLULVT", "940GZZLUMDT"]},
                {"naptanIds": ["940GZZLOWBT", "940GZZLOEMB"]}
            ]
        }

        result = get_sequenced_stops(data)

        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], ["940GZZLUHPK", "940GZZLUNHG"])
        self.assertEqual(result[1], ["940GZZLULVT", "940GZZLUMDT"])
        self.assertEqual(result[2], ["940GZZLOWBT", "940GZZLOEMB"])

    def test_empty_ordered_line_routes(self):
        """Test with empty orderedLineRoutes."""
        data = {"orderedLineRoutes": []}

        result = get_sequenced_stops(data)

        self.assertEqual(result, [])

    def test_missing_ordered_line_routes_key(self):
        """Test when orderedLineRoutes key is missing."""
        data = {"someOtherKey": []}

        result = get_sequenced_stops(data)

        self.assertEqual(result, [])

    def test_input_is_not_dict(self):
        """Test when input is not a dict."""
        result = get_sequenced_stops([])

        self.assertEqual(result, [])

    def test_input_is_empty_dict(self):
        """Test when input is empty dict."""
        result = get_sequenced_stops({})

        self.assertEqual(result, [])

    def test_input_is_none(self):
        """Test when input is None."""
        result = get_sequenced_stops(None)

        self.assertEqual(result, [])

    def test_route_with_single_stop(self):
        """Test route with single stop."""
        data = {
            "orderedLineRoutes": [
                {"naptanIds": ["940GZZLUHPK"]}
            ]
        }

        result = get_sequenced_stops(data)

        self.assertEqual(result, [["940GZZLUHPK"]])

    def test_mixed_route_sizes(self):
        """Test multiple routes with different numbers of stops."""
        data = {
            "orderedLineRoutes": [
                {"naptanIds": ["A"]},
                {"naptanIds": ["B", "C", "D"]},
                {"naptanIds": ["E", "F"]}
            ]
        }

        result = get_sequenced_stops(data)

        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], ["A"])
        self.assertEqual(result[1], ["B", "C", "D"])
        self.assertEqual(result[2], ["E", "F"])

    def test_input_dict_with_extra_keys(self):
        """Test dict with orderedLineRoutes and other keys."""
        data = {
            "id": "bakerloo",
            "name": "Bakerloo",
            "orderedLineRoutes": [
                {"naptanIds": ["STOP1", "STOP2"]}
            ],
            "otherKey": "value"
        }

        result = get_sequenced_stops(data)

        self.assertEqual(result, [["STOP1", "STOP2"]])


if __name__ == '__main__':
    unittest.main()
