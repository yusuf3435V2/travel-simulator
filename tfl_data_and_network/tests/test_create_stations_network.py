"""Tests for create_stations_network.py"""

import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import os
import pandas as pd
import networkx as nx

sys.path.insert(0, os.path.dirname(__file__))

from create_stations_network import (
    add_edge_between_stations,
    get_stops_from_line,
    create_station_network,
    load_station_network,
    load_station_data
)


class TestAddEdgeBetweenStations(unittest.TestCase):
    """Test add_edge_between_stations function."""

    def test_adds_edge_with_attributes(self):
        """Test that edge is added with correct attributes."""
        G = nx.Graph()

        add_edge_between_stations(G, "A", "B", "line1", 5)

        self.assertTrue(G.has_edge("A", "B"))
        edge_data = G.get_edge_data("A", "B")
        self.assertEqual(edge_data['line_id'], "line1")
        self.assertEqual(edge_data['duration'], 5)

    def test_adds_multiple_edges(self):
        """Test adding multiple edges."""
        G = nx.Graph()

        add_edge_between_stations(G, "A", "B", "line1", 5)
        add_edge_between_stations(G, "B", "C", "line1", 3)
        add_edge_between_stations(G, "C", "D", "line2", 4)

        self.assertEqual(G.number_of_edges(), 3)

    def test_overwrites_existing_edge(self):
        """Test that adding edge twice overwrites attributes."""
        G = nx.Graph()

        add_edge_between_stations(G, "A", "B", "line1", 5)
        add_edge_between_stations(G, "A", "B", "line2", 10)

        edge_data = G.get_edge_data("A", "B")
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


class TestLoadStationNetwork(unittest.TestCase):
    """Test load_station_network function."""

    @patch('os.path.exists')
    @patch('networkx.read_graphml')
    def test_loads_existing_file(self, mock_read, mock_exists):
        """Test loading existing graphml file."""
        mock_exists.return_value = True
        mock_network = MagicMock()
        mock_read.return_value = mock_network

        result = load_station_network("test/path.graphml")

        self.assertEqual(result, mock_network)
        mock_read.assert_called_once_with("test/path.graphml")

    @patch('create_stations_network.create_station_network')
    @patch('os.path.exists')
    @patch('networkx.read_graphml')
    def test_creates_file_if_missing(self, mock_read, mock_exists, mock_create):
        """Test that file is created if missing."""
        mock_exists.return_value = False
        mock_network = MagicMock()
        mock_read.return_value = mock_network
        mock_create.return_value = {'network': mock_network, 'stops_df': pd.DataFrame()}

        result = load_station_network("missing/path.graphml")

        mock_create.assert_called_once_with(network_file_path="missing/path.graphml")

    @patch('os.path.exists')
    @patch('networkx.read_graphml')
    def test_default_file_path(self, mock_read, mock_exists):
        """Test default file path is used."""
        mock_exists.return_value = True
        mock_network = MagicMock()
        mock_read.return_value = mock_network

        load_station_network()

        mock_exists.assert_called_with("stations/tube_network.graphml")


class TestLoadStationData(unittest.TestCase):
    """Test load_station_data function."""

    @patch('os.path.exists')
    @patch('pandas.read_csv')
    def test_loads_existing_csv(self, mock_read_csv, mock_exists):
        """Test loading existing CSV file."""
        mock_exists.return_value = True
        mock_df = MagicMock()
        mock_read_csv.return_value = mock_df

        result = load_station_data("test/stations.csv")

        self.assertEqual(result, mock_df)
        mock_read_csv.assert_called_once_with("test/stations.csv")

    @patch('create_stations_network.create_station_network')
    @patch('os.path.exists')
    @patch('pandas.read_csv')
    def test_creates_file_if_missing(self, mock_read_csv, mock_exists, mock_create):
        """Test that file is created if missing."""
        mock_exists.return_value = False
        mock_df = pd.DataFrame()
        mock_read_csv.return_value = mock_df
        mock_create.return_value = {'stops_df': mock_df, 'network': MagicMock()}

        result = load_station_data("missing/stations.csv")

        mock_create.assert_called_once_with(station_file_path="missing/stations.csv")

    @patch('os.path.exists')
    @patch('pandas.read_csv')
    def test_default_file_path(self, mock_read_csv, mock_exists):
        """Test default file path is used."""
        mock_exists.return_value = True
        mock_df = MagicMock()
        mock_read_csv.return_value = mock_df

        load_station_data()

        mock_exists.assert_called_with("stations/Stations.csv")


class TestCreateStationNetwork(unittest.TestCase):
    """Test create_station_network function."""

    @patch('create_stations_network.get_lines')
    @patch('create_stations_network.get_line_stops_data')
    @patch('create_stations_network.get_sequenced_stops')
    @patch('create_stations_network.get_duration_data')
    @patch('networkx.write_graphml')
    @patch.object(pd.DataFrame, 'to_csv')
    def test_returns_dict_with_network_and_stops(
            self, mock_to_csv, mock_write, mock_duration, mock_seq, mock_stops_data, mock_lines):
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
    @patch('networkx.write_graphml')
    @patch.object(pd.DataFrame, 'to_csv')
    def test_saves_files(self, mock_to_csv, mock_write, mock_lines):
        """Test that files are saved."""
        mock_lines.return_value = []

        create_station_network("custom_network.graphml", "custom_stations.csv")

        mock_write.assert_called_once()
        mock_to_csv.assert_called_once()

    @patch('create_stations_network.get_lines')
    def test_handles_empty_lines_list(self, mock_lines):
        """Test handling when no lines are returned."""
        mock_lines.return_value = []

        with patch('networkx.write_graphml'):
            with patch.object(pd.DataFrame, 'to_csv'):
                result = create_station_network()

                self.assertEqual(result['network'].number_of_nodes(), 0)
                self.assertEqual(len(result['stops_df']), 0)


if __name__ == '__main__':
    unittest.main()
