"""Create a network of stations from the TFL API."""

import logging

import networkx as nx
from get_sequenced_stops import get_sequenced_stops, get_line_stops_data
from get_travel_times import get_duration_data
from get_lines import get_lines
from api_utils import setup_logger


def create_colour_scheme():
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


def add_edge_between_stations(
    G: nx.Graph, station1: str, station2: str, line_id: str, duration: int
) -> None:
    """Add an edge between two stations in the graph G with the line_id and duration as attributes."""
    G.add_edge(station1, station2, line=line_id, duration=duration)


def get_stops_from_line_2(line_data: dict, line_id: str) -> list[dict]:
    """Extracts the stops from the line data."""
    stations = []
    if isinstance(line_data, dict) and "stations" in line_data:
        for station in line_data["stations"]:
            if station.get("stationId"):
                stations.append({
                    "UniqueId": station.get("stationId"),
                    "Name": station["name"],
                    "Latitude": station["lat"],
                    "Longitude": station["lon"],
                    "Line_id": line_id
                })
    return stations


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


def create_station_network() -> None:
    """Create a station network from the TFL API and save it as a JSON file."""
    network = nx.Graph()
    possible_lines = get_lines()
    # color_scheme = create_colour_scheme()
    direction = "all"
    stops = []
    for line_id in possible_lines:
        line_data = get_line_stops_data(line_id, direction)
        stops_line = get_stops_from_line(line_data, line_id)
        stops.append(stops_line)
        line_branches = get_sequenced_stops(line_data)
        for branch in line_branches:
            for i in range(len(branch) - 1):
                if network.has_edge(branch[i], branch[i + 1]):
                    edge_data = network.get_edge_data(branch[i], branch[i + 1])
                    if edge_data.get('line') == line_id:
                        logging.info(
                            f"Edge already exists between {branch[i]} and {branch[i + 1]} for line {line_id}, skipping")
                        continue
                duration = get_duration_data(branch[i], branch[i + 1])
                add_edge_between_stations(
                    network, branch[i], branch[i +
                                               1], line_id=line_id, duration=duration)
    network.nodes()
    return stops


if __name__ == "__main__":
    setup_logger()
    create_station_network()
