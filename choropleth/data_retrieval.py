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
FILE_KEY = "boundaryData.pkl"


def load_boundary_data(filepath: str) -> gpd.GeoDataFrame:
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


def get_file_from_s3(bucket_name: str, file_key: str) -> bytes:
    """Fetch a file from an S3 bucket."""
    s3 = boto3.client('s3')
    try:
        response = s3.get_object(
            Bucket=bucket_name, Key=f"processed/{file_key}")
        return response['Body'].read()
    except Exception as e:
        logger.error("Error fetching file from S3: %s", e)
        return b""


def get_normalised_stops(stops_url: str) -> gpd.GeoDataFrame:
    """Fetch tube stops and return averaged coordinates per station."""
    try:
        response = requests.get(stops_url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error("Error: with url: %s . Message: %s", stops_url, e)
        return gpd.GeoDataFrame()

    # Process the response to get unique stations with averaged coordinates
    stops_df = pd.DataFrame(response.json()["stopPoints"])
    clean_stops = stops_df[['lat', 'lon', 'commonName', 'id']]
    stations = clean_stops.groupby('commonName')[
        ['lat', 'lon']].mean().reset_index()

    # Convert to GeoDataFrame easily attached to the map later
    stations_gdf = gpd.GeoDataFrame(
        stations,
        geometry=gpd.points_from_xy(stations['lon'], stations['lat']),
        crs='EPSG:4326'
    )
    return stations_gdf


def save_normalised_stops(stations_gdf: gpd.GeoDataFrame, filename: str):
    """Save the normalised stops to a CSV file."""
    stations_gdf.to_csv(filename, index=False)


def check_s3_contents(BUCKET_NAME):
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # # list contents of s3 bucket to check if file exists
    # check_s3_contents(BUCKET_NAME)
    stations = get_normalised_stops(STOPS_URL)
    save_normalised_stops(stations, "normalised_stops.csv")
    # file = get_file_from_s3(BUCKET_NAME, FILE_KEY) --- IGNORE ---
