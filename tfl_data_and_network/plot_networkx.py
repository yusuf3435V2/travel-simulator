"""Plot the stations network using NetworkX and Folium."""

import logging
import os
import pandas as pd
import networkx as nx
import folium
from api_utils import setup_logger
from create_stations_network import load_station_network_local


def create_colour_scheme() -> dict:
    """Create a colour scheme for the different lines."""
    return {
        "bakerloo": "brown",
        "central": "red",
        "circle": "yellow",
        "district": "green",
        "hammersmith-city": "pink",
        "jubilee": "grey",
        "metropolitan": "purple",
        "northern": "black",
        "piccadilly": "darkblue",
        "victoria": "lightblue",
        "waterloo-city": "cyan",
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


def extract_station_network_local(file_path: str = "stations/tube_network.graphml") -> nx.Graph:
    """Load the station network from a .graphml file, extracting from API if missing."""
    # Ensure file exists by extracting from API if necessary
    if not ensure_files_exist(network_file_path=file_path):
        logging.error("Failed to ensure network file exists at %s", file_path)
        return nx.Graph()

    try:
        return nx.read_graphml(file_path)
    except Exception as e:
        logging.error("Failed to read network file at %s: %s", file_path, e)
        return nx.Graph()


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


def plot_station_network(network: nx.Graph, station_data: pd.DataFrame) -> folium.Map:
    """Plot the station network using Folium with colored edges."""
    if len(station_data) == 0:
        logging.error("Station data is empty, cannot plot map")
        raise ValueError("Cannot plot map with empty station data")

    if network.number_of_nodes() == 0:
        logging.warning("Network has no nodes, plotting station markers only")

    color_scheme = create_colour_scheme()

    # Calculate center of map
    center_lat = station_data['Latitude'].mean()
    center_lon = station_data['Longitude'].mean()

    # Create Folium map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

    # Add stations as markers
    logging.info("Adding %s station markers to map", len(station_data))
    for _, row in station_data.iterrows():
        if pd.isna(row['Latitude']) or pd.isna(row['Longitude']):
            logging.warning(
                "Station %s has missing coordinates, skipping", row['Name'])
            continue
        folium.CircleMarker(
            location=[row['Latitude'], row['Longitude']],
            radius=1,
            popup=row['Name'],
            color='blue',
            fill=True,
            fillColor='blue',
            fillOpacity=0.4
        ).add_to(m)

    # Add edges colored by line
    logging.info("Adding %s edges to map", network.number_of_edges())
    for source, target, data in network.edges(data=True):
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

            folium.PolyLine(coords, color=line_color,
                            weight=2, opacity=0.7).add_to(m)

    logging.info(
        "Plotted %s stations and %s edges", len(station_data), network.number_of_edges())
    return m


if __name__ == "__main__":
    setup_logger()
    logging.info("Ensuring database files exist")
    ensure_files_exist()
    
    logging.info("Loading station network and data")
    network_graph = extract_station_network_local()
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
