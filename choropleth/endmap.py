import requests
import pandas as pd
import geopandas as gpd
import os
import pickle
import folium


def load_boundary_data() -> gpd.GeoDataFrame:
    """Load boundary data from cache or geojson file."""
    cache_file = "./boundaryData.pkl"
    if os.path.exists(cache_file):
        gdf = pickle.load(open(cache_file, "rb"))
    elif os.path.exists("./boundaryData.geojson"):
        gdf = gpd.read_file("./boundaryData.geojson")
        with open(cache_file, "wb") as f:
            pickle.dump(gdf, f)
    else:
        raise FileNotFoundError(
            "Boundary data not found. Please download from ONS and save as 'boundaryData.geojson'.")

    # Filter to E09 areas (london)
    gdf = gdf[gdf["CTYUA25CD"].str.startswith("E09")]
    return gdf


def get_stop_locations(stops_url: str) -> pd.DataFrame:
    """Fetch tube stop locations from TFL API and return a cleaned DataFrame."""
    response = requests.get(stops_url)
    data = response.json()
    stops_df = pd.DataFrame(data["stopPoints"])
    clean_stops = stops_df[['lat', 'lon', 'commonName', 'id']]
    return clean_stops


def get_normalised_stops(stops_url: str) -> pd.DataFrame:
    """Fetch tube stop locations and return a DataFrame with averaged coordinates per station."""
    clean_stops = get_stop_locations(stops_url)

    # GROUP BY STATION NAME AND AVERAGE COORDINATES
    stations = clean_stops.groupby('commonName')[
        ['lat', 'lon']].mean().reset_index()

    return stations


def get_stations_per_boundary(gdf: gpd.GeoDataFrame, stations_gdf: gpd.GeoDataFrame) -> pd.Series:
    """Perform spatial join to count how many stations fall within each boundary zone."""
    stations_in_zones = gpd.sjoin(
        stations_gdf, gdf, how='left', predicate='within')
    station_counts = stations_in_zones.groupby("index_right").size()
    return station_counts


def create_choropleth(gdf: gpd.GeoDataFrame, stations: pd.DataFrame) -> folium.Map:
    """Create a choropleth map with station counts and station markers."""
    m = gdf.explore(column='station_count', cmap='YlOrRd', legend=True)

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


if __name__ == "__main__":
    stops_url = "https://api.tfl.gov.uk/StopPoint/Mode/tube"
    # STEP 1: Load boundary data
    # This data is manually downloaded once from ONS website.
    gdf = load_boundary_data()

    # STEP 2: Load tube stops
    stations = get_normalised_stops(stops_url)

    # STEP 3: Convert stations to GeoDataFrame
    stations_gdf = gpd.GeoDataFrame(
        stations,
        geometry=gpd.points_from_xy(stations['lon'], stations['lat']),
        crs='EPSG:4326'
    )

    # STEP 4: Spatial join - count stations in each boundary zone
    station_counts = get_stations_per_boundary(gdf, stations_gdf)

    # Merge counts back to gdf
    gdf['station_count'] = gdf.index.map(station_counts).fillna(0).astype(int)

    # STEP 5: Create the map coloured by station count
    m = create_choropleth(gdf, stations)

    # STEP 6: Save the map
    m.save("combined_map.html")
    print(
        f"Map created with {len(stations)} tube stops across {gdf['station_count'].astype(bool).sum()} zones")
