"""Tests for plot_networkx.py"""

import unittest
from unittest.mock import patch, MagicMock

import pandas as pd
import numpy as np
import networkx as nx
import folium

from plot_networkx import (
    create_colour_scheme,
    plot_station_network,
    extract_station_network_local,
    extract_station_data_local,
    validate_plot_inputs,
    create_base_map,
    create_line_feature_groups,
    format_station_popup,
    add_station_markers,
    get_edge_coordinates,
    add_network_edges
)


class TestExtractStationNetworkLocal(unittest.TestCase):
    """Test extract_station_network_local function."""

    @patch('plot_networkx.load_station_network_local')
    @patch('plot_networkx.ensure_files_exist')
    @patch('networkx.read_graphml')
    def test_ensures_files_and_reads_network(self, mock_read, mock_ensure, _mock_load):
        """Test that files are ensured before reading network."""
        mock_ensure.return_value = True
        mock_graph = MagicMock()
        mock_read.return_value = mock_graph

        result = extract_station_network_local("test_path.graphml")

        mock_ensure.assert_called_once()
        mock_read.assert_called_once_with("test_path.graphml")
        self.assertEqual(result, mock_graph)


class TestExtractStationDataLocal(unittest.TestCase):
    """Test extract_station_data_local function."""

    @patch('plot_networkx.load_station_network_local')
    @patch('plot_networkx.ensure_files_exist')
    @patch('pandas.read_csv')
    def test_ensures_files_and_reads_csv(self, mock_read_csv, mock_ensure, _mock_load):
        """Test that files are ensured before reading CSV."""
        mock_ensure.return_value = True
        mock_df = pd.DataFrame({'id': [1, 2]})
        mock_read_csv.return_value = mock_df

        result = extract_station_data_local("test_path.csv")

        mock_ensure.assert_called_once()
        mock_read_csv.assert_called_once_with("test_path.csv")
        pd.testing.assert_frame_equal(result, mock_df)


class TestCreateColourScheme(unittest.TestCase):
    """Test create_colour_scheme function."""

    def test_returns_dict(self):
        """Test that function returns a dictionary."""
        result = create_colour_scheme()
        self.assertIsInstance(result, dict)

    def test_contains_all_lines(self):
        """Test that all expected lines are in the scheme."""
        result = create_colour_scheme()
        expected_lines = [
            "bakerloo", "central", "circle", "district", "dlr", "elizabeth",
            "hammersmith-city", "jubilee", "metropolitan", "northern",
            "piccadilly", "victoria", "waterloo-city"
        ]
        for line in expected_lines:
            self.assertIn(line, result)

    def test_all_values_are_colors(self):
        """Test that all values are valid hex color strings."""
        result = create_colour_scheme()
        for color in result.values():
            # Check if it's a valid hex color (starts with # and has 6 hex digits)
            self.assertTrue(color.startswith(
                '#'), f"Color {color} is not hex format")
            self.assertEqual(
                len(color), 7, f"Color {color} has invalid length")

    def test_consistent_mapping(self):
        """Test that function returns consistent results."""
        result1 = create_colour_scheme()
        result2 = create_colour_scheme()
        self.assertEqual(result1, result2)


