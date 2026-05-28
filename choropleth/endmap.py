import requests
import pandas as pd
import geopandas as gpd
import os
import pickle
import folium

stops_url = "https://api.tfl.gov.uk/StopPoint/Mode/tube"

if __name__ == "__main__":
    # STEP 1: Load boundary data
    # This data is manually downloaded once from ONS website.
    cache_file = "./boundaryData.pkl"
    if os.path.exists(cache_file):
        gdf = pickle.load(open(cache_file, "rb"))
    else:
        gdf = gpd.read_file("./boundaryData.geojson")
        with open(cache_file, "wb") as f:
            pickle.dump(gdf, f)

    # Filter to E09 areas
    gdf = gdf[gdf["CTYUA25CD"].str.startswith("E09")]

    # STEP 2: Load tube stops
    response = requests.get(stops_url)
    data = response.json()
    stops_df = pd.DataFrame(data["stopPoints"])
    clean_stops = stops_df[['lat', 'lon', 'commonName', 'id']]

    # GROUP BY STATION NAME AND AVERAGE COORDINATES
    stations = clean_stops.groupby('commonName')[
        ['lat', 'lon']].mean().reset_index()

    # STEP 3: Convert stations to GeoDataFrame
    stations_gdf = gpd.GeoDataFrame(
        stations,
        geometry=gpd.points_from_xy(stations['lon'], stations['lat']),
        crs='EPSG:4326'
    )

    # STEP 4: Spatial join - count stations in each boundary zone
    stations_in_zones = gpd.sjoin(
        stations_gdf, gdf, how='left', predicate='within')
    station_counts = stations_in_zones.groupby("index_right").size()

    # Merge counts back to gdf
    gdf['station_count'] = gdf.index.map(station_counts).fillna(0).astype(int)

    # STEP 5: Create the map colored by station count
    m = gdf.explore(column='station_count', cmap='YlOrRd', legend=True)

    # STEP 6: Add station markers on top
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

    # STEP 7: Save the map
    m.save("combined_map.html")
    print(
        f"Map created with {len(stations)} tube stops across {gdf['station_count'].astype(bool).sum()} zones")
