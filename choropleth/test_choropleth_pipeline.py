import pytest
import pandas as pd
import geopandas as gpd
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import BytesIO
from botocore.exceptions import ClientError

from choropleth_pipeline import (
    setup_logger,
    clean_boundary_data,
    load_boundaries_local,
    extract_stations,
    convert_stations_to_geodataframe,
    get_stations_per_boundary,
    save_choropleth_to_s3,
    lambda_handler,
)


import pytest
import pandas as pd
import geopandas as gpd
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import BytesIO
from botocore.exceptions import ClientError

from choropleth_pipeline import (
    setup_logger,
    clean_boundary_data,
    load_boundaries_local,
    extract_stations,
    convert_stations_to_geodataframe,
    get_stations_per_boundary,
    save_choropleth_to_s3,
    lambda_handler,
)


@pytest.fixture
def boundary_gdf():
    """Sample GeoDataFrame with London borough boundaries."""
    from shapely.geometry import Point
    return gpd.GeoDataFrame({
        "BOROUGH": ["Islington", "Tower Hamlets"],
        "geometry": [Point(0.1, 51.5).buffer(0.05), Point(0.05, 51.51).buffer(0.05)],
    }, crs="EPSG:4326")


@pytest.fixture
def stations_df():
    """Sample stations DataFrame."""
    return pd.DataFrame({
        "Name": ["Station A", "Station B"],
        "Latitude": [51.5, 51.51],
        "Longitude": [0.1, 0.05],
    })


@pytest.fixture
def geojson_file(tmp_path):
    """Temporary GeoJSON file with boundary data."""
    from shapely.geometry import Point
    gdf = gpd.GeoDataFrame({
        "BOROUGH": ["Test Borough"],
        "geometry": [Point(0.1, 51.5).buffer(0.05)],
    }, crs="EPSG:4326")

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


def test_clean_boundary_data(boundary_gdf):
    """Test boundary data cleaning."""
    result = clean_boundary_data(boundary_gdf)
    assert list(result.columns) == ["Borough Name", "geometry"]
    assert len(result) == 2


def test_clean_boundary_data_missing_columns():
    """Test error when required columns missing."""
    from shapely.geometry import Point
    gdf = gpd.GeoDataFrame({"NAME": ["Test"], "geometry": [Point(0.1, 51.5)]})
    with pytest.raises(KeyError):
        clean_boundary_data(gdf)


def test_clean_boundary_data_skip_if_cleaned(boundary_gdf, caplog):
    """Test already-cleaned data is skipped."""
    boundary_gdf.columns = ["borough_name", "geometry"]
    with caplog.at_level(logging.INFO):
        clean_boundary_data(boundary_gdf)
    assert "already cleaned" in caplog.text


def test_load_boundaries_local(geojson_file):
    """Test loading boundary data from file."""
    result = load_boundaries_local(str(geojson_file))
    assert isinstance(result, gpd.GeoDataFrame)


def test_load_boundaries_local_not_found():
    """Test error when file not found."""
    with pytest.raises(FileNotFoundError):
        load_boundaries_local("nonexistent.geojson")


@patch("choropleth_pipeline.boto3.client")
def test_extract_stations(mock_boto3, stations_df):
    """Test extracting stations from S3."""
    mock_s3 = MagicMock()
    mock_boto3.return_value = mock_s3

    csv_buffer = BytesIO()
    stations_df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    mock_s3.get_object.return_value = {
        "Body": MagicMock(read=lambda: csv_buffer.getvalue())}

    result = extract_stations("stations.csv")
    assert len(result) == 2
    assert "Name" in result.columns


@patch("choropleth_pipeline.boto3.client")
def test_extract_stations_error(mock_boto3):
    """Test S3 extraction error handling."""
    mock_s3 = MagicMock()
    mock_boto3.return_value = mock_s3
    mock_s3.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey"}}, "GetObject")

    result = extract_stations("missing.csv")
    assert result.empty


def test_convert_stations_to_geodataframe(stations_df):
    """Test converting DataFrame to GeoDataFrame."""
    result = convert_stations_to_geodataframe(stations_df)
    assert isinstance(result, gpd.GeoDataFrame)
    assert result.crs == "EPSG:4326"
    assert len(result) == 2


def test_convert_stations_missing_coords():
    """Test error with missing coordinates."""
    df = pd.DataFrame({"Name": ["A"], "Latitude": [51.5]})
    with pytest.raises(KeyError):
        convert_stations_to_geodataframe(df)


def test_get_stations_per_boundary(boundary_gdf, stations_df):
    """Test counting stations per boundary."""
    stations_gdf = convert_stations_to_geodataframe(stations_df)
    result = get_stations_per_boundary(boundary_gdf, stations_gdf)
    assert isinstance(result, pd.Series)
    assert result.sum() == 2


def test_get_stations_per_boundary_empty():
    """Test with no stations."""
    from shapely.geometry import Point
    gdf = gpd.GeoDataFrame({"BOROUGH": ["Zone"], "geometry": [
                           Point(0.1, 51.5).buffer(0.05)]}, crs="EPSG:4326")
    empty_stations = gpd.GeoDataFrame(
        {"Name": [], "geometry": gpd.GeoSeries([], crs="EPSG:4326")})

    result = get_stations_per_boundary(gdf, empty_stations)
    assert len(result) == 0


@patch("choropleth_pipeline.boto3.client")
def test_save_choropleth_to_s3(mock_boto3, boundary_gdf):
    """Test saving choropleth to S3."""
    mock_s3 = MagicMock()
    mock_boto3.return_value = mock_s3

    save_choropleth_to_s3(boundary_gdf, "output.geojson")
    mock_s3.put_object.assert_called_once()


@patch("choropleth_pipeline.boto3.client")
def test_save_choropleth_to_s3_error(mock_boto3, boundary_gdf):
    """Test S3 save error handling."""
    mock_s3 = MagicMock()
    mock_boto3.return_value = mock_s3
    mock_s3.put_object.side_effect = Exception("S3 Error")

    with pytest.raises(RuntimeError):
        save_choropleth_to_s3(boundary_gdf, "output.geojson")


@patch("choropleth_pipeline.save_choropleth_to_s3")
@patch("choropleth_pipeline.get_stations_per_boundary")
@patch("choropleth_pipeline.convert_stations_to_geodataframe")
@patch("choropleth_pipeline.extract_stations")
@patch("choropleth_pipeline.load_boundaries_local")
def test_lambda_handler_success(mock_load, mock_extract, mock_convert, mock_get_counts, mock_save, boundary_gdf, stations_df):
    """Test successful pipeline execution."""
    stations_gdf = convert_stations_to_geodataframe(stations_df)
    mock_load.return_value = boundary_gdf
    mock_extract.return_value = stations_df
    mock_convert.return_value = stations_gdf
    mock_get_counts.return_value = pd.Series({0: 1, 1: 1})

    result = lambda_handler()
    assert result["statusCode"] == 200
    mock_save.assert_called_once()


@patch("choropleth_pipeline.load_boundaries_local")
def test_lambda_handler_error(mock_load):
    """Test pipeline error handling."""
    mock_load.side_effect = FileNotFoundError("Not found")

    result = lambda_handler()
    assert result["statusCode"] == 500
    assert "Failed" in result["body"]