class TestPlotStationNetwork(unittest.TestCase):
    """Test plot_station_network function."""

    def setUp(self):
        """Set up test fixtures."""
        self.valid_station_data = pd.DataFrame({
            'UniqueId': ['A', 'B', 'C'],
            'Name': ['Station A', 'Station B', 'Station C'],
            'Latitude': [51.5, 51.6, 51.7],
            'Longitude': [-0.1, -0.2, -0.3],
            'Line_id': ['central', 'northern', 'circle']
        })

    @patch('plot_networkx.folium.Map')
    @patch('plot_networkx.folium.CircleMarker')
    def test_empty_station_data_raises_error(self, _mock_marker, _mock_map):
        """Test that empty station data raises ValueError."""
        empty_df = pd.DataFrame({'Latitude': [], 'Longitude': []})
        network = nx.MultiGraph()

        with self.assertRaises(ValueError) as context:
            plot_station_network(network, empty_df)

        self.assertIn("empty", str(context.exception).lower())

    @patch('plot_networkx.folium.Map')
    @patch('plot_networkx.folium.CircleMarker')
    def test_valid_data_returns_folium_map(self, _mock_marker, mock_map):
        """Test that valid data returns Folium map."""
        mock_map_instance = MagicMock()
        mock_map.return_value = mock_map_instance

        network = nx.MultiGraph()
        network.add_node('A')

        result = plot_station_network(network, self.valid_station_data)

        # Should return mock map (which is the return value of mock_map())
        self.assertEqual(result, mock_map_instance)

    @patch('plot_networkx.folium.Map')
    @patch('plot_networkx.folium.CircleMarker')
    def test_empty_network_with_valid_stations(self, _mock_marker, mock_map):
        """Test that empty network with valid stations still works."""
        mock_map_instance = MagicMock()
        mock_map.return_value = mock_map_instance

        network = nx.MultiGraph()  # Empty network
        result = plot_station_network(network, self.valid_station_data)

        # Should still return map (logs warning but doesn't fail)
        self.assertEqual(result, mock_map_instance)

    @patch('plot_networkx.folium.Map')
    @patch('plot_networkx.folium.CircleMarker')
    def test_calculates_map_center(self, _mock_marker, mock_map):
        """Test that map center is calculated from station data."""
        mock_map_instance = MagicMock()
        mock_map.return_value = mock_map_instance

        network = nx.MultiGraph()
        plot_station_network(network, self.valid_station_data)

        # Should call Map with center location (mean of lat/lon)
        expected_lat = self.valid_station_data['Latitude'].mean()
        expected_lon = self.valid_station_data['Longitude'].mean()
        mock_map.assert_called_once_with(
            location=[expected_lat, expected_lon],
            zoom_start=12
        )

    @patch('plot_networkx.folium.Map')
    @patch('plot_networkx.folium.CircleMarker')
    def test_adds_station_markers(self, mock_marker, mock_map):
        """Test that station markers are added."""
        mock_map_instance = MagicMock()
        mock_map.return_value = mock_map_instance
        mock_marker_instance = MagicMock()
        mock_marker.return_value = mock_marker_instance

        network = nx.MultiGraph()
        plot_station_network(network, self.valid_station_data)

        # Should create 3 markers (one for each station)
        self.assertEqual(mock_marker.call_count, 3)

    @patch('plot_networkx.folium.Map')
    @patch('plot_networkx.folium.CircleMarker')
    def test_skips_stations_with_nan_coordinates(self, mock_marker, mock_map):
        """Test that stations with NaN coordinates are skipped."""
        mock_map_instance = MagicMock()
        mock_map.return_value = mock_map_instance
        mock_marker_instance = MagicMock()
        mock_marker.return_value = mock_marker_instance

        station_data = pd.DataFrame({
            'UniqueId': ['A', 'B', 'C'],
            'Name': ['Station A', 'Station B', 'Station C'],
            'Latitude': [51.5, np.nan, 51.7],
            'Longitude': [-0.1, -0.2, -0.3],
            'Line_id': ['central', 'northern', 'circle']
        })

        network = nx.MultiGraph()
        plot_station_network(network, station_data)

        # Should create markers only for valid stations (2 instead of 3)
        self.assertEqual(mock_marker.call_count, 2)

    @patch('plot_networkx.folium.Map')
    @patch('plot_networkx.folium.CircleMarker')
    @patch('plot_networkx.folium.PolyLine')
    def test_adds_edges_to_map(self, mock_polyline, mock_marker, mock_map):
        """Test that edges are added to map."""
        mock_map_instance = MagicMock()
        mock_map.return_value = mock_map_instance
        mock_marker_instance = MagicMock()
        mock_marker.return_value = mock_marker_instance
        mock_polyline_instance = MagicMock()
        mock_polyline.return_value = mock_polyline_instance

        network = nx.MultiGraph()
        network.add_edge('A', 'B', line_id='northern', duration=5)

        plot_station_network(network, self.valid_station_data)

        # Should create 1 polyline for the edge
        mock_polyline.assert_called_once()

    @patch('plot_networkx.folium.Map')
    @patch('plot_networkx.folium.CircleMarker')
    @patch('plot_networkx.folium.PolyLine')
    def test_edge_gets_correct_color(self, mock_polyline, mock_marker, mock_map):
        """Test that edges get the correct color from scheme."""
        mock_map_instance = MagicMock()
        mock_map.return_value = mock_map_instance
        mock_marker_instance = MagicMock()
        mock_marker.return_value = mock_marker_instance
        mock_polyline_instance = MagicMock()
        mock_polyline.return_value = mock_polyline_instance

        network = nx.MultiGraph()
        network.add_edge('A', 'B', line_id='central', duration=5)

        plot_station_network(network, self.valid_station_data)

        # Central line should be #dc241f (hex for red)
        call_args = mock_polyline.call_args
        self.assertEqual(call_args[1]['color'], '#dc241f')

    @patch('plot_networkx.folium.Map')
    @patch('plot_networkx.folium.CircleMarker')
    @patch('plot_networkx.folium.PolyLine')
    def test_unknown_line_gets_default_color(self, mock_polyline, mock_marker, mock_map):
        """Test that unknown line IDs get default black color."""
        mock_map_instance = MagicMock()
        mock_map.return_value = mock_map_instance
        mock_marker_instance = MagicMock()
        mock_marker.return_value = mock_marker_instance
        mock_polyline_instance = MagicMock()
        mock_polyline.return_value = mock_polyline_instance

        network = nx.MultiGraph()
        network.add_edge('A', 'B', line_id='unknown-line', duration=5)

        plot_station_network(network, self.valid_station_data)

        # Unknown line should default to black
        call_args = mock_polyline.call_args
        self.assertEqual(call_args[1]['color'], 'black')

    @patch('plot_networkx.folium.Map')
    @patch('plot_networkx.folium.CircleMarker')
    @patch('plot_networkx.folium.PolyLine')
    def test_skips_edges_with_missing_stations(self, mock_polyline, mock_marker, mock_map):
        """Test that edges with missing station IDs are skipped."""
        mock_map_instance = MagicMock()
        mock_map.return_value = mock_map_instance
        mock_marker_instance = MagicMock()
        mock_marker.return_value = mock_marker_instance
        mock_polyline_instance = MagicMock()
        mock_polyline.return_value = mock_polyline_instance

        network = nx.MultiGraph()
        # Add edge to stations that don't exist in station_data
        network.add_edge('X', 'Y', line_id='central', duration=5)

        plot_station_network(network, self.valid_station_data)

        # Should not create polyline since stations are missing
        mock_polyline.assert_not_called()

    @patch('plot_networkx.folium.Map')
    @patch('plot_networkx.folium.CircleMarker')
    @patch('plot_networkx.folium.PolyLine')
    def test_multiple_edges(self, mock_polyline, mock_marker, mock_map):
        """Test adding multiple edges."""
        mock_map_instance = MagicMock()
        mock_map.return_value = mock_map_instance
        mock_marker_instance = MagicMock()
        mock_marker.return_value = mock_marker_instance
        mock_polyline_instance = MagicMock()
        mock_polyline.return_value = mock_polyline_instance

        network = nx.MultiGraph()
        network.add_edge('A', 'B', line_id='central', duration=5)
        network.add_edge('B', 'C', line_id='northern', duration=3)

        plot_station_network(network, self.valid_station_data)

        # Should create 2 polylines
        self.assertEqual(mock_polyline.call_count, 2)

    @patch('plot_networkx.folium.Map')
    @patch('plot_networkx.folium.CircleMarker')
    @patch('plot_networkx.folium.PolyLine')
    def test_polyline_coordinates(self, mock_polyline, mock_marker, mock_map):
        """Test that polyline coordinates are correct."""
        mock_map_instance = MagicMock()
        mock_map.return_value = mock_map_instance
        mock_marker_instance = MagicMock()
        mock_marker.return_value = mock_marker_instance
        mock_polyline_instance = MagicMock()
        mock_polyline.return_value = mock_polyline_instance

        network = nx.MultiGraph()
        network.add_edge('A', 'B', line_id='central', duration=5)

        plot_station_network(network, self.valid_station_data)

        # Check that coordinates are passed correctly
        call_args = mock_polyline.call_args[0][0]
        expected_coords = [
            [51.5, -0.1],  # Station A
            [51.6, -0.2]   # Station B
        ]
        self.assertEqual(call_args, expected_coords)


