"""Create a network of stations from the TFL API."""

import logging
import time
from io import BytesIO
import boto3
import pandas as pd
import networkx as nx
from connect_nearby_stations import connect_nearby_stations
from get_sequenced_stops import get_sequenced_stops, get_line_stops_data
from get_travel_times import get_duration_data
from get_lines import get_lines
from api_utils import setup_logger


def add_edge_between_stations(
    G: nx.MultiGraph, station1: str, station2: str, line_id: str, duration: int
) -> None:
    """
    Add an edge between two stations in the graph G
    with the line_id and duration as attributes."""
    G.add_edge(station1, station2, line_id=line_id, duration=duration)


def get_stops_from_line(line_data: dict, line_id: str) -> list[dict]:
    """Extracts the stops from the line data."""
    stations = []
    if isinstance(line_data, dict) and "stopPointSequences" in line_data:
        for station_sequence in line_data["stopPointSequences"]:
            for station in station_sequence["stopPoint"]:
                if station.get("stationId"):
                    if station.get("stationId") not in [
                        s["UniqueId"] for s in stations
                    ]:
                        stations.append(
                            {
                                "UniqueId": station.get("stationId"),
                                "Name": station.get("name", station.get("stationId")),
                                "Latitude": station.get("lat"),
                                "Longitude": station.get("lon"),
                                "Line_id": line_id,
                            }
                        )
    return stations


def create_station_network() -> dict[str, pd.DataFrame | nx.MultiGraph]:
    """Create a station network from the TFL API and return network + stops data."""
    network = nx.MultiGraph()
    possible_lines = get_lines(mode="tube,dlr,elizabeth-line")
    direction = "all"
    stops = []
    for line_id in possible_lines:
        line_data = get_line_stops_data(line_id, direction)
        stops_line = get_stops_from_line(line_data, line_id)
        stops.extend(stops_line)
        line_branches = get_sequenced_stops(line_data)
        for branch in line_branches:
            for i in range(len(branch) - 1):
                station1 = branch[i]
                station2 = branch[i + 1]
                if network.has_edge(station1, station2):
                    edge_data_dict = network.get_edge_data(station1, station2)
                    edge_data = edge_data_dict[0]
                    if edge_data.get("line_id") == line_id:
                        logging.info(
                            "Edge already exists between %s and %s for line %s, skipping",
                            station1,
                            station2,
                            line_id,
                        )
                        continue
                    duration = edge_data.get("duration")
                    logging.info(
                        "Edge already exists between %s and %s for a different line, "
                        "using existing duration: %s minutes",
                        station1,
                        station2,
                        duration,
                    )
                else:
                    duration = get_duration_data(station1, station2)
                add_edge_between_stations(
                    network, station1, station2, line_id=line_id, duration=duration
                )
    stops_df = pd.DataFrame(stops)
    network = connect_nearby_stations(network, stops_df)
    logging.info(
        "Created station network with %s stations and %s edges",
        len(network.nodes),
        len(network.edges),
    )
    return {"stops_df": stops_df, "network": network}


def load_station_network_local(
    network_file_path: str = "stations/tube_network.graphml",
    station_file_path: str = "stations/Stations.csv",
) -> bool:
    """Load the station network data to the local directory."""
    try:
        stations_network_data = create_station_network()
        nx.write_graphml(
            stations_network_data.get(
                "network", nx.MultiGraph()), network_file_path
        )
        stations_network_data.get("stops_df", pd.DataFrame()).to_csv(
            station_file_path, index=False
        )
        logging.info(
            "Successfully loaded station network and data to local files")
        return True
    except Exception as e:
        logging.error(
            "Failed to load station network data to local files: %s", e)
        return False


def track_network_creation_time() -> None:
    """Track the time taken to create the station network."""
    start_time = time.time()
    create_station_network()
    end_time = time.time()
    logging.info(
        "Time taken to create station network: %.2f seconds", end_time - start_time
    )


def lambda_handler(event: dict = None, context: dict = None) -> dict:
    """Run the full pipeline and save it in a S3 bucket."""
    try:
        setup_logger()
        stations_network_data = create_station_network()
        network = stations_network_data.get("network", nx.MultiGraph())
        stops_df = stations_network_data.get("stops_df", pd.DataFrame())
        s3_client = boto3.client("s3")
        bucket_name = "c23-travel-simulation-bucket"

        graphml_bytes = BytesIO()
        nx.write_graphml(network, graphml_bytes)
        s3_client.put_object(
            Bucket=bucket_name,
            Key="processed/stations_network.graphml",
            Body=graphml_bytes.getvalue(),
        )
        logging.info(
            "Successfully uploaded network to S3 bucket %s", bucket_name)

        csv_bytes = stops_df.to_csv(index=False).encode()
        s3_client.put_object(
            Bucket=bucket_name, Key="processed/stations.csv", Body=csv_bytes
        )
        logging.info(
            "Successfully uploaded station data to S3 bucket %s", bucket_name)
        return {"statusCode": 200, "body": "Data processed and loaded successfully."}
    except Exception as e:
        logging.error("Failed to run pipeline and save to S3: %s", e)
        return {
            "statusCode": 500,
            "body": "Failed to run pipeline and save to S3: %s" % str(e),
        }


if __name__ == "__main__":
    lambda_handler()
