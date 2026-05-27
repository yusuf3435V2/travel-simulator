"""Create a network of stations from the TFL API."""

import logging
import time
import os
import pandas as pd
import networkx as nx
from get_sequenced_stops import get_sequenced_stops, get_line_stops_data
from get_travel_times import get_duration_data
from get_lines import get_lines
from api_utils import setup_logger


def add_edge_between_stations(
    G: nx.Graph, station1: str, station2: str, line_id: str, duration: int
) -> None:
    """Add an edge between two stations in the graph G with the line_id and duration as attributes."""
    G.add_edge(station1, station2, line_id=line_id, duration=duration)


# def get_stops_from_line_2(line_data: dict, line_id: str) -> list[dict]:
#     """Extracts the stops from the line data."""
#     stations = []
#     if isinstance(line_data, dict) and "stations" in line_data:
#         for station in line_data["stations"]:
#             if station.get("stationId"):
#                 stations.append({
#                     "UniqueId": station.get("stationId"),
#                     "Name": station["name"],
#                     "Latitude": station["lat"],
#                     "Longitude": station["lon"],
#                     "Line_id": line_id
#                 })
#     return stations


def get_stops_from_line(line_data: dict, line_id: str) -> list[dict]:
    """Extracts the stops from the line data."""
    stations = []
    if isinstance(line_data, dict) and "stopPointSequences" in line_data:
        for station_sequence in line_data["stopPointSequences"]:
            for station in station_sequence["stopPoint"]:
                if station.get("stationId"):
                    if station.get("stationId") not in [s["UniqueId"] for s in stations]:
                        stations.append({
                            "UniqueId": station.get("stationId"),
                            "Name": station.get("name", station.get("stationId")),
                            "Latitude": station.get("lat"),
                            "Longitude": station.get("lon"),
                            "Line_id": line_id
                        })
    return stations


def create_station_network(network_file_path: str = "stations/tube_network.graphml",
                           station_file_path: str = "stations/Stations.csv") -> dict[str, pd.DataFrame | nx.Graph]:
    """Create a station network from the TFL API and save it as a .graphml file."""
    network = nx.Graph()
    possible_lines = get_lines(mode="tube")
    direction = "all"
    stops = []
    for line_id in possible_lines:
        line_data = get_line_stops_data(line_id, direction)
        stops_line = get_stops_from_line(line_data, line_id)
        stops.extend(stops_line)
        line_branches = get_sequenced_stops(line_data)
        for branch in line_branches:
            for i in range(len(branch) - 1):
                if network.has_edge(branch[i], branch[i + 1]):
                    edge_data = network.get_edge_data(branch[i], branch[i + 1])
                    if edge_data.get('line_id') == line_id:
                        logging.info(
                            f"Edge already exists between {branch[i]} and {branch[i + 1]} for line {line_id}, skipping")
                        continue
                    duration = edge_data.get('duration')
                    logging.info(
                        f"""Edge already exists between {branch[i]} and {branch[i + 1]} for a different line, 
                        using existing duration: {duration} seconds""")
                else:
                    duration = get_duration_data(branch[i], branch[i + 1])
                add_edge_between_stations(
                    network, branch[i], branch[i + 1], line_id=line_id, duration=duration)
    nx.write_graphml(network, network_file_path)
    stops_df = pd.DataFrame(stops)
    stops_df.to_csv(station_file_path, index=False)
    return {'stops_df': stops_df, 'network': network}


def track_network_creation_time() -> None:
    """Track the time taken to create the station network."""
    start_time = time.time()
    create_station_network()
    end_time = time.time()
    logging.info(
        f"Time taken to create station network: {end_time - start_time:.2f} seconds")


def load_station_network(file_path: str = "stations/tube_network.graphml") -> nx.Graph:
    """Load the station network from a .graphml file."""
    if not os.path.exists(file_path):
        logging.error(
            f"Network file not found at {file_path}. Please run create_station_network() to create the network file.")
        create_station_network(network_file_path=file_path)
    return nx.read_graphml(file_path)


def load_station_data(file_path: str = "stations/Stations.csv") -> pd.DataFrame:
    """Load the station data from a .csv file."""
    if not os.path.exists(file_path):
        logging.error(
            f"Station data file not found at {file_path}. Please run create_station_network() to create the station data file.")
        create_station_network(station_file_path=file_path)
    return pd.read_csv(file_path)



if __name__ == "__main__":
    setup_logger()
    track_network_creation_time()
