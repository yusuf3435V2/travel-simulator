"""Tests for dashboard/kml_export.py."""

import sys
import zipfile
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

DASHBOARD_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DASHBOARD_DIR))

import kml_export  # noqa: E402
from kml_export import (  # noqa: E402
    generate_kml_bytes,
    generate_kmz_bytes,
    get_affected_stations,
)


@pytest.fixture
def sample_stations_df():
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
def mock_load_stations(monkeypatch, sample_stations_df):
    def fake_load_stations_from_s3(bucket_name, key):
        return sample_stations_df

    monkeypatch.setattr(
        kml_export,
        "load_stations_from_s3",
        fake_load_stations_from_s3,
    )


def test_get_affected_stations_returns_nearby_station_and_catchment(mock_load_stations):
    affected_stations, catchment_gdf = get_affected_stations(
        proposed_lat=51.5074,
        proposed_lon=-0.1278,
        radius_m=800,
    )

    assert len(affected_stations) == 1
    assert affected_stations.iloc[0]["Name"] == "Near Station"
    assert len(catchment_gdf) == 1
    assert catchment_gdf.iloc[0]["name"] == "Walking Catchment"


def test_generate_kml_bytes_contains_expected_text(mock_load_stations):
    kml_bytes = generate_kml_bytes(
        proposed_lat=51.5074,
        proposed_lon=-0.1278,
        selected_line="Bakerloo",
        radius_m=800,
    )

    kml_text = kml_bytes.decode("utf-8")

    assert "Proposed Station" in kml_text
    assert "Bakerloo" in kml_text
    assert "800m Walking Catchment" in kml_text
    assert "Near Station" in kml_text
    assert "Far Station" not in kml_text


def test_generate_kmz_bytes_contains_doc_kml(mock_load_stations):
    kmz_bytes = generate_kmz_bytes(
        proposed_lat=51.5074,
        proposed_lon=-0.1278,
        selected_line="Bakerloo",
        radius_m=800,
    )

    with zipfile.ZipFile(BytesIO(kmz_bytes), "r") as kmz:
        assert "doc.kml" in kmz.namelist()

        kml_text = kmz.read("doc.kml").decode("utf-8")

        assert "Proposed Station" in kml_text
        assert "800m Walking Catchment" in kml_text
