"""Configuration and fixtures for choropleth tests."""

import sys
from pathlib import Path
import pandas as pd
import geopandas as gpd
import logging
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from choropleth_pipeline import setup_logger


@pytest.fixture
def boundary_gdf():
    """Sample GeoDataFrame with London borough boundaries."""
    from shapely.geometry import Point

    return gpd.GeoDataFrame(
        {
            "BOROUGH": ["Islington", "Tower Hamlets"],
            "geometry": [
                Point(0.1, 51.5).buffer(0.05),
                Point(0.05, 51.51).buffer(0.05),
            ],
        },
        crs="EPSG:4326",
    )


@pytest.fixture
def stations_df():
    """Sample stations DataFrame."""
    return pd.DataFrame(
        {
            "Name": ["Station A", "Station B"],
            "Latitude": [51.5, 51.51],
            "Longitude": [0.1, 0.05],
        }
    )


@pytest.fixture
def geojson_file(tmp_path):
    """Temporary GeoJSON file with boundary data."""
    from shapely.geometry import Point

    gdf = gpd.GeoDataFrame(
        {
            "BOROUGH": ["Test Borough"],
            "geometry": [Point(0.1, 51.5).buffer(0.05)],
        },
        crs="EPSG:4326",
    )

    geojson_file = tmp_path / "boundaryData.geojson"
    gdf.to_file(geojson_file, driver="GeoJSON")
    return geojson_file


@pytest.mark.parametrize("log_level", ["INFO", "DEBUG", "WARNING"])
def test_setup_logger(log_level):
    """Test logger configuration at different levels."""
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    setup_logger(log_level)
    assert root_logger.level == getattr(logging, log_level)
