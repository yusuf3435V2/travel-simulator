"""Tests for create_stations_network.py"""

from create_stations_network import (
    add_edge_between_stations,
    get_stops_from_line,
    create_station_network,
    track_network_creation_time,
    pipeline
)
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

import pandas as pd
import networkx as nx

sys.path.insert(0, os.path.dirname(__file__))


class TestAddEdgeBetweenStations(unittest.TestCase):
    """Test add_edge_between_stations function."""

    def test_adds_edge_with_attributes(self):
        """Test that edge is added with correct attributes."""
        network = nx.Graph()

        add_edge_between_stations(network, "A", "B", "line1", 5)

        self.assertTrue(network.has_edge("A", "B"))
        edge_data = network.get_edge_data("A", "B")
        self.assertEqual(edge_data['line_id'], "line1")
        self.assertEqual(edge_data['duration'], 5)

    def test_adds_multiple_edges(self):
        """Test adding multiple edges."""
        network = nx.Graph()

        add_edge_between_stations(network, "A", "B", "line1", 5)
        add_edge_between_stations(network, "B", "C", "line1", 3)
        add_edge_between_stations(network, "C", "D", "line2", 4)

        self.assertEqual(network.number_of_edges(), 3)

    def test_overwrites_existing_edge(self):
        """Test that adding edge twice overwrites attributes."""
        network = nx.Graph()

        add_edge_between_stations(network, "A", "B", "line1", 5)
        add_edge_between_stations(network, "A", "B", "line2", 10)

        edge_data = network.get_edge_data("A", "B")
        self.assertEqual(edge_data['line_id'], "line2")
        self.assertEqual(edge_data['duration'], 10)


class TestGetStopsFromLine(unittest.TestCase):
    """Test get_stops_from_line function."""

    def test_extracts_stations_from_valid_data(self):
        """Test extraction of stations from valid line data."""
        line_data = {
            "stopPointSequences": [
                {
                    "stopPoint": [
                        {
                            "stationId": "940GZZLUHPK",
                            "name": "King's Cross St. Pancras",
                            "lat": 51.5308,
                            "lon": -0.1119
                        },
                        {
                            "stationId": "940GZZLUNHG",
                            "name": "Northern",
                            "lat": 51.5220,
                            "lon": -0.1200
                        }
                    ]
                }
            ]
        }

        result = get_stops_from_line(line_data, "northern")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["UniqueId"], "940GZZLUHPK")
        self.assertEqual(result[0]["Name"], "King's Cross St. Pancras")
        self.assertEqual(result[0]["Line_id"], "northern")

    def test_handles_missing_station_id(self):
        """Test that stops without stationId are skipped."""
        line_data = {
            "stopPointSequences": [
                {
                    "stopPoint": [
                        {"name": "Invalid Stop"},  # Missing stationId
                        {"stationId": "940GZZLUHPK", "name": "Valid Stop"}
                    ]
                }
            ]
        }

        result = get_stops_from_line(line_data, "line1")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["UniqueId"], "940GZZLUHPK")

    def test_deduplicates_stations(self):
        """Test that duplicate stations are only added once."""
        line_data = {
            "stopPointSequences": [
                {
                    "stopPoint": [
                        {"stationId": "A", "name": "Station A"},
                        {"stationId": "B", "name": "Station B"}
                    ]
                },
                {
                    "stopPoint": [
                        {"stationId": "A", "name": "Station A"},
                        {"stationId": "C", "name": "Station C"}
                    ]
                }
            ]
        }

        result = get_stops_from_line(line_data, "line1")

        self.assertEqual(len(result), 3)
        station_ids = [s["UniqueId"] for s in result]
        self.assertEqual(station_ids.count("A"), 1)

    def test_handles_missing_coordinates(self):
        """Test handling when lat/lon are missing."""
        line_data = {
            "stopPointSequences": [
                {
                    "stopPoint": [
                        {"stationId": "A", "name": "Station A"}
                    ]
                }
            ]
        }

        result = get_stops_from_line(line_data, "line1")

        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0]["Latitude"])

    def test_uses_station_id_as_fallback_name(self):
        """Test that stationId is used as name if name is missing."""
        line_data = {
            "stopPointSequences": [
                {
                    "stopPoint": [
                        {"stationId": "940GZZLUHPK"}
                    ]
                }
            ]
        }

        result = get_stops_from_line(line_data, "line1")

        self.assertEqual(result[0]["Name"], "940GZZLUHPK")

    def test_returns_empty_list_for_invalid_data(self):
        """Test that empty list is returned for invalid data."""
        result = get_stops_from_line({}, "line1")
        self.assertEqual(result, [])

        result = get_stops_from_line({"stopPointSequences": []}, "line1")
        self.assertEqual(result, [])

    def test_multiple_sequences(self):
        """Test extraction from multiple stopPointSequences."""
        line_data = {
            "stopPointSequences": [
                {"stopPoint": [{"stationId": "A", "name": "A"}]},
                {"stopPoint": [{"stationId": "B", "name": "B"}]},
                {"stopPoint": [{"stationId": "C", "name": "C"}]}
            ]
        }

        result = get_stops_from_line(line_data, "line1")

        self.assertEqual(len(result), 3)


