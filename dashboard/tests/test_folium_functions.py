"""Tests for dashboard/folium_functions.py."""

import sys
from pathlib import Path

import folium
import pandas as pd
import pytest

DASHBOARD_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DASHBOARD_DIR))

from folium_functions import (  # noqa: E402
    create_folium_map,
    find_station_demand_changes,
    plot_original_station_point,
)


@pytest.fixture
def comparison_df():
    return pd.DataFrame(
        [
            {
                "nearest_station_baseline": "Station A",
                "alighting_station_altered": "Station B",
                "time_spent_diff": -5.0,
            },
            {
                "nearest_station_baseline": "Station B",
                "alighting_station_altered": "Station C",
                "time_spent_diff": 2.0,
            },
            {
                "nearest_station_baseline": "Station A",
                "alighting_station_altered": "Station C",
                "time_spent_diff": -3.0,
            },
        ]
    )


@pytest.fixture
def station_data():
    return pd.DataFrame(
        [
            {
                "Name": "Station A",
                "Latitude": 51.500,
                "Longitude": -0.100,
            },
            {
                "Name": "Station B",
                "Latitude": 51.510,
                "Longitude": -0.110,
            },
            {
                "Name": "Station C",
                "Latitude": 51.520,
                "Longitude": -0.120,
            },
        ]
    )


def test_find_station_demand_changes_returns_empty_for_empty_dataframe():
    result = find_station_demand_changes(pd.DataFrame())

    assert result.empty


def test_find_station_demand_changes_sums_station_impacts(comparison_df):
    result = find_station_demand_changes(comparison_df)

    assert set(result.columns) == {
        "Station",
        "Total Time Spent Difference",
    }

    station_a_value = result.loc[
        result["Station"] == "Station A",
        "Total Time Spent Difference",
    ].iloc[0]

    station_b_value = result.loc[
        result["Station"] == "Station B",
        "Total Time Spent Difference",
    ].iloc[0]

    station_c_value = result.loc[
        result["Station"] == "Station C",
        "Total Time Spent Difference",
    ].iloc[0]

    assert station_a_value == -8.0
    assert station_b_value == -3.0
    assert station_c_value == -1.0


def test_plot_original_station_point_adds_marker_and_catchment():
    metadata = {
        "Latitude": 51.5074,
        "Longitude": -0.1278,
    }

    m = folium.Map(location=[51.5074, -0.1278], zoom_start=12)

    result = plot_original_station_point(metadata, m)

    html = result.get_root().render()

    assert isinstance(result, folium.Map)
    assert "Proposed Station" in html
    assert "800m walking catchment" in html


def test_plot_original_station_point_missing_latitude_returns_same_map():
    metadata = {
        "Longitude": -0.1278,
    }

    m = folium.Map(location=[51.5074, -0.1278], zoom_start=12)

    result = plot_original_station_point(metadata, m)

    assert result is m


def test_plot_original_station_point_missing_longitude_returns_same_map():
    metadata = {
        "Latitude": 51.5074,
    }

    m = folium.Map(location=[51.5074, -0.1278], zoom_start=12)

    result = plot_original_station_point(metadata, m)

    assert result is m


def test_create_folium_map_returns_folium_map(station_data, comparison_df):
    result = create_folium_map(station_data, comparison_df)

    assert isinstance(result, folium.Map)


def test_create_folium_map_contains_station_names(station_data, comparison_df):
    result = create_folium_map(station_data, comparison_df)

    html = result.get_root().render()

    assert "Station A" in html
    assert "Station B" in html
    assert "Station C" in html


def test_create_folium_map_contains_time_spent_difference_text(
    station_data,
    comparison_df,
):
    result = create_folium_map(station_data, comparison_df)

    html = result.get_root().render()

    assert "Time Spent Difference" in html
