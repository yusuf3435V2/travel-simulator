"""This module contains functions for retrieving and processing data for the choropleth map."""
import logging
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
        return gdf
    except Exception as e:
        logger.error("Error fetching file from S3: %s", e)
        raise RuntimeError(f"Failed to load boundaries from S3: {e}")


def get_file_from_s3(bucket_name: str, file_path: str) -> bytes:
    """Fetch a file from an S3 bucket."""
    s3 = boto3.client('s3')
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
    cache_file = script_dir / "normalised_stops.pkl"

    # Load from cache if it exists
    if cache_file.exists():
        logger.info("Loading normalised stops from cache.")
        with open(cache_file, "rb") as f:
            return pickle.load(f)

    # Fetch from API if no cache
    try:
        logger.info("Fetching stops from TFL API.")
        response = requests.get(stops_url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error("Error with url: %s . Message: %s", stops_url, e)
        raise RuntimeError(f"Failed to fetch stops data: {e}")

    # Process and normalize
    logger.info("Normalising station locations")
    stops_df = pd.DataFrame(response.json()["stopPoints"])
    clean_stops = stops_df[['lat', 'lon', 'commonName', 'id']]
    stations = clean_stops.groupby('commonName')[
        ['lat', 'lon']].mean().reset_index()

    # Convert to GeoDataFrame (single place)
    logger.info("Converting stations to GeoDataFrame.")
    stations_gdf = gpd.GeoDataFrame(
        stations,
        geometry=gpd.points_from_xy(stations['lon'], stations['lat']),
        crs='EPSG:4326'
    )
    return stations_gdf


def save_normalised_stops(stations_gdf: gpd.GeoDataFrame, filename: str = "normalised_stops.pkl"):
    """Save the normalised stops GeoDataFrame."""
    with open(filename, "wb") as f:
        pickle.dump(stations_gdf, f)


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
