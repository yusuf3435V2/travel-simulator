import boto3
import pandas as pd
import networkx as nx
import logging
import dotenv
import os


def load_env_variables() -> str:
    """Loads environment variables from a .env file."""
    dotenv.load_dotenv()
    bucket_name = os.getenv("S3_BUCKET_NAME")
    if not bucket_name:
        raise ValueError("S3_BUCKET_NAME not found in environment variables.")
    return bucket_name


def fetch_file_from_s3(bucket_name: str, s3_key: str) -> pd.DataFrame:
    """Fetch passenger data from S3 and return as a DataFrame."""
    s3_client = boto3.client("s3")
    try:
        obj = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        df = pd.read_csv(obj["Body"])
        logging.info(f"File {s3_key} loaded from S3 bucket {bucket_name}.")
        return df
    except Exception as e:
        logging.error(f"Error loading file from S3: {e}")
        return pd.DataFrame()  # Return empty DataFrame on error


def fetch_passenger_data_from_s3(bucket_name: str) -> pd.DataFrame:
    """Fetch passenger data from S3 and return as a DataFrame."""
    return fetch_file_from_s3(bucket_name, "processed/passengers.csv")


def fetch_station_data_from_s3(bucket_name: str) -> pd.DataFrame:
    """Fetch station data from S3 and return as a DataFrame."""
    return fetch_file_from_s3(bucket_name, "processed/Stations.csv")


def fetch_graph_from_s3(bucket_name: str) -> nx.Graph:
    """Fetch graph data from S3 and return as a NetworkX graph."""
    s3_client = boto3.client("s3")
    graph_file = s3_client.get_object(
        Bucket=bucket_name, Key="processed/stations_network.graphml"
    )
    try:
        file_content = graph_file["Body"].read().decode("utf-8").strip()
        return nx.parse_graphml(file_content)
    except Exception as e:
        logging.error(f"Error parsing graph from S3 file: {e}")
        return nx.Graph()  # Return empty graph on error


def check_baseline_exists_in_s3() -> bool:
    """Checks if the baseline simulation results file exists in S3."""
    s3_client = boto3.client("s3")
    bucket_name = load_env_variables()
    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix="raw/")
        for obj in response.get("Contents", []):
            if "BASELINE.csv" in obj["Key"]:
                return True
        return False
    except Exception as e:
        print(f"Error checking for baseline file in S3: {e}")
        return False


def save_results_to_s3(file_path: str, bucket_name: str, s3_key: str):
    """Saves a file to an S3 bucket."""
    s3_client = boto3.client("s3")
    try:
        s3_client.upload_file(file_path, bucket_name, s3_key)
        print(
            f"File {file_path} uploaded to S3 bucket {bucket_name} with key {s3_key}."
        )
    except Exception as e:
        print(f"Error uploading file to S3: {e}")


def load_results_from_s3(bucket_name: str, s3_key: str) -> pd.DataFrame:
    """Loads a CSV file from S3 into a DataFrame."""
    s3_client = boto3.client("s3")
    try:
        obj = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        df = pd.read_csv(obj["Body"])
        print(f"File {s3_key} loaded from S3 bucket {bucket_name}.")
        return df
    except Exception as e:
        print(f"Error loading file from S3: {e}")
        return pd.DataFrame()  # Return empty DataFrame on error
