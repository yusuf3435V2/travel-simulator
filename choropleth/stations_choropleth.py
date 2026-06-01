"""Plot the stations network using NetworkX and Folium."""

import logging
from io import BytesIO
import os
import pandas as pd
import networkx as nx
import folium
import boto3


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
        logging.info("Successfully loaded network from S3")
        return network
    except Exception as e:
        logging.error("Failed to extract network from S3: %s", e)
        return nx.MultiGraph()


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
    except Exception as e:
        logging.error("Failed to extract stations from S3: %s", e)
        return pd.DataFrame()


def validate_plot_inputs(station_data: pd.DataFrame, network: nx.MultiGraph) -> None:
    """Validate that input data is suitable for plotting."""
    if len(station_data) == 0:
        logging.error("Station data is empty, cannot plot map")
        raise ValueError("Cannot plot map with empty station data")

    if network.number_of_nodes() == 0:
        logging.warning("Network has no nodes, plotting station markers only")


def create_base_map(station_data: pd.DataFrame) -> folium.Map:
    """Create base Folium map centered on station data."""
    center_lat = station_data['Latitude'].mean()
    center_lon = station_data['Longitude'].mean()
    return folium.Map(location=[center_lat, center_lon], zoom_start=12)


def create_line_feature_groups(station_data: pd.DataFrame, base_map: folium.Map) -> dict:
    """Create FeatureGroups for each line and add to map."""
    line_groups = {}
    for line_id in station_data['Line_id'].unique():
        if pd.notna(line_id):
            line_name = str(line_id).replace('-', ' & ').capitalize()
            line_groups[line_id] = folium.FeatureGroup(
                name=f"Line: {line_name}")
            base_map.add_child(line_groups[line_id])
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

    if pd.isna(source_lat) or pd.isna(target_lat):
        logging.debug("Skipping edge %s-%s, missing coordinates",
                      source_id, target_id)
        return None

    return [[source_lat, source_lon], [target_lat, target_lon]]


def add_network_edges(network: nx.MultiGraph, station_data: pd.DataFrame,
                      base_map: folium.Map, line_groups: dict, color_scheme: dict) -> None:
    """Add all network edges to the map with layer control."""
    logging.info("Adding %s edges to map", network.number_of_edges())
    for source, target, key, data in network.edges(keys=True, data=True):
        line_id = data.get('line_id', 'unknown')
        line_color = color_scheme.get(line_id, 'black')

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


def plot_station_network(network: nx.MultiGraph, station_data: pd.DataFrame) -> folium.Map:
    """Plot the station network using Folium with colored edges and layer control."""
    validate_plot_inputs(station_data, network)

    color_scheme = create_colour_scheme()
    base_map = create_base_map(station_data)
    line_groups = create_line_feature_groups(station_data, base_map)

    add_station_markers(station_data, base_map, color_scheme)
    add_network_edges(network, station_data, base_map,
                      line_groups, color_scheme)

    folium.LayerControl().add_to(base_map)

    logging.info(
        "Plotted %s stations and %s edges", len(station_data), network.number_of_edges())
    return base_map


def main() -> None:
    """Main entry point for plotting station network from S3."""
    setup_logger()
    logging.info("Loading station network and data from S3")
    network_graph = extract_station_network()
    station_dataframe = extract_stations()

    logging.info("Plotting station network")
    try:
        station_map = plot_station_network(network_graph, station_dataframe)
        station_map.save("tube_network_map.html")
        logging.info("Map saved to tube_network_map.html")
    except ValueError as e:
        logging.error("Failed to plot map: %s", e)
    except IOError as e:
        logging.error("Failed to save map to file: %s", e)


if __name__ == "__main__":
    main()
