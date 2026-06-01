"""Tests for pure functions in dashboard/coverage_context.py."""

import sys
from pathlib import Path
import pandas as pd
import pytest

DASHBOARD_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DASHBOARD_DIR))

from coverage_context import create_coverage_context  # noqa: E402


@pytest.fixture
def sample_stations_df():
    return pd.DataFrame(
        [
            {
                "UniqueId": "station_1",
                "Name": "Near Station",
                "Latitude": 51.5075,
                "Longitude": -0.1279,
                "Line_id": "bakerloo",
            },
            {
                "UniqueId": "station_2",
                "Name": "Second Near Station",
                "Latitude": 51.5080,
                "Longitude": -0.1285,
                "Line_id": "northern",
            },
            {
                "UniqueId": "station_3",
                "Name": "Far Station",
                "Latitude": 51.6000,
                "Longitude": -0.2000,
                "Line_id": "central",
            },
        ]
    )


def test_create_coverage_context_returns_expected_keys(sample_stations_df):
    result = create_coverage_context(
        stations_df=sample_stations_df,
        proposed_lat=51.5074,
        proposed_lon=-0.1278,
        radius_m=800,
    )

    assert set(result.keys()) == {
        "stations_within_catchment",
        "nearest_station_name",
        "nearest_station_distance_m",
        "affected_lines",
        "coverage_level",
    }


def test_create_coverage_context_counts_stations_inside_catchment(sample_stations_df):
    result = create_coverage_context(
        stations_df=sample_stations_df,
        proposed_lat=51.5074,
        proposed_lon=-0.1278,
        radius_m=800,
    )

    assert result["stations_within_catchment"] == 2
    assert result["coverage_level"] == "Medium"


def test_create_coverage_context_finds_nearest_station(sample_stations_df):
    result = create_coverage_context(
        stations_df=sample_stations_df,
        proposed_lat=51.5074,
        proposed_lon=-0.1278,
        radius_m=800,
    )

    assert result["nearest_station_name"] == "Near Station"
    assert result["nearest_station_distance_m"] >= 0


def test_create_coverage_context_returns_affected_lines(sample_stations_df):
    result = create_coverage_context(
        stations_df=sample_stations_df,
        proposed_lat=51.5074,
        proposed_lon=-0.1278,
        radius_m=800,
    )

    assert sorted(result["affected_lines"]) == ["bakerloo", "northern"]


@pytest.mark.parametrize(
    "radius_m, expected_count, expected_level",
    [
        (5, 0, "Low"),
        (800, 2, "Medium"),
        (20000, 3, "High"),
    ],
)
def test_create_coverage_context_coverage_levels(
    sample_stations_df,
    radius_m,
    expected_count,
    expected_level,
):
    result = create_coverage_context(
        stations_df=sample_stations_df,
        proposed_lat=51.5074,
        proposed_lon=-0.1278,
        radius_m=radius_m,
    )

    assert result["stations_within_catchment"] == expected_count
    assert result["coverage_level"] == expected_level


def test_create_coverage_context_handles_duplicate_station_names():
    stations_df = pd.DataFrame(
        [
            {
                "UniqueId": "station_1",
                "Name": "Shared Station",
                "Latitude": 51.5075,
                "Longitude": -0.1279,
                "Line_id": "bakerloo",
            },
            {
                "UniqueId": "station_2",
                "Name": "Shared Station",
                "Latitude": 51.5076,
                "Longitude": -0.1280,
                "Line_id": "northern",
            },
        ]
    )

    result = create_coverage_context(
        stations_df=stations_df,
        proposed_lat=51.5074,
        proposed_lon=-0.1278,
        radius_m=800,
    )

    assert result["stations_within_catchment"] == 1
    assert sorted(result["affected_lines"]) == ["bakerloo", "northern"]


def test_create_coverage_context_raises_key_error_for_missing_columns():
    stations_df = pd.DataFrame(
        [
            {
                "Name": "Bad Station",
                "lat": 51.5075,
                "lon": -0.1279,
            }
        ]
    )

    with pytest.raises(KeyError):
        create_coverage_context(
            stations_df=stations_df,
            proposed_lat=51.5074,
            proposed_lon=-0.1278,
            radius_m=800,
        )
