"""This module contains functions for retrieving and processing data for the choropleth map."""
import logging
import io
from pathlib import Path
import requests
import pandas as pd
import geopandas as gpd
import boto3
import pickle

logger = logging.getLogger(__name__)

STOPS_URL = "https://api.tfl.gov.uk/StopPoint/Mode/tube"
BUCKET_NAME = "c23-travel-simulation-bucket"
BOUNDARY_FILE = "boundaryData.pkl"


def create_stations_geodataframe(df: pd.DataFrame) -> gpd.GeoDataFrame:
    """Create a GeoDataFrame from stations DataFrame with geometry."""
    return gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df['Longitude'], df['Latitude']),
        crs='EPSG:4326'
    )


def load_boundaries_local(filepath: str) -> gpd.GeoDataFrame:
    """Load boundary data from cache or geojson file."""
    script_dir = Path(__file__).parent
    cache_file = script_dir / filepath
    geojson_file = script_dir / "boundaryData.geojson"

    if cache_file.exists():
        with open(cache_file, "rb") as f:
            gdf = pickle.load(f)
    elif geojson_file.exists():
        gdf = gpd.read_file(geojson_file)
        with open(cache_file, "wb") as f:
            pickle.dump(gdf, f)
    else:
        raise FileNotFoundError(
            "Boundary data not found. Please download from ONS and save as 'boundaryData.geojson'.")

    # Filter to E09 areas (london)
    gdf = gdf[gdf["CTYUA25CD"].str.startswith("E09")]
    return gdf


def load_boundaries_s3(bucket_name: str, file_path: str) -> gpd.GeoDataFrame:
    """Load boundary data from S3 bucket."""
    s3 = boto3.client('s3')
    try:
        response = s3.get_object(
            Bucket=bucket_name, Key=file_path)
        gdf = pickle.loads(response['Body'].read())
        gdf = gdf[gdf["CTYUA25CD"].str.startswith("E09")]
        logger.info("Boundary data loaded successfully from S3: %s", file_path)
        return gdf
    except Exception as e:
        logger.error("Error fetching file from S3: %s", e)
        raise RuntimeError(f"Failed to load boundaries from S3: {e}")


def get_file_from_s3(bucket_name: str, file_path: str) -> bytes:
    """Fetch a file from an S3 bucket."""
    s3 = boto3.client('s3')
    logger.info("Fetching file from S3: %s", file_path)
    try:
        response = s3.get_object(
            Bucket=bucket_name, Key=file_path)
        return response['Body'].read()
    except Exception as e:
        logger.error("Error fetching file from S3: %s", e)
        raise RuntimeError(f"Failed to fetch file from S3: {e}")


def upload_file_to_s3(bucket_name: str, file_path: str, data: bytes):
    """Upload a file to an S3 bucket. Specify full path."""
    s3 = boto3.client('s3')
    logger.info("Uploading file to S3: %s", file_path)
    try:
        s3.put_object(Bucket=bucket_name,
                      Key=file_path, Body=data)
        logger.info("File uploaded successfully to S3: %s", file_path)
    except Exception as e:
        logger.error("Error uploading file to S3: %s", e)
        raise RuntimeError(f"Failed to upload file to S3: {e}")


