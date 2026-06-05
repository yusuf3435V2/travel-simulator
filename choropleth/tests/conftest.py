import sys
import os
import pytest
import geopandas as gpd
import pandas as pd

# Add parent directory to path to import modules from tfl_data_and_network
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


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
