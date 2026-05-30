"""Plot the stations network using NetworkX and Folium."""

import logging
from io import BytesIO
import os
import pandas as pd
import networkx as nx
import folium
import boto3
from api_utils import setup_logger
from create_stations_network import load_station_network_local


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


def ensure_files_exist(network_file_path: str = "stations/tube_network.graphml",
                       station_file_path: str = "stations/Stations.csv") -> bool:
    """Ensure network and station files exist, creating them if necessary."""
    network_exists = os.path.exists(network_file_path)
    station_exists = os.path.exists(station_file_path)

    if network_exists and station_exists:
        logging.debug("Both network and station files exist")
        return True

    if not network_exists or not station_exists:
        logging.info("Missing files detected. Extracting from API...")
        return load_station_network_local(
            network_file_path=network_file_path,
            station_file_path=station_file_path
        )

    return False


def extract_station_network_local(file_path: str = "stations/tube_network.graphml") -> nx.MultiGraph:
    """Load the station network from a .graphml file, extracting from API if missing."""
    # Ensure file exists by extracting from API if necessary
    if not ensure_files_exist(network_file_path=file_path):
        logging.error("Failed to ensure network file exists at %s", file_path)
        return nx.MultiGraph()

    try:
        return nx.read_graphml(file_path)
    except Exception as e:
        logging.error("Failed to read network file at %s: %s", file_path, e)
        return nx.MultiGraph()


def extract_station_data_local(file_path: str = "stations/Stations.csv") -> pd.DataFrame:
    """Load the station data from a .csv file, extracting from API if missing."""
    # Ensure file exists by extracting from API if necessary
    if not ensure_files_exist(station_file_path=file_path):
        logging.error(
            "Failed to ensure station data file exists at %s", file_path)
        return pd.DataFrame()

    try:
        return pd.read_csv(file_path)
    except Exception as e:
        logging.error(
            "Failed to read station data file at %s: %s", file_path, e)
        return pd.DataFrame()


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


def plot_station_network(network: nx.MultiGraph, station_data: pd.DataFrame) -> folium.Map:
    """Plot the station network using Folium with colored edges and layer control."""
    if len(station_data) == 0:
        logging.error("Station data is empty, cannot plot map")
        raise ValueError("Cannot plot map with empty station data")

    if network.number_of_nodes() == 0:
        logging.warning("Network has no nodes, plotting station markers only")

    color_scheme = create_colour_scheme()

    # Calculate center of map
    center_lat = station_data['Latitude'].mean()
    center_lon = station_data['Longitude'].mean()

    # Create Folium map with layer control
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

    # Group edges by line for layer control
    line_groups = {}
    for line_id in station_data['Line_id'].unique():
        if pd.notna(line_id):
            line_groups[line_id] = folium.FeatureGroup(
                name=f"Line: {str(line_id).replace('-', ' & ').capitalize()}")
            m.add_child(line_groups[line_id])

    # Add stations as markers
    logging.info("Adding %s station markers to map", len(station_data))
    for _, row in station_data.iterrows():
        if pd.isna(row['Latitude']) or pd.isna(row['Longitude']):
            logging.warning(
                "Station %s has missing coordinates, skipping", row['Name'])
            continue

        # Get all lines at this station
        station_lines = station_data[station_data['UniqueId']
                                     == row['UniqueId']]['Line_id'].unique()
        lines_text = ", ".join([str(l).replace('-', ' & ').capitalize()
                               for l in station_lines if pd.notna(l)])

        popup_text = f"<b>{row['Name'].replace('-', ' ').title()}</b><br>Lines: {lines_text}"

        folium.CircleMarker(
            location=[row['Latitude'], row['Longitude']],
            radius=2,
            popup=folium.Popup(popup_text, max_width=200),
            color=color_scheme.get(row['Line_id'], 'grey'),
            fill=True,
            fillColor=color_scheme.get(row['Line_id'], 'grey'),
            fillOpacity=0.7,
            weight=1
        ).add_to(m)

    # Add edges colored by line with layer control
    logging.info("Adding %s edges to map", network.number_of_edges())
    for source, target, key, data in network.edges(keys=True, data=True):
        line_id = data.get('line_id', 'unknown')
        line_color = color_scheme.get(line_id, 'black')

        source_row = station_data[station_data['UniqueId'] == source]
        target_row = station_data[station_data['UniqueId'] == target]

        if not source_row.empty and not target_row.empty:
            if pd.isna(source_row.iloc[0]['Latitude']) or pd.isna(target_row.iloc[0]['Latitude']):
                logging.debug(
                    "Skipping edge %s-%s, missing coordinates", source, target)
                continue
            coords = [
                [source_row.iloc[0]['Latitude'], source_row.iloc[0]['Longitude']],
                [target_row.iloc[0]['Latitude'], target_row.iloc[0]['Longitude']]
            ]

            polyline = folium.PolyLine(
                coords,
                color=line_color,
                weight=2,
                opacity=0.7,
                popup=f"Line: {str(line_id).replace('-', ' & ').capitalize()}"
            )

            # Add to line's feature group
            if line_id in line_groups:
                polyline.add_to(line_groups[line_id])
            else:
                polyline.add_to(m)

    # Add layer control to toggle lines
    folium.LayerControl().add_to(m)

    logging.info(
        "Plotted %s stations and %s edges", len(station_data), network.number_of_edges())
    return m


def main_local() -> None:
    """Main entry point for plotting station network from S3 or local files."""
    setup_logger()
    logging.info("Ensuring database files exist")
    ensure_files_exist()

    logging.info("Loading station network and data from S3")
    network_graph = extract_station_network_local()
    station_dataframe = extract_station_data_local()

    # Fallback to local files if S3 extraction failed
    if network_graph.number_of_nodes() == 0:
        logging.info("Network is empty, falling back to local files")
        network_graph = extract_station_network_local()

    if station_dataframe.empty:
        logging.info("Stations data is empty, falling back to local files")
        station_dataframe = extract_station_data_local()

    logging.info("Plotting station network")
    try:
        station_map = plot_station_network(network_graph, station_dataframe)
        station_map.save("stations/tube_network_map.html")
        logging.info("Map saved to stations/tube_network_map.html")
    except ValueError as e:
        logging.error("Failed to plot map: %s", e)
    except IOError as e:
        logging.error("Failed to save map to file: %s", e)


def main() -> None:
    """Main entry point for plotting station network from S3."""
    setup_logger()
    logging.info("Loading station network and data from S3")
    network_graph = extract_station_network()
    station_dataframe = extract_stations()

    logging.info("Plotting station network")
    try:
        station_map = plot_station_network(network_graph, station_dataframe)
        station_map.save("stations/tube_network_map.html")
        logging.info("Map saved to stations/tube_network_map.html")
    except ValueError as e:
        logging.error("Failed to plot map: %s", e)
    except IOError as e:
        logging.error("Failed to save map to file: %s", e)


if __name__ == "__main__":
    main()
