"""The main choropleth functions to build the interactive map."""
import logging
import boto3
import pandas as pd
import geopandas as gpd
import folium
from data_retrieval import load_boundary_data, get_normalised_stops

logger = logging.getLogger(__name__)


STOPS_URL = "https://api.tfl.gov.uk/StopPoint/Mode/tube"


def get_stations_per_boundary(gdf: gpd.GeoDataFrame, stations_gdf: gpd.GeoDataFrame) -> pd.Series:
    """Perform spatial join to count how many stations fall within each boundary zone."""
    stations_in_zones = gpd.sjoin(
        stations_gdf, gdf, how='left', predicate='within')
    station_counts = stations_in_zones.groupby("index_right").size()
    return station_counts


def create_choropleth(gdf: gpd.GeoDataFrame) -> folium.Map:
    """Create a choropleth map with station counts and station markers."""
    m = gdf.explore(column='station_count', cmap='YlOrRd', legend=True)

    return m


def add_tube_stations_to_map(stations: pd.DataFrame, m: folium.Map) -> folium.Map:
    """Add tube station markers to the existing map."""
    for idx, row in stations.iterrows():
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=3,
            popup=row['commonName'],
            color='blue',
            fill=True,
            fillColor='blue',
            fillOpacity=0.7
        ).add_to(m)
    return m


def everything_all_in_one(STOPS_URL: str):
    """A function that combines the local functionality into one."""
    # STEP 1: Load boundary data
    # This data is manually downloaded once from ONS website.
    gdf = load_boundary_data("s3.pkl")

    # STEP 2: Load tube stops
    stations_gdf = get_normalised_stops(STOPS_URL)

    # STEP 3: Spatial join - count stations in each boundary zone
    station_counts = get_stations_per_boundary(gdf, stations_gdf)

    # Merge counts back to gdf
    gdf['station_count'] = gdf.index.map(station_counts).fillna(0).astype(int)

    # STEP 4: Create the map coloured by station count
    m = create_choropleth(gdf)
    m = add_tube_stations_to_map(stations_gdf, m)

    # STEP 5: Save the map
    m.save("combined_map.html")
    print(
        f"Map created with {len(stations_gdf)} tube stops across {gdf['station_count'].astype(bool).sum()} zones")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # # list contents of s3 bucket to check if file exists
    # check_s3_contents(BUCKET_NAME)

    # file = get_file_from_s3(BUCKET_NAME, FILE_KEY)
    # # save file to local disk
    # with open("s3.pkl", "wb") as f:
    #     f.write(file)
    everything_all_in_one(STOPS_URL)
