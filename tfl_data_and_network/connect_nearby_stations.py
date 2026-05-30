"""This script will connect stations based on the condition that they have the same name, ensuring that the graph is able to account for tube/non-tube connections."""

from s3_utils import fetch_file_from_s3, upload_file_to_s3
import networkx as nx
import pandas as pd
import dotenv
import os


def get_station_data(bucket_name: str) -> pd.DataFrame:
    """Fetch station data from S3 and return as a DataFrame."""
    return fetch_file_from_s3(bucket_name, "processed/stations.csv")


def connect_nearby_stations(graph: nx.Graph, station_data: pd.DataFrame) -> nx.Graph:
    """Connect stations with the same name in the graph."""
    station_groups = station_data.groupby("Name")
    for name, group in station_groups:
        if len(group) > 1:
            station_ids = group["UniqueId"].tolist()
            for i in range(len(station_ids)):
                for j in range(i + 1, len(station_ids)):
                    if not graph.has_edge(station_ids[i], station_ids[j]):
                        graph.add_edge(station_ids[i], station_ids[j], weight=0)
    return graph


if __name__ == "__main__":
    dotenv.load_dotenv()
    bucket_name = os.getenv("S3_BUCKET_NAME")
    station_data = get_station_data(bucket_name)
    graph = nx.Graph()  # Replace with code to load your existing graph
    updated_graph = connect_nearby_stations(graph, station_data)
    # Code to save the updated graph back to S3 if needed
    graphml_data = nx.generate_graphml(updated_graph)
    upload_file_to_s3(
        bucket_name, "processed/stations_network.graphml", "\n".join(graphml_data)
    )
