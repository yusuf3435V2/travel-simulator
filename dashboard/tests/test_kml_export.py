"""Tests for dashboard/kml_export.py."""

import sys
import zipfile
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

DASHBOARD_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DASHBOARD_DIR))


from kml_export import (  # noqa: E402
    generate_kml_bytes,
    generate_kmz_bytes,
    get_affected_stations,
)


def test_get_affected_stations_returns_nearby_station_and_catchment(
    mock_load_stations_kml,
):
    affected_stations, catchment_gdf = get_affected_stations(
        proposed_lat=51.5074,
        proposed_lon=-0.1278,
        radius_m=800,
    )

    assert len(affected_stations) == 1
    assert affected_stations.iloc[0]["Name"] == "Near Station"
    assert len(catchment_gdf) == 1
    assert catchment_gdf.iloc[0]["name"] == "Walking Catchment"


def test_generate_kml_bytes_contains_expected_text(mock_load_stations_kml):
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


def test_generate_kmz_bytes_contains_doc_kml(mock_load_stations_kml):
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