class TestCreateStationNetwork(unittest.TestCase):
    """Test create_station_network function."""

    @patch('create_stations_network.get_lines')
    @patch('create_stations_network.get_line_stops_data')
    @patch('create_stations_network.get_sequenced_stops')
    @patch('create_stations_network.get_duration_data')
    @patch('networkx.write_graphml')
    @patch.object(pd.DataFrame, 'to_csv')
    def test_returns_dict_with_network_and_stops(
            self, _mock_to_csv, _mock_write, mock_duration, mock_seq, mock_stops_data, mock_lines):
        """Test that create_station_network returns dict with network and stops_df."""
        mock_lines.return_value = ["line1"]
        mock_stops_data.return_value = {
            "stopPointSequences": [
                {"stopPoint": [{"stationId": "A", "name": "A"}]}
            ]
        }
        mock_seq.return_value = [["A", "B"]]
        mock_duration.return_value = 5

        result = create_station_network()

        self.assertIn('network', result)
        self.assertIn('stops_df', result)
        self.assertIsInstance(result['network'], nx.Graph)
        self.assertIsInstance(result['stops_df'], pd.DataFrame)

    @patch('create_stations_network.get_lines')
    def test_handles_empty_lines_list(self, mock_lines):
        """Test handling when no lines are returned."""
        mock_lines.return_value = []

        result = create_station_network()

        self.assertEqual(result['network'].number_of_nodes(), 0)
        self.assertEqual(len(result['stops_df']), 0)


class TestTrackNetworkCreationTime(unittest.TestCase):
    """Test track_network_creation_time function."""

    @patch('create_stations_network.create_station_network')
    @patch('time.time')
    def test_track_network_creation_time(self, mock_time, mock_create):
        """Test timing of network creation."""
        mock_time.side_effect = [100.0, 105.5]  # 5.5 seconds
        mock_create.return_value = {
            'network': nx.Graph(), 'stops_df': pd.DataFrame()}

        track_network_creation_time()

        mock_create.assert_called_once()
        mock_time.assert_called()

    @patch('create_stations_network.create_station_network')
    @patch('time.time')
    def test_track_network_creation_time_measures_duration(self, mock_time, mock_create):
        """Test that timing measures the duration correctly."""
        mock_time.side_effect = [1000.0, 1010.5]  # 10.5 seconds
        mock_create.return_value = {
            'network': nx.Graph(), 'stops_df': pd.DataFrame()}

        track_network_creation_time()

        # Verify time.time was called twice (start and end)
        self.assertEqual(mock_time.call_count, 2)

    @patch('create_stations_network.create_station_network')
    @patch('time.time')
    def test_track_network_creation_time_calls_create(self, mock_time, mock_create):
        """Test that create_station_network is called."""
        mock_time.side_effect = [100.0, 101.0]
        mock_create.return_value = {
            'network': nx.Graph(), 'stops_df': pd.DataFrame()}

        track_network_creation_time()

        mock_create.assert_called_once_with()


class TestPipeline(unittest.TestCase):
    """Test pipeline function."""

    @patch.dict(os.environ, {
        'AWS_DEFAULT_REGION': 'eu-west-2',
        'AWS_ACCESS_KEY_ID': 'test-key',
        'AWS_SECRET_ACCESS_KEY': 'test-secret'
    })
    @patch('create_stations_network.boto3.Session')
    @patch('create_stations_network.create_station_network')
    def test_pipeline_uploads_to_s3(self, mock_create, mock_session):
        """Test that pipeline uploads network and data to S3."""
        mock_network = nx.Graph()
        mock_df = pd.DataFrame({'id': [1, 2]})
        mock_create.return_value = {
            'network': mock_network, 'stops_df': mock_df}

        mock_s3_client = MagicMock()
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.client.return_value = mock_s3_client

        result = pipeline()

        self.assertTrue(result)
        self.assertEqual(mock_s3_client.put_object.call_count, 2)

    @patch.dict(os.environ, {
        'AWS_DEFAULT_REGION': 'eu-west-2',
        'AWS_ACCESS_KEY_ID': 'test-key',
        'AWS_SECRET_ACCESS_KEY': 'test-secret'
    })
    @patch('create_stations_network.boto3.Session')
    @patch('create_stations_network.create_station_network')
    def test_pipeline_uses_processed_prefix(self, mock_create, mock_session):
        """Test that pipeline uploads to processed/ prefix in bucket."""
        mock_network = nx.Graph()
        mock_df = pd.DataFrame({'id': [1, 2]})
        mock_create.return_value = {
            'network': mock_network, 'stops_df': mock_df}

        mock_s3_client = MagicMock()
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.client.return_value = mock_s3_client

        pipeline()

        calls = mock_s3_client.put_object.call_args_list
        self.assertEqual(calls[0][1]['Key'], 'processed/tube_network.graphml')
        self.assertEqual(calls[1][1]['Key'], 'processed/stations.csv')

    @patch.dict(os.environ, {
        'AWS_DEFAULT_REGION': 'eu-west-2',
        'AWS_ACCESS_KEY_ID': 'test-key',
        'AWS_SECRET_ACCESS_KEY': 'test-secret'
    })
    @patch('create_stations_network.boto3.Session')
    @patch('create_stations_network.create_station_network')
    def test_pipeline_returns_false_on_exception(self, mock_create, mock_session):
        """Test that pipeline returns False on exception."""
        mock_create.side_effect = Exception("API error")
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance

        result = pipeline()

        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
