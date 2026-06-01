"""Plot the stations network using NetworkX and Folium."""

import logging
from io import BytesIO
import pickle
import pandas as pd
import geopandas as gpd
import networkx as nx
import folium
import boto3
from botocore.exceptions import ClientError


def setup_logger(log_level: str = "INFO") -> None:
    """Configure logging with the specified log_level: (DEBUG, INFO, WARNING, ERROR, CRITICAL)"""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(levelname)s - %(message)s',
        encoding="utf-8"
    )


def create_colour_scheme() -> dict:
    """Create a colour scheme for the different lines."""
    return {
        "bakerloo": "#b26300",
        "central": "#dc241f",
        "circle": "#ffd329",
        "district": "#007d32",
        "dlr": "#00afad",
        "elizabeth": "#773dbd",
        "hammersmith-city": "#f4a9be",
        "jubilee": "#a1a5a7",
        "metropolitan": "#9b0058",
        "northern": "#000000",
        "piccadilly": "#0019a8",
        "victoria": "#0098d8",
        "waterloo-city": "#93ceba",
    }


def extract_station_network() -> nx.MultiGraph:
    """Extract the station network from S3 bucket."""
    try:
        s3_client = boto3.client('s3')
        response = s3_client.get_object(
            Bucket='c23-travel-simulation-bucket',
            Key='processed/stations_network.graphml'
        )
        graphml_bytes = BytesIO(response['Body'].read())
        network = nx.read_graphml(graphml_bytes)
        if not network.is_multigraph():
            network = nx.MultiGraph(network)
        logging.info("Successfully loaded network from S3")
        return network
    except (ClientError, IOError, nx.NetworkXError) as e:
        logging.error("Failed to extract network from S3: %s", e)
        return nx.MultiGraph()


def extract_boundaries() -> gpd.GeoDataFrame:
    """Extract boundary data from S3 bucket."""
    try:
        s3_client = boto3.client('s3')
        response = s3_client.get_object(
            Bucket='c23-travel-simulation-bucket',
            Key='processed/boundaryData.pkl'
        )
        gdf = pickle.loads(response['Body'].read())
        logging.info("Successfully loaded boundaries from S3")
        gdf = gdf[gdf["CTYUA25CD"].str.startswith("E09")]
        return gdf
    except (ClientError, IOError, pickle.UnpicklingError) as e:
        logging.error("Failed to extract boundaries from S3: %s", e)
        return gpd.GeoDataFrame()


