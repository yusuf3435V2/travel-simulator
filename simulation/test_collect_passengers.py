"""Tests for collecting passengers at stations."""

from collect_passengers import (
    load_user_information,
    shortest_path_between_stations,
    shortest_path_length_between_stations,
    get_line_switches,
    total_switch_time,
    get_station_latlong,
    get_nearest_station,
)
import pytest
import pandas as pd
import networkx as nx
import json


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Fixture for sample passenger data."""
    return pd.read_csv("simulation/sample_passengers.csv")


@pytest.fixture
def sample_stations() -> nx.Graph:
    """Fixture for sample station graph (5 stations). With duration weight on each edge."""
    G = nx.Graph()
    G.add_edge("StationA", "StationB", duration=5, line="piccadilly")
    G.add_edge("StationB", "StationC", duration=10, line="piccadilly")
    G.add_edge("StationC", "StationD", duration=15, line="piccadilly")
    G.add_edge("StationD", "StationE", duration=20, line="piccadilly")
    G.add_edge("StationA", "StationC", duration=12, line="district")
    return G


@pytest.fixture
def sample_station_data() -> pd.DataFrame:
    """Fixture for sample station data."""
    data = pd.read_csv("stations/Stations.csv")
    return data


def test_get_station_latlong(sample_station_data):
    """Test that the latitude and longitude of a station are retrieved correctly."""
    latlong = get_station_latlong("940GZZLUBNK", sample_station_data)
    assert latlong == (51.513356, -0.088899), (
        f"Expected (51.5072, -0.1276), got {latlong}"
    )


def test_get_station_latlong_invalid_id(sample_station_data):
    """Test that None is returned when an invalid station ID is provided."""
    latlong = get_station_latlong("INVALID_ID", sample_station_data)
    assert latlong is None, f"Expected None, got {latlong}"


def test_shortest_path(sample_stations):
    """Test that the shortest path between two stations is calculated correctly."""
    path = shortest_path_between_stations(sample_stations, "StationA", "StationD")
    assert path == ["StationA", "StationB", "StationC", "StationD"], (
        f"Expected ['StationA', 'StationB', 'StationC', 'StationD'], got {path}"
    )


def test_get_nearest_station(sample_station_data):
    """Test that the nearest station to a given latitude and longitude is retrieved correctly."""
    nearest_station = get_nearest_station(51.513356, -0.088899, sample_station_data)
    assert nearest_station == "940GZZLUBNK", (
        f"Expected '940GZZLUBNK', got {nearest_station}"
    )


def test_shortest_path_no_path(sample_stations):
    """Test that the shortest path function returns an empty list when no path exists."""
    sample_stations.remove_edge("StationC", "StationD")  # Remove edge to create no path
    path = shortest_path_between_stations(sample_stations, "StationA", "StationD")
    assert path == [], f"Expected [], got {path}"


def test_shortest_path_length(sample_stations):
    """Test that the shortest path length between two stations is calculated correctly."""
    length = shortest_path_length_between_stations(
        sample_stations, "StationA", "StationD"
    )
    assert length == 27, f"Expected 27, got {length}"


def test_check_line_switches(sample_stations):
    """Test that line switches are correctly identified in a path."""
    path = ["StationA", "StationC", "StationD"]
    line_switches = get_line_switches(path, sample_stations)
    assert line_switches == [("StationC", "district", "piccadilly")], (
        f"Expected [('StationC', 'district', 'piccadilly')], got {line_switches}"
    )


def test_total_switch_time():
    """Test that total switch time is calculated correctly."""
    line_switches = [
        ("StationC", "district", "piccadilly"),
        ("StationD", "piccadilly", "district"),
    ]
    switch_time = 5
    total_time = total_switch_time(line_switches, switch_time)
    assert total_time == 10, f"Expected 10, got {total_time}"


def test_sample_data_valid_columns(sample_data):
    """Test that sample data contains the expected columns."""
    expected_columns = {
        "passenger_id",
        "origin_lat",
        "origin_lng",
        "destination_lat",
        "destination_lng",
        "day_type",
    }
    for column in expected_columns:
        assert column in sample_data.columns, f"Missing expected column: {column}"
