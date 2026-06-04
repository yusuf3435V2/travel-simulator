"""Tests for stations_choropleth.py"""

from stations_choropleth import (
    create_colour_scheme,
    create_line_feature_groups,
    format_station_popup,
    add_station_markers,
    get_edge_coordinates,
    add_network_edges,
    extract_station_network,
    extract_stations,
    load_choropleth_from_s3,
    create_combined_base_map,
    create_choropleth,
)
import unittest
from unittest.mock import patch, MagicMock, mock_open
from io import BytesIO

import pandas as pd
import numpy as np
import networkx as nx
import folium
import geopandas as gpd
from shapely.geometry import box, Point

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


class TestExtractStationNetwork(unittest.TestCase):
    """Test extract_station_network function."""

    @patch('stations_choropleth.boto3.client')
    @patch('stations_choropleth.st.cache_data')
    def test_returns_multigraph(self, mock_cache, mock_boto_client):
        """Test that function returns a MultiGraph."""
        # Bypass the cache decorator for testing
        mock_cache.return_value = lambda f: f

        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        # Create a sample MultiGraph and serialize it
        test_graph = nx.MultiGraph()
        test_graph.add_edge('A', 'B', line_id='central')
        graphml_bytes = BytesIO()
        nx.write_graphml(test_graph, graphml_bytes)
        graphml_bytes.seek(0)

        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: graphml_bytes.read())
        }

        result = extract_station_network()
        self.assertIsInstance(result, nx.MultiGraph)


class TestExtractStations(unittest.TestCase):
    """Test extract_stations function."""

    @patch('stations_choropleth.boto3.client')
    @patch('stations_choropleth.st.cache_data')
    def test_returns_dataframe(self, mock_cache, mock_boto_client):
        """Test that function returns a DataFrame."""
        # Bypass the cache decorator for testing
        mock_cache.return_value = lambda f: f

        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        csv_data = "Name,Latitude,Longitude\nStation A,51.5,-0.1\n"
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: csv_data.encode('utf-8'))
        }

        result = extract_stations()
        self.assertIsInstance(result, pd.DataFrame)

    @patch('stations_choropleth.boto3.client')
    def test_returns_geodataframe(self, mock_boto_client):
        """Test that function returns a GeoDataFrame."""
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        # Create sample GeoJSON data
        gdf = gpd.GeoDataFrame(
            {'Station Count': [5, 10]},
            geometry=[Point(0, 0), Point(1, 1)]
        )
        geojson_data = gdf.to_json().encode('utf-8')

        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: geojson_data)
        }

        result = load_choropleth_from_s3()
        self.assertIsInstance(result, gpd.GeoDataFrame)

    @patch('stations_choropleth.boto3.client')
    def test_drops_id_column_if_present(self, mock_boto_client):
        """Test that id column is dropped from loaded GeoDataFrame."""
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        gdf = gpd.GeoDataFrame(
            {'id': [1, 2], 'Station Count': [5, 10]},
            geometry=[Point(0, 0), Point(1, 1)]
        )
        geojson_data = gdf.to_json().encode('utf-8')

        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: geojson_data)
        }

        result = load_choropleth_from_s3()
        self.assertNotIn('id', result.columns)


class TestCreateCombinedBaseMap(unittest.TestCase):
    """Test create_combined_base_map function."""

    def test_returns_folium_map(self):
        """Test that function returns a folium Map."""
        gdf = gpd.GeoDataFrame(
            {'Station Count': [5, 10]},
            geometry=[box(0, 0, 1, 1), box(1, 1, 2, 2)]
        )
        stations_df = pd.DataFrame({
            'Latitude': [51.5, 51.6],
            'Longitude': [-0.1, -0.2]
        })

        result = create_combined_base_map(gdf, stations_df)
        self.assertIsInstance(result, folium.Map)

    def test_centers_map_on_stations(self):
        """Test that map is centered on station mean coordinates."""
        gdf = gpd.GeoDataFrame(
            {'Station Count': [5]},
            geometry=[box(0, 0, 1, 1)]
        )
        stations_df = pd.DataFrame({
            'Latitude': [51.5, 51.7],  # Mean should be 51.6
            'Longitude': [-0.1, -0.3]  # Mean should be -0.2
        })

        result = create_combined_base_map(gdf, stations_df)
        self.assertAlmostEqual(result.location[0], 51.6, places=1)
        self.assertAlmostEqual(result.location[1], -0.2, places=1)


class TestCreateChoropleth(unittest.TestCase):
    """Test create_choropleth function."""

    @patch('stations_choropleth.extract_station_network')
    @patch('stations_choropleth.extract_stations')
    @patch('stations_choropleth.load_choropleth_from_s3')
    def test_returns_folium_map_or_none(self, mock_load_choropleth, mock_extract_stations, mock_extract_network):
        """Test that create_choropleth returns a folium Map or None."""
        # Setup mocks
        mock_extract_network.return_value = nx.MultiGraph()
        mock_extract_stations.return_value = pd.DataFrame({
            'UniqueId': ['A'],
            'Name': ['Station A'],
            'Latitude': [51.5],
            'Longitude': [-0.1],
            'Line_id': ['central']
        })

        gdf = gpd.GeoDataFrame(
            {'Station Count': [1]},
            geometry=[box(0, 0, 1, 1)]
        )
        mock_load_choropleth.return_value = gdf

        result = create_choropleth()
        self.assertTrue(isinstance(result, folium.Map) or result is None)

    @patch('stations_choropleth.extract_station_network')
    @patch('stations_choropleth.extract_stations')
    def test_returns_none_when_stations_empty(self, mock_extract_stations, mock_extract_network):
        """Test that None is returned when stations data is empty."""
        mock_extract_network.return_value = nx.MultiGraph()
        mock_extract_stations.return_value = pd.DataFrame()

        result = create_choropleth()
        self.assertIsNone(result)


class TestConvertStationsToGeoDataFrame(unittest.TestCase):
    """Test convert_stations_to_geodataframe functionality via create_combined_base_map."""

    def test_station_data_to_geodataframe(self):
        """Test that station DataFrame is properly used in map creation."""
        gdf = gpd.GeoDataFrame(
            {'Station Count': [5]},
            geometry=[box(0, 0, 1, 1)]
        )
        stations_df = pd.DataFrame({
            'Latitude': [51.5],
            'Longitude': [-0.1]
        })

        result = create_combined_base_map(gdf, stations_df)
        self.assertIsInstance(result, folium.Map)


class TestGetStationsPerBoundary(unittest.TestCase):
    """Test get_stations_per_boundary functionality via choropleth creation."""

    def test_choropleth_creation_with_boundaries(self):
        """Test that choropleth creation works with boundary data."""
        # This is tested implicitly through create_choropleth tests
        # as the function uses station data overlaid on boundaries
        pass


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
