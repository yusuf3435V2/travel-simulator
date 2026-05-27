"""Creates a station network from the TFL API and saves it as a JSON file."""

import os
import json
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
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


def check_station_data_available():
    """Check if there is a station data file available in the 'stations' directory."""
    if not os.path.exists("stations/Stations.csv"):
        raise FileNotFoundError(
            """Station data file not found. 
            Please run separate_station_data.py to create the station data file."""
        )


def add_edge_between_stations(
        G: nx.Graph, station1: str, station2: str, line_id: str, duration: int) -> None:
    """Add an edge between two stations in the graph G 
    with the line_id and duration as attributes."""
    G.add_edge(station1, station2, line=line_id, duration=duration)


def draw_edge_colours(
    G: nx.Graph, pos: dict, possible_lines: list, color_scheme: dict
) -> None:
    """Draw edges with colors based on the line."""
    for line_id in possible_lines:
        # Default to black if not found
        line_color = color_scheme.get(line_id, "black")
        edges = [(u, v) for u, v, d in G.edges(
            data=True) if d.get("line") == line_id]
        nx.draw_networkx_edges(G, pos, edgelist=edges,
                               edge_color=line_color, width=1.5)


def create_station_network(station_data: pd.DataFrame) -> None:
    """Create a station network from the TFL API and save it as a JSON file."""
    G = nx.Graph()
    labels = {}
    color_scheme = create_colour_scheme()
    possible_lines = get_lines()
    direction = "all"
    for line_id in possible_lines:
        line_color = color_scheme.get(line_id, "black")
        print(f"Processing line: {line_id} with color: {line_color}")
        line_data = get_line_stops_data(line_id, direction)
        stops_branches = get_sequenced_stops(line_data)
        for stops in stops_branches:
            for i in range(len(stops) - 1):
                # check if the edge has already been made
                if G.has_edge(stops[i], stops[i + 1]):
                    print(
                        "found existing edge between: "
                        + stops[i]
                        + " and "
                        + stops[i + 1]
                    )
                    continue
                try:
                    corresponding_start_station_name = get_station_name(
                        stops[i], station_data
                    )
                    corresponding_end_station_name = get_station_name(
                        stops[i + 1], station_data
                    )
                    labels[stops[i]] = labels.get(
                        stops[i], corresponding_start_station_name)
                    labels[stops[i + 1]] = labels.get(
                        stops[i +
                              1], corresponding_end_station_name)
                    duration = get_duration_data(
                        stops[i], stops[i + 1])
                except ValueError:
                    print(
                        f"Could not find station name for ID: {stops[i]}, using ID as name."
                    )
                add_edge_between_stations(
                    G, stops[i], stops[i + 1], line_id, duration)
    pos = nx.spring_layout(G, k=0.5, iterations=50)
    nx.draw_networkx_nodes(G, pos, node_size=20, node_color="lightblue")

    # Draw edges with colors based on the line
    draw_edge_colours(G, pos, possible_lines, color_scheme)

    nx.draw_networkx_labels(G, pos=pos, labels=labels, font_size=6)
    plt.show()
    with open("station_network.json", "w") as f:
        json.dump(nx.node_link_data(G), f)


def load_separate_station_data() -> pd.DataFrame:
    """Load the separate station data from the 'stations' directory."""
    # This is a placeholder function. You would need to implement this to
    # load the station data from the files created by separate_station_data.py.
    return pd.read_csv("stations/Stations.csv", encoding="utf-8")


def get_station_name(station_id: str, station_data: pd.DataFrame) -> str:
    """Get the name of a station given its ID."""
    station_name = station_data[station_data["UniqueId"]
                                == station_id]["Name"].values
    if len(station_name) == 0:
        raise ValueError("Could not find station name for ID: " + station_id)
    if len(station_name) > 1:
        pass
    return station_name[0]


if __name__ == "__main__":
    setup_logger()
    check_station_data_available()
    stations = load_separate_station_data()
    print(stations.head())
    create_station_network(stations)
