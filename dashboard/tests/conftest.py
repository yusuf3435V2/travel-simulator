"""Shared fixtures for dashboard tests."""

import sys
import geopandas as gpd
from pathlib import Path

import pandas as pd
import pytest

DASHBOARD_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DASHBOARD_DIR))


# Fixtures for test_coverage_context.py


@pytest.fixture
def sample_stations_df_with_unique_id():
    """Sample stations DataFrame with UniqueId (for test_coverage_context.py)."""
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


# Fixtures for test_df_analysis.py


@pytest.fixture
def comparison_df_df_analysis():
    """Comparison DataFrame for test_df_analysis.py."""
    return pd.DataFrame(
        [
            {
                "route_id": 1,
                "nearest_station_baseline": "A",
                "alighting_station_baseline": "B",
                "nearest_station_altered": "User Station",
                "alighting_station_altered": "B",
                "time_spent_diff": -5.0,
            },
            {
                "route_id": 2,
                "nearest_station_baseline": "B",
                "alighting_station_baseline": "A",
                "nearest_station_altered": "B",
                "alighting_station_altered": "User Station",
                "time_spent_diff": -3.0,
            },
            {
                "route_id": 3,
                "nearest_station_baseline": "A",
                "alighting_station_baseline": "C",
                "nearest_station_altered": "A",
                "alighting_station_altered": "C",
                "time_spent_diff": 2.0,
            },
        ]
    )


# Fixtures for test_folium_functions.py


@pytest.fixture
def comparison_df_folium():
    """Comparison DataFrame for test_folium_functions.py."""
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
    """Station data for test_folium_functions.py."""
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


# Fixtures for test_kml_export.py


@pytest.fixture
def sample_stations_df_kml():
    """Sample stations DataFrame for test_kml_export.py."""
    return pd.DataFrame(
        [
            {
                "Name": "Near Station",
                "Latitude": 51.5075,
                "Longitude": -0.1279,
                "Line_id": "bakerloo",
            },
            {
                "Name": "Far Station",
                "Latitude": 51.7000,
                "Longitude": -0.3000,
                "Line_id": "central",
            },
        ]
    )


@pytest.fixture
def mock_load_stations(monkeypatch, sample_stations_df_kml):
    """Mock load_stations_from_s3 for test_kml_export.py."""
    import kml_export

    def fake_load_stations_from_s3(bucket_name, key):
        return sample_stations_df_kml

    monkeypatch.setattr(
        kml_export,
        "load_stations_from_s3",
        fake_load_stations_from_s3,
    )


# Fixtures for test_s3_utils.py


class FakeBody:
    """Fake S3 response body for testing."""

    def __init__(self, text):
        self.text = text

    def read(self):
        return self.text.encode("utf-8")


class FakeS3Client:
    """Fake S3 client for testing."""

    def __init__(self):
        self.objects = {}
        self.list_response = {}

    def get_object(self, Bucket, Key):
        if Key not in self.objects:
            raise Exception("Object not found")

        return {
            "Body": FakeBody(self.objects[Key]),
        }

    def list_objects_v2(self, Bucket, Prefix, Delimiter):
        return self.list_response


@pytest.fixture
def fake_s3(monkeypatch):
    """Fake S3 client fixture for test_s3_utils.py."""
    import s3_utils

    client = FakeS3Client()
    monkeypatch.setattr(s3_utils, "s3_client", client)
    return client