class TestValidatePlotInputs(unittest.TestCase):
    """Test validate_plot_inputs function."""

    def test_raises_error_on_empty_station_data(self):
        """Test that empty station data raises ValueError."""
        with self.assertRaises(ValueError):
            validate_plot_inputs(pd.DataFrame(), nx.MultiGraph())

    def test_passes_with_valid_data(self):
        """Test that valid data passes validation."""
        station_data = pd.DataFrame(
            {'UniqueId': ['A'], 'Latitude': [51.5], 'Longitude': [-0.1]})
        network = nx.MultiGraph()
        network.add_node('A')
        validate_plot_inputs(station_data, network)


class TestCreateBaseMap(unittest.TestCase):
    """Test create_base_map function."""

    def test_returns_folium_map_with_correct_center(self):
        """Test that map is created with correct center."""
        station_data = pd.DataFrame({
            'Latitude': [51.0, 52.0],
            'Longitude': [-0.5, 0.5]
        })
        result = create_base_map(station_data)
        self.assertEqual(result.location[0], 51.5)
        self.assertEqual(result.location[1], 0.0)


class TestCreateLineFeatureGroups(unittest.TestCase):
    """Test create_line_feature_groups function."""

    def test_creates_group_per_unique_line(self):
        """Test that one feature group is created per unique line."""
        station_data = pd.DataFrame(
            {'Line_id': ['central', 'central', 'northern']})
        base_map = folium.Map(location=[51.5, -0.1])
        result = create_line_feature_groups(station_data, base_map)
        self.assertEqual(len(result), 2)
        self.assertIn('central', result)
        self.assertIn('northern', result)

    def test_skips_nan_line_ids(self):
        """Test that NaN line IDs are skipped."""
        station_data = pd.DataFrame({'Line_id': ['central', np.nan]})
        base_map = folium.Map(location=[51.5, -0.1])
        result = create_line_feature_groups(station_data, base_map)
        self.assertEqual(len(result), 1)