def extract_stations() -> pd.DataFrame:
    """Extract the stations data from S3 bucket."""
    try:
        s3_client = boto3.client('s3')
        response = s3_client.get_object(
            Bucket='c23-travel-simulation-bucket',
            Key='processed/stations.csv'
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


def create_line_feature_groups(station_data: pd.DataFrame, base_map: folium.Map) -> dict:
    """Create FeatureGroups for each line and add to map."""
    logging.info("Creating feature groups for tube lines")
    line_groups = {}
    for line_id in station_data['Line_id'].unique():
        if pd.notna(line_id):
            line_name = str(line_id).replace('-', ' & ').capitalize()
            line_groups[line_id] = folium.FeatureGroup(
                name=f"Line: {line_name}")
            base_map.add_child(line_groups[line_id])
    logging.info("Created %s feature groups", len(line_groups))
    return line_groups


def format_station_popup(row: pd.Series, station_data: pd.DataFrame) -> str:
    """Format popup text for a station marker."""
    station_lines = station_data[station_data['UniqueId']
                                 == row['UniqueId']]['Line_id'].unique()
    lines_text = ", ".join([str(l).replace('-', ' & ').capitalize()
                           for l in station_lines if pd.notna(l)])
    return f"<b>{row['Name'].replace('-', ' ').title()}</b><br>Lines: {lines_text}"


def add_station_markers(station_data: pd.DataFrame, base_map: folium.Map,
                        color_scheme: dict) -> None:
    """Add all station markers to the map."""
    logging.info("Adding %s station markers to map", len(station_data))
    for _, row in station_data.iterrows():
        if pd.isna(row['Latitude']) or pd.isna(row['Longitude']):
            logging.warning(
                "Station %s has missing coordinates, skipping", row['Name'])
            continue

        popup_text = format_station_popup(row, station_data)

        folium.CircleMarker(
            location=[row['Latitude'], row['Longitude']],
            radius=2,
            popup=folium.Popup(popup_text, max_width=200),
            color=color_scheme.get(row['Line_id'], 'grey'),
            fill=True,
            fillColor=color_scheme.get(row['Line_id'], 'grey'),
            fillOpacity=0.7,
            weight=1
        ).add_to(base_map)


def get_edge_coordinates(source_id: str, target_id: str,
                         station_data: pd.DataFrame) -> list[list[float]] | None:
    """Get coordinates for an edge between two stations."""
    source_row = station_data[station_data['UniqueId'] == source_id]
    target_row = station_data[station_data['UniqueId'] == target_id]

    if source_row.empty or target_row.empty:
        return None

    source_lat = source_row.iloc[0]['Latitude']
    source_lon = source_row.iloc[0]['Longitude']
    target_lat = target_row.iloc[0]['Latitude']
    target_lon = target_row.iloc[0]['Longitude']

    if (pd.isna(source_lat) or pd.isna(target_lat) or pd.isna(source_lon) or pd.isna(target_lon)):
        logging.debug("Skipping edge %s-%s, missing coordinates",
                      source_id, target_id)
        return None

    return [[source_lat, source_lon], [target_lat, target_lon]]


def add_network_edges(network: nx.MultiGraph, station_data: pd.DataFrame,
                      base_map: folium.Map, line_groups: dict, color_scheme: dict) -> None:
    """Add all network edges to the map with layer control."""
    logging.info("Adding %s edges to map", network.number_of_edges())
    for source, target, _, data in network.edges(keys=True, data=True):
        line_id = data.get('line_id', 'unknown')

        # Only include edges with colours in the scheme
        if line_id not in color_scheme:
            logging.debug(
                "Skipping edge %s-%s, line_id '%s' not in colour scheme", source, target, line_id)
            continue

        line_color = color_scheme[line_id]

        coords = get_edge_coordinates(source, target, station_data)
        if coords is None:
            continue

        line_name = str(line_id).replace('-', ' & ').capitalize()
        polyline = folium.PolyLine(
            coords,
            color=line_color,
            weight=2,
            opacity=0.7,
            popup=f"Line: {line_name}"
        )

        # Add to line's feature group
        if line_id in line_groups:
            polyline.add_to(line_groups[line_id])
        else:
            polyline.add_to(base_map)


def create_combined_base_map(gdf: gpd.GeoDataFrame, station_data: pd.DataFrame) -> folium.Map:
    """Create a choropleth map colored by station density as base for network overlay."""
    logging.info("Creating choropleth base map with %s zones", len(gdf))
    m = gdf.explore(column='station_count', cmap='YlOrRd',
                    legend=True, name="Choropleth")

    # Center on stations for better UX
    center_lat = station_data['Latitude'].mean()
    center_lon = station_data['Longitude'].mean()
    m.location = [center_lat, center_lon]

    # Add tooltip layer with no name
    folium.GeoJson(
        data=gdf.__geo_interface__,
        style_function=lambda x: {'fillOpacity': 0,
                                  'color': 'transparent', 'weight': 0},
        tooltip=folium.features.GeoJsonTooltip(
            fields=['CTYUA25NM', 'station_count'],
            aliases=['Borough:', 'Station Count:']
        ),
        name='Borough Tooltips'
    ).add_to(m)

    logging.info(
        "Choropleth map centered at (%.4f, %.4f)", center_lat, center_lon)

    return m


def create_choropleth() -> folium.Map | None:
    """Create a choropleth map with station counts and station markers."""
    setup_logger()
    logging.info("Starting choropleth creation")

    network = extract_station_network()
    gdf = extract_boundaries()
    stations_df = extract_stations()

    if gdf.empty or stations_df.empty:
        logging.error("Failed to load required data")
        return None
    stations_gdf = convert_stations_to_geodataframe(stations_df)
    station_counts = get_stations_per_boundary(gdf, stations_gdf)
    gdf['station_count'] = gdf.index.map(station_counts).fillna(0).astype(int)

    m = create_combined_base_map(gdf, stations_df)

    color_scheme = create_colour_scheme()
    line_groups = create_line_feature_groups(stations_df, m)

    add_station_markers(stations_df, m, color_scheme)
    add_network_edges(network, stations_df, m, line_groups, color_scheme)

    logging.info("Adding layer control to map")
    folium.LayerControl().add_to(m)

    logging.info("Saving map to tube_network_map.html")
    try:
        m.save("tube_network_map.html")
        logging.info("Map successfully saved to tube_network_map.html")
    except IOError as e:
        logging.error("Failed to save map: %s", e)

    return m


if __name__ == "__main__":
    create_choropleth()
