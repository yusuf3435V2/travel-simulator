"""Tests for dashboard/s3_utils.py."""

import io
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

DASHBOARD_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DASHBOARD_DIR))

import s3_utils  # noqa: E402
from s3_utils import (  # noqa: E402
    get_comparison_csv,
    get_folder_metadata,
    get_simulation_folders,
    get_station_data,
)


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


def test_get_comparison_csv_returns_dataframe(fake_s3):
    fake_s3.objects["raw/test/simulation_comparison.csv"] = (
        "route_id,time_spent_diff\n"
        "1,-5\n"
        "2,3\n"
    )

    result = get_comparison_csv(
        "test-bucket",
        "raw/test/simulation_comparison.csv",
    )

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert result["time_spent_diff"].tolist() == [-5, 3]


def test_get_comparison_csv_returns_empty_dataframe_on_error(fake_s3):
    result = get_comparison_csv(
        "test-bucket",
        "missing.csv",
    )

    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_get_station_data_returns_dataframe(fake_s3):
    fake_s3.objects["processed/stations.csv"] = (
        "Name,Latitude,Longitude\n"
        "Station A,51.5,-0.1\n"
    )

    result = get_station_data("test-bucket")

    assert isinstance(result, pd.DataFrame)


def test_get_station_data_returns_empty_dataframe_on_error(fake_s3):
    result = get_station_data("test-bucket")

    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_get_folder_metadata_returns_json_dict(fake_s3):
    fake_s3.objects["raw/run-1/user_station.json"] = json.dumps(
        {
            "Latitude": 51.5,
            "Longitude": -0.1,
        }
    )

    result = get_folder_metadata(
        "test-bucket",
        "raw/run-1/user_station.json",
    )

    assert result == {
        "Latitude": 51.5,
        "Longitude": -0.1,
    }


def test_get_folder_metadata_returns_error_dict_on_error(fake_s3):
    result = get_folder_metadata(
        "test-bucket",
        "missing.json",
    )

    assert "Error" in result


def test_get_simulation_folders_returns_folder_metadata(fake_s3):
    fake_s3.list_response = {
        "CommonPrefixes": [
            {"Prefix": "raw/run-1/"},
            {"Prefix": "raw/run-2/"},
        ]
    }

    fake_s3.objects["raw/run-1/user_station.json"] = json.dumps(
        {
            "Latitude": 51.5,
            "Longitude": -0.1,
        }
    )

    fake_s3.objects["raw/run-2/user_station.json"] = json.dumps(
        {
            "Latitude": 51.6,
            "Longitude": -0.2,
        }
    )

    result = get_simulation_folders(
        "test-bucket",
        "raw",
    )

    assert result == [
        {
            "Latitude": 51.5,
            "Longitude": -0.1,
            "Folder": "run-1",
        },
        {
            "Latitude": 51.6,
            "Longitude": -0.2,
            "Folder": "run-2",
        },
    ]



