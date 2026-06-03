import geopandas as gpd
import pandas as pd
import logging
from pathlib import Path
from io import BytesIO
import boto3
from botocore.exceptions import ClientError


def setup_logger(log_level: str = "INFO") -> None:
    """Configure logging with the specified log_level: (DEBUG, INFO, WARNING, ERROR, CRITICAL)"""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(levelname)s - %(message)s',
        encoding="utf-8"
    )


def clean_boundary_data(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Filter boundary data to London boroughs and select relevant columns."""
    # Check if already cleaned
    if "borough_name" in gdf.columns and "geometry" in gdf.columns and len(gdf.columns) == 2:
        logging.info("Boundary data already cleaned, skipping cleaning steps.")
        return gdf

    logging.info(
        "Cleaning boundary data - selecting borough name and geometry.")

    if "BOROUGH" not in gdf.columns or "geometry" not in gdf.columns:
        logging.error(
            "Required columns not found. Available columns: %s", gdf.columns.tolist())
        raise KeyError(
            f"Required columns not found. Available columns: {gdf.columns.tolist()}")

    gdf = gdf[["BOROUGH", "geometry"]]
    gdf.columns = ["Borough Name", "geometry"]
    logging.info("Cleaned %s boroughs", len(gdf))
    return gdf


def load_boundaries_local(filename: str = "boundaryData.geojson") -> gpd.GeoDataFrame:
    """Load boundary data from cache or geojson file."""
    script_dir = Path(__file__).parent
    geojson_file = script_dir / filename

    # https://gis-tfl.opendata.arcgis.com/datasets/london-boroughs-1/about
    if geojson_file.exists():
        gdf = gpd.read_file(geojson_file)
    else:
        raise FileNotFoundError(
            "Boundary data not found. Please download from ONS and save as 'boundaryData.geojson'.")
    # Filter and clean boundary data
    gdf = clean_boundary_data(gdf)
    return gdf


def extract_stations(station_s3_path: str = 'processed/stations.csv') -> pd.DataFrame:
    """Extract the stations data from S3 bucket."""
    try:
        s3_client = boto3.client('s3')
        response = s3_client.get_object(
            Bucket='c23-travel-simulation-bucket',
            Key=station_s3_path
        )
        csv_bytes = response['Body'].read().decode('utf-8')
        stations_df = pd.read_csv(BytesIO(csv_bytes.encode()))
        logging.info("Successfully loaded stations from S3")
        return stations_df
    except (ClientError, IOError, pd.errors.ParserError) as e:
        logging.error("Failed to extract stations from S3: %s", e)
        return pd.DataFrame()


def convert_stations_to_geodataframe(stations: pd.DataFrame) -> gpd.GeoDataFrame:
    """Convert stations DataFrame to GeoDataFrame."""
    logging.info("Converting stations to GeoDataFrame.")
    stations_gdf = gpd.GeoDataFrame(
        stations,
        geometry=gpd.points_from_xy(
            stations['Longitude'], stations['Latitude']),
        crs='EPSG:4326'
    )
    return stations_gdf


def get_stations_per_boundary(gdf: gpd.GeoDataFrame, stations_gdf: gpd.GeoDataFrame) -> pd.Series:
    """Perform spatial join to count stations in each boundary zone."""
    logging.info("Performing spatial join for %s stations and %s zones", len(
        stations_gdf), len(gdf))
    stations_in_zones = gpd.sjoin(
        stations_gdf, gdf, how='left', predicate='within')
    station_counts = stations_in_zones.groupby("index_right").size()
    logging.info("Counted stations in %s zones", len(station_counts))
    return station_counts


def save_choropleth_to_s3(gdf: gpd.GeoDataFrame, s3_path: str) -> None:
    """Save processed choropleth GeoDataFrame as GeoJSON to S3."""
    logging.info("Saving choropleth GeoDataFrame to S3: %s", s3_path)
    try:
        s3 = boto3.client('s3')
        geojson_str = gdf.to_json()
        data = geojson_str.encode('utf-8')
        s3.put_object(Bucket='c23-travel-simulation-bucket',
                      Key=s3_path, Body=data)
        logging.info(
            "Choropleth GeoDataFrame saved successfully to S3: %s", s3_path)
    except Exception as e:
        logging.error("Error saving choropleth to S3: %s", e)
        raise RuntimeError(f"Failed to save choropleth to S3: {e}")


def lambda_handler(event: dict = None, context: dict = None) -> dict:
    """Run the full pipeline and save the choropleth GeoDataFrame to S3."""
    try:
        setup_logger()
        boundary_local_path = "boundaryData.geojson"
        station_s3_path = "processed/stations.csv"
        choropleth_s3_path = "outputs/choropleth.geojson"

        # Load boundary and station data from S3
        gdf = load_boundaries_local(boundary_local_path)
        stations_df = extract_stations(station_s3_path)
        stations_gdf = convert_stations_to_geodataframe(stations_df)

        # Spatial join - count stations in each boundary zone
        station_counts = get_stations_per_boundary(gdf, stations_gdf)

        # Merge counts back to gdf
        gdf['Station Count'] = gdf.index.map(
            station_counts).fillna(0).astype(int)

        return {"statusCode": 200, "body": "Choropleth created and saved to S3 successfully."}
    except Exception as e:
        logging.error(
            "Failed to run pipeline and save choropleth to S3: %s", e)
        return {
            "statusCode": 500,
            "body": f"Failed to run pipeline and save choropleth to S3: {str(e)}",
        }


if __name__ == "__main__":
    lambda_handler()
