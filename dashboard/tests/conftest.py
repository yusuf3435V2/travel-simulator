import sys
import os
import pytest
import pandas as pd


# Add parent directory to path to import modules from tfl_data_and_network
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import s3_utils
import kml_export


class FakeBody:
    def __init__(self, text):
        self.text = text

    def read(self):
        return self.text.encode("utf-8")


class FakeS3Client:
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
    client = FakeS3Client()
    monkeypatch.setattr(s3_utils, "s3_client", client)
    return client


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


@pytest.fixture
def comparison_df():
    return pd.DataFrame(
        [
            {
                "route_id": 1,
                "nearest_station_baseline": "Station A",
                "alighting_station_baseline": "Other",
                "nearest_station_altered": "User Station",
                "alighting_station_altered": "Other",
                "time_spent_diff": -5.0,
            },
            {
                "route_id": 2,
                "nearest_station_baseline": "Station B",
                "alighting_station_baseline": "Other",
                "nearest_station_altered": "User Station",
                "alighting_station_altered": "Other",
                "time_spent_diff": -3.0,
            },
            {
                "route_id": 3,
                "nearest_station_baseline": "Other",
                "alighting_station_baseline": "Other",
                "nearest_station_altered": "User Station",
                "alighting_station_altered": "Station A",
                "time_spent_diff": -3.0,
            },
            {
                "route_id": 4,
                "nearest_station_baseline": "Other",
                "alighting_station_baseline": "Other",
                "nearest_station_altered": "User Station",
                "alighting_station_altered": "Station C",
                "time_spent_diff": -1.0,
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


@pytest.fixture
def comparison_df_2():
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


@pytest.fixture
def mock_load_stations(monkeypatch, sample_stations_df):
    def fake_load_stations_from_s3(bucket_name, key):
        return sample_stations_df

    monkeypatch.setattr(
        kml_export,
        "load_stations_from_s3",
        fake_load_stations_from_s3,
    )


@pytest.fixture
def mock_load_stations_kml(monkeypatch):
    """Mock for kml_export tests with only 1 nearby station."""
    kml_stations_df = pd.DataFrame(
        [
            {
                "UniqueId": "station_1",
                "Name": "Near Station",
                "Latitude": 51.5075,
                "Longitude": -0.1279,
                "Line_id": "bakerloo",
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

    def fake_load_stations_from_s3(bucket_name, key):
        return kml_stations_df

    monkeypatch.setattr(
        kml_export,
        "load_stations_from_s3",
        fake_load_stations_from_s3,
    )


@pytest.fixture
def sample_stations_df_2():
    return pd.DataFrame(
        [
            {
                "Name": "Near Station",
                "Latitude": 51.5075,
                "Longitude": -0.1279,
                "Line_id": "bakerloo",
            },
            {
                "Name": "Second Near Station",
                "Latitude": 51.5080,
                "Longitude": -0.1285,
                "Line_id": "northern",
            },
        ]
    )
