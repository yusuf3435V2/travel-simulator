"""Tests for stations_choropleth.py"""

from stations_choropleth import (
    create_colour_scheme,
    create_line_feature_groups,
    format_station_popup,
    add_station_markers,
    get_edge_coordinates,
    add_network_edges,
    convert_stations_to_geodataframe,
    get_stations_per_boundary,
)
import unittest
from unittest.mock import patch, MagicMock
from io import BytesIO

import pandas as pd
import numpy as np
import networkx as nx
import folium
import geopandas as gpd
from shapely.geometry import box

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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


class TestConvertStationsToGeoDataFrame(unittest.TestCase):
    """Test convert_stations_to_geodataframe function."""

    def test_returns_geodataframe(self):
        """Test that function returns a GeoDataFrame."""
        station_data = pd.DataFrame({
            'Latitude': [51.5, 51.6],
            'Longitude': [-0.1, -0.2]
        })
        result = convert_stations_to_geodataframe(station_data)
        self.assertIsInstance(result, gpd.GeoDataFrame)

    def test_creates_point_geometry(self):
        """Test that point geometry is created correctly."""
        station_data = pd.DataFrame({
            'Latitude': [51.5, 51.6],
            'Longitude': [-0.1, -0.2]
        })
        result = convert_stations_to_geodataframe(station_data)
        self.assertTrue(
            all(geom.geom_type == 'Point' for geom in result.geometry))

    def test_preserves_data_columns(self):
        """Test that original data columns are preserved."""
        station_data = pd.DataFrame({
            'Name': ['Station A', 'Station B'],
            'Latitude': [51.5, 51.6],
            'Longitude': [-0.1, -0.2]
        })
        result = convert_stations_to_geodataframe(station_data)
        self.assertIn('Name', result.columns)
        self.assertIn('geometry', result.columns)


class TestGetStationsPerBoundary(unittest.TestCase):
    """Test get_stations_per_boundary function."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a simple boundary GeoDataFrame
        self.boundaries = gpd.GeoDataFrame(
            {'CTYUA25CD': ['E09000001', 'E09000002']},
            geometry=[
                box(0, 0, 1, 1),  # Small box
                box(1, 0, 2, 1)   # Adjacent box
            ],
            crs='EPSG:4326'
        )

        # Create stations within the first boundary
        self.stations = gpd.GeoDataFrame(
            {'Name': ['Station A', 'Station B']},
            geometry=gpd.points_from_xy([0.5, 1.5], [0.5, 0.5]),
            crs='EPSG:4326'
        )

    def test_returns_series(self):
        """Test that function returns a Series."""
        result = get_stations_per_boundary(self.boundaries, self.stations)
        self.assertIsInstance(result, pd.Series)

    def test_counts_stations_correctly(self):
        """Test that stations are counted correctly."""
        result = get_stations_per_boundary(self.boundaries, self.stations)
        # One station in first boundary (index 0)
        self.assertEqual(result.get(0, 0), 1)
        # One station in second boundary (index 1)
        self.assertEqual(result.get(1, 0), 1)


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

    def test_feature_groups_are_folium_objects(self):
        """Test that created groups are FeatureGroup objects."""
        station_data = pd.DataFrame({'Line_id': ['central']})
        base_map = folium.Map(location=[51.5, -0.1])
        result = create_line_feature_groups(station_data, base_map)
        self.assertIsInstance(result['central'], folium.FeatureGroup)


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

    def test_formats_hyphens_in_name(self):
        """Test that hyphens in station name are replaced with spaces."""
        station_data = pd.DataFrame({
            'UniqueId': ['A'],
            'Name': ['Kings-Cross'],
            'Line_id': ['circle']
        })
        row = station_data.iloc[0]
        result = format_station_popup(row, station_data)
        self.assertIn('Kings Cross', result)

    def test_formats_hyphens_in_line_name(self):
        """Test that hyphens in line name are replaced with &."""
        station_data = pd.DataFrame({
            'UniqueId': ['A'],
            'Name': ['Station'],
            'Line_id': ['hammersmith-city']
        })
        row = station_data.iloc[0]
        result = format_station_popup(row, station_data)
        self.assertIn('Hammersmith & city', result)


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

    @patch('stations_choropleth.folium.CircleMarker')
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

    @patch('stations_choropleth.folium.CircleMarker')
    def test_uses_correct_colors(self, mock_marker):
        """Test that markers use correct colors from scheme."""
        station_data = pd.DataFrame({
            'UniqueId': ['A'],
            'Name': ['Station A'],
            'Latitude': [51.5],
            'Longitude': [-0.1],
            'Line_id': ['central']
        })
        base_map = folium.Map(location=[51.5, -0.1])
        color_scheme = create_colour_scheme()

        add_station_markers(station_data, base_map, color_scheme)

        # Check that CircleMarker was called with central line color
        call_args = mock_marker.call_args
        self.assertEqual(call_args[1]['color'], '#dc241f')  # Central line red


class TestAddNetworkEdges(unittest.TestCase):
    """Test add_network_edges function."""

    @patch('stations_choropleth.folium.PolyLine')
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
        # Only 1 polyline since X-Y stations don't exist
        self.assertEqual(mock_polyline.call_count, 1)

    @patch('stations_choropleth.folium.PolyLine')
    def test_skips_edges_not_in_color_scheme(self, mock_polyline):
        """Test that edges with unknown line IDs are skipped."""
        station_data = pd.DataFrame({
            'UniqueId': ['A', 'B'],
            'Latitude': [51.5, 51.6],
            'Longitude': [-0.1, -0.2],
            'Line_id': ['central', 'northern']
        })
        network = nx.MultiGraph()
        network.add_edge('A', 'B', line_id='unknown-line', duration=5)

        base_map = folium.Map(location=[51.5, -0.1])
        color_scheme = create_colour_scheme()
        line_groups = create_line_feature_groups(station_data, base_map)

        add_network_edges(network, station_data, base_map,
                          line_groups, color_scheme)
        # Unknown line should not create polyline
        mock_polyline.assert_not_called()

    @patch('stations_choropleth.folium.PolyLine')
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
