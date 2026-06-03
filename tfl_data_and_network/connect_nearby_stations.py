"""This script will connect stations based on the condition that they have the same name, ensuring that the graph is able to account for tube/non-tube connections."""

import networkx as nx
import pandas as pd
import logging


def unsuffix_name(station_name: str) -> str:
    """Remove suffixes like ' Underground Station' from station names."""
    suffixes = [
        " Underground Station",
        " DLR Station",
        " Elizabeth Line Station",
        " Rail Station",
        " Underground",
    ]
    # If station name contains a "(", remove this and everything after it as well
    if "(" in station_name:
        station_name = station_name.split("(")[0].strip()
    for suffix in suffixes:
        if station_name.lower().endswith(suffix.lower()):
            return station_name[: -len(suffix)].strip()
    return station_name


def connect_nearby_stations(graph: nx.Graph, station_data: pd.DataFrame) -> nx.Graph:
    """Connect stations with the same name in the graph."""
    if "Name" not in station_data.columns or "UniqueId" not in station_data.columns:
        logging.error(
            "Station data must contain 'Name' and 'UniqueId' columns.")
        return graph
    station_data["unsuffixed_name"] = station_data["Name"].apply(unsuffix_name)
    station_groups = station_data.groupby("unsuffixed_name")
    for name, group in station_groups:
        if len(group) > 1:
            station_ids = group["UniqueId"].tolist()
            for i in range(len(station_ids)):
                for j in range(i + 1, len(station_ids)):
                    if not graph.has_edge(station_ids[i], station_ids[j]):
                        graph.add_edge(
                            station_ids[i],
                            station_ids[j],
                            duration=0,
                            line_id="transfer",
                        )
    return graph