def get_normalised_stops(stops_url: str) -> gpd.GeoDataFrame:
    """Fetch tube stops and return averaged coordinates per station."""
    script_dir = Path(__file__).parent
    cache_file = script_dir / "stations.csv"

    # Load from cache if it exists
    if cache_file.exists():
        logger.info("Loading normalised stops from cache.")
        df = pd.read_csv(cache_file)
        return create_stations_geodataframe(df)

    # Fetch from API if no cache
    try:
        logger.info("Fetching stops from TFL API.")
        response = requests.get(stops_url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error("Error with url: %s . Message: %s", stops_url, e)
        raise RuntimeError(f"Failed to fetch stops data: {e}")

    # Process and normalize
    stations_gdf = normalise_stops_data(response)
    save_normalised_stops(stations_gdf, str(cache_file))
    return stations_gdf


def normalise_stops_data(response: requests.Response) -> gpd.GeoDataFrame:
    """Process API response to normalise station locations. (Deprecated - API outdated)"""
    logger.warning(
        "Using outdated TFL API - consider updating to current API version")
    logger.info("Normalising station locations")
    stops_df = pd.DataFrame(response.json()["stopPoints"])
    clean_stops = stops_df[['lat', 'lon', 'commonName', 'id']]
    stations = clean_stops.groupby('commonName')[
        ['lat', 'lon']].mean().reset_index()

    # Rename to match CSV structure (Longitude, Latitude)
    stations = stations.rename(columns={'lon': 'Longitude', 'lat': 'Latitude'})

    # Convert to GeoDataFrame (single place)
    logger.info("Converting stations to GeoDataFrame.")
    return create_stations_geodataframe(stations)


def get_normalised_stops_from_s3(
    bucket_name: str,
    s3_path: str,
    stops_url: str
) -> gpd.GeoDataFrame:
    """Load normalised stops from S3, or fetch from API and cache if not found."""
    try:
        logger.info("Loading stations from S3: %s", s3_path)
        data = get_file_from_s3(bucket_name, s3_path)
        df = pd.read_csv(io.BytesIO(data))
        return create_stations_geodataframe(df)
    except RuntimeError:
        logger.info("Stations not in S3, fetching from API.")
        # Fetch from API directly without local save
        try:
            logger.info("Fetching stops from TFL API.")
            response = requests.get(stops_url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error("Error with url: %s . Message: %s", stops_url, e)
            raise RuntimeError(f"Failed to fetch stops data: {e}")

        stations_gdf = normalise_stops_data(response)

        # Cache to S3 for future use (skip local save for cloud pipeline)
        data = stations_gdf.to_csv(index=False).encode('utf-8')
        upload_file_to_s3(bucket_name, s3_path, data)
        logger.info("Stations cached to S3: %s", s3_path)
        return stations_gdf


def save_normalised_stops(stations_gdf: gpd.GeoDataFrame, filename: str = "stations.csv"):
    """Save the normalised stops GeoDataFrame to CSV."""
    stations_gdf.to_csv(filename, index=False)


def save_choropleth_to_s3(gdf: gpd.GeoDataFrame, bucket_name: str, s3_path: str) -> None:
    """Save processed choropleth GeoDataFrame as GeoJSON to S3."""
    logger.info("Saving choropleth GeoDataFrame to S3: %s", s3_path)
    try:
        geojson_str = gdf.to_json()
        data = geojson_str.encode('utf-8')
        upload_file_to_s3(bucket_name, s3_path, data)
        logger.info(
            "Choropleth GeoDataFrame saved successfully to S3: %s", s3_path)
    except Exception as e:
        logger.error("Error saving choropleth to S3: %s", e)
        raise RuntimeError(f"Failed to save choropleth to S3: {e}")


def load_choropleth_from_s3(bucket_name: str, s3_path: str) -> gpd.GeoDataFrame:
    """Load choropleth GeoDataFrame from S3 GeoJSON."""
    logger.info("Loading choropleth GeoDataFrame from S3: %s", s3_path)
    try:
        data = get_file_from_s3(bucket_name, s3_path)
        gdf = gpd.read_file(io.BytesIO(data))
        logger.info(
            "Choropleth GeoDataFrame loaded successfully from S3: %s", s3_path)
        return gdf
    except Exception as e:
        logger.error("Error loading choropleth from S3: %s", e)
        raise RuntimeError(f"Failed to load choropleth from S3: {e}")


def check_s3_contents():
    """List contents of the configured S3 bucket."""
    s3 = boto3.client('s3')
    try:
        response = s3.list_objects_v2(Bucket=BUCKET_NAME)
        if 'Contents' in response:
            files = [obj['Key'] for obj in response['Contents']]
            logger.info("Files in bucket '%s': %s", BUCKET_NAME, files)
        else:
            logger.info("Bucket '%s' is empty.", BUCKET_NAME)
    except Exception as e:
        logger.error("Error listing objects in bucket '%s': %s",
                     BUCKET_NAME, e)
        raise RuntimeError(f"Failed to list S3 bucket contents: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # # list contents of s3 bucket to check if file exists
    # check_s3_contents(BUCKET_NAME)

    # gets the stop positions
    # stations = get_normalised_stops(STOPS_URL)
    # save_normalised_stops(stations)
