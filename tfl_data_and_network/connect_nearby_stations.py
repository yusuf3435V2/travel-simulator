"""This script will connect stations based on the condition that they have the same name, ensuring that the graph is able to account for tube/non-tube connections."""

from s3_utils import fetch_file_from_s3, upload_file_to_s3
import networkx as nx
import pandas as pd
import dotenv
import os
import boto3
import logging


def fetch_df_from_s3(bucket_name: str, s3_key: str) -> pd.DataFrame:
    """Fetch passenger data from S3 and return as a DataFrame."""
    s3_client = boto3.client("s3")
    print(s3_key)
    try:
        obj = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        df = pd.read_csv(obj["Body"])
        logging.info(f"File {s3_key} loaded from S3 bucket {bucket_name}.")
        return df
    except Exception as e:
        logging.error(f"Error loading file {s3_key} from S3: {e}")
        return pd.DataFrame()  # Return empty DataFrame on error


def fetch_graph_from_s3(bucket_name: str) -> nx.Graph:
    """Fetch graph data from S3 and return as a NetworkX graph."""
    s3_client = boto3.client("s3")
    try:
        graph_file = s3_client.get_object(
            Bucket=bucket_name, Key="processed/stations_network.graphml"
        )
        file_content = graph_file["Body"].read().decode("utf-8").strip()
        return nx.parse_graphml(file_content)
    except Exception as e:
        logging.error(f"Error parsing graph from S3 file: {e}")
        return nx.Graph()  # Return empty graph on error


def get_station_data(bucket_name: str) -> pd.DataFrame:
    """Fetch station data from S3 and return as a DataFrame."""
    return fetch_df_from_s3(bucket_name, "processed/stations.csv")


def connect_nearby_stations(graph: nx.Graph, station_data: pd.DataFrame) -> nx.Graph:
    """Connect stations with the same name in the graph."""
    station_data["unsuffixed_name"] = station_data["Name"].apply(unsuffix_name)
    station_groups = station_data.groupby("unsuffixed_name")
    for name, group in station_groups:
        if len(group) > 1:
            station_ids = group["UniqueId"].tolist()
            for i in range(len(station_ids)):
                for j in range(i + 1, len(station_ids)):
                    if not graph.has_edge(station_ids[i], station_ids[j]):
                        graph.add_edge(station_ids[i], station_ids[j], duration=0, line_id="transfer")
    return graph


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


if __name__ == "__main__":
    dotenv.load_dotenv()
    bucket_name = os.getenv("S3_BUCKET_NAME")
    station_data = get_station_data(bucket_name)
    print(station_data)
    graph = fetch_graph_from_s3(bucket_name)
    updated_graph = connect_nearby_stations(graph, station_data)
    # Code to save the updated graph back to S3 if needed
    graphml_data = nx.generate_graphml(updated_graph)
    upload_file_to_s3(
        bucket_name, "processed/stations_network.graphml", "\n".join(graphml_data)
    )
