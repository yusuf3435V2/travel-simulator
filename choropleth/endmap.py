"""The main choropleth functions to build the interactive map."""
import logging
import pandas as pd
import geopandas as gpd
import folium
from data_functions import (
    load_boundaries_local,
    get_normalised_stops,
    load_boundaries_s3,
    get_normalised_stops_from_s3,
    save_choropleth_to_s3
)

logger = logging.getLogger(__name__)


STOPS_URL = "https://api.tfl.gov.uk/StopPoint/Mode/tube"
BOUNDARIES_FILE = "boundaryData.pkl"
BUCKET_NAME = "c23-travel-simulation-bucket"


def get_stations_per_boundary(gdf: gpd.GeoDataFrame, stations_gdf: gpd.GeoDataFrame) -> pd.Series:
    """Perform spatial join to count how many stations fall within each boundary zone."""
    stations_in_zones = gpd.sjoin(
        stations_gdf, gdf, how='left', predicate='within')
    station_counts = stations_in_zones.groupby("index_right").size()
    return station_counts


def create_choropleth(gdf: gpd.GeoDataFrame) -> folium.Map:
    """Create a choropleth map with station counts."""
    m = gdf.explore(column='station_count', cmap='YlOrRd', legend=True)

    return m


def choropleth_creation(stops_url: str):
    """A function that combines the local functionality into one."""
    # STEP 1: Load boundary data
    # This data is manually downloaded once from ONS website.
    gdf = load_boundaries_local(BOUNDARIES_FILE)

    # STEP 2: Load tube stops
    stations_gdf = get_normalised_stops(stops_url)

    # STEP 3: Spatial join - count stations in each boundary zone
    station_counts = get_stations_per_boundary(gdf, stations_gdf)

    # Merge counts back to gdf
    gdf['station_count'] = gdf.index.map(station_counts).fillna(0).astype(int)

    # STEP 4: Create the map coloured by station count
    m = create_choropleth(gdf)

    # STEP 5: Save the map
    m.save("choropleth_local.html")
    logger.info(
        f"Map created with {len(stations_gdf)} tube stops across {gdf['station_count'].astype(bool).sum()} zones")


def choropleth_creation_cloud(
    stops_url: str,
    boundary_s3_path: str = "processed/boundaryData.pkl",
    station_s3_path: str = "processed/stations.csv",
    choropleth_s3_path: str = "outputs/choropleth.geojson"
):
    """Create choropleth map using boundary and station data from S3.\n
    Saves processed choropleth data back to S3."""
    # STEP 1: Load boundary and station data from S3
    logger.info("Loading boundaries from S3: %s", boundary_s3_path)
    gdf = load_boundaries_s3(BUCKET_NAME, boundary_s3_path)

    logger.info("Loading stations from S3: %s", station_s3_path)
    stations_gdf = get_normalised_stops_from_s3(
        BUCKET_NAME, station_s3_path, stops_url)

    # STEP 2: Spatial join - count stations in each boundary zone
    logger.info(
        "Performing spatial join to count stations in each boundary zone.")
    station_counts = get_stations_per_boundary(gdf, stations_gdf)

    # Merge counts back to gdf
    gdf['station_count'] = gdf.index.map(station_counts).fillna(0).astype(int)

    # STEP 3: Save processed choropleth data to S3
    save_choropleth_to_s3(gdf, BUCKET_NAME, choropleth_s3_path)

    # STEP 4: Create and save the HTML visualization
    m = create_choropleth(gdf)
    m.save("choropleth_cloud.html")
    logger.info(
        f"Map created with {len(stations_gdf)} tube stops across {gdf['station_count'].astype(bool).sum()} zones")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # # list contents of s3 bucket to check if file exists
    # check_s3_contents()

    # choropleth_creation(STOPS_URL)

    choropleth_creation_cloud(STOPS_URL)