class TestFormatStationPopup(unittest.TestCase):
    """Test format_station_popup function."""

    def test_includes_station_name_and_lines(self):
        """Test that popup includes station name and lines."""
        station_data = pd.DataFrame({
            'UniqueId': ['A', 'A'],
            'Name': ['Earl\'s Court', 'Earl\'s Court'],
            'Line_id': ['district', 'piccadilly']
        })
        row = station_data.iloc[0]
        result = format_station_popup(row, station_data)
        self.assertIn('Earl', result)
        self.assertIn('District', result)
        self.assertIn('Piccadilly', result)


class TestGetEdgeCoordinates(unittest.TestCase):
    """Test get_edge_coordinates function."""

    def setUp(self):
        """Set up test fixtures."""
        self.station_data = pd.DataFrame({
            'UniqueId': ['A', 'B'],
            'Latitude': [51.5, 51.6],
            'Longitude': [-0.1, -0.2]
        })

    def test_returns_correct_coordinates(self):
        """Test that coordinates are correct."""
        result = get_edge_coordinates('A', 'B', self.station_data)
        self.assertEqual(result, [[51.5, -0.1], [51.6, -0.2]])

    def test_returns_none_for_missing_stations(self):
        """Test that None is returned for missing stations."""
        self.assertIsNone(get_edge_coordinates('X', 'B', self.station_data))
        self.assertIsNone(get_edge_coordinates('A', 'Z', self.station_data))

    def test_returns_none_for_nan_coordinates(self):
        """Test that None is returned with NaN coordinates."""
        station_data = pd.DataFrame({
            'UniqueId': ['A', 'B'],
            'Latitude': [51.5, np.nan],
            'Longitude': [-0.1, -0.2]
        })
        self.assertIsNone(get_edge_coordinates('A', 'B', station_data))


class TestAddStationMarkers(unittest.TestCase):
    """Test add_station_markers function."""

    @patch('plot_networkx.folium.CircleMarker')
    def test_adds_markers_and_skips_nan(self, mock_marker):
        """Test that markers are added and NaN coordinates skipped."""
        station_data = pd.DataFrame({
            'UniqueId': ['A', 'B'],
            'Name': ['Station A', 'Station B'],
            'Latitude': [51.5, np.nan],
            'Longitude': [-0.1, -0.2],
            'Line_id': ['central', 'northern']
        })
        base_map = folium.Map(location=[51.5, -0.1])
        color_scheme = create_colour_scheme()

        add_station_markers(station_data, base_map, color_scheme)
        self.assertEqual(mock_marker.call_count, 1)


class TestAddNetworkEdges(unittest.TestCase):
    """Test add_network_edges function."""

    @patch('plot_networkx.folium.PolyLine')
    def test_adds_polylines_and_skips_missing(self, mock_polyline):
        """Test that polylines are added and missing stations skipped."""
        station_data = pd.DataFrame({
            'UniqueId': ['A', 'B'],
            'Latitude': [51.5, 51.6],
            'Longitude': [-0.1, -0.2],
            'Line_id': ['central', 'northern']
        })
        network = nx.MultiGraph()
        network.add_edge('A', 'B', line_id='central', duration=5)
        network.add_edge('X', 'Y', line_id='central', duration=5)

        base_map = folium.Map(location=[51.5, -0.1])
        color_scheme = create_colour_scheme()
        line_groups = create_line_feature_groups(station_data, base_map)

        add_network_edges(network, station_data, base_map,
                          line_groups, color_scheme)
        self.assertEqual(mock_polyline.call_count, 1)

    @patch('plot_networkx.folium.PolyLine')
    def test_handles_multiple_edges_same_nodes(self, mock_polyline):
        """Test that multiple edges between same nodes are handled."""
        station_data = pd.DataFrame({
            'UniqueId': ['A', 'B'],
            'Latitude': [51.5, 51.6],
            'Longitude': [-0.1, -0.2],
            'Line_id': ['central', 'northern']
        })
        network = nx.MultiGraph()
        network.add_edge('A', 'B', key=0, line_id='central', duration=5)
        network.add_edge('A', 'B', key=1, line_id='northern', duration=3)

        base_map = folium.Map(location=[51.5, -0.1])
        color_scheme = create_colour_scheme()
        line_groups = create_line_feature_groups(station_data, base_map)

        add_network_edges(network, station_data, base_map,
                          line_groups, color_scheme)
        self.assertEqual(mock_polyline.call_count, 2)


if __name__ == '__main__':
    unittest.main()
