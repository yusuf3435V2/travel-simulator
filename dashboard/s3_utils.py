import boto3
import json
import pandas as pd
from io import StringIO
import streamlit as st


s3_client = boto3.client("s3")


def get_comparison_csv(bucket_name, bucket_path):
    """
    Fetches a CSV file from S3 and returns it as a DataFrame.
    """
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=bucket_path)
        csv_content = response["Body"].read().decode("utf-8")
        return pd.read_csv(StringIO(csv_content))
    except Exception as e:
        st.error(f"Could not load comparison CSV: {str(e)}")
        return pd.DataFrame()  # Return empty DataFrame on error


@st.cache_data(ttl=10)  # Caches results for 1 hour
def get_simulation_folders(bucket_name, prefix=""):
    """
    Lists 'folders' (common prefixes) at a specific path in an S3 bucket,
    and returns latitude and longitude from each folder's user_station.json.
    """
    # Ensure the prefix ends with a slash if it's not empty
    if prefix and not prefix.endswith("/"):
        prefix += "/"

    response = s3_client.list_objects_v2(
        Bucket=bucket_name, Prefix=prefix, Delimiter="/"
    )

    folders = []
    # 'CommonPrefixes' contains the "folders"
    if "CommonPrefixes" in response:
        for cp in response["CommonPrefixes"]:
            # e.g., "simulations/run_01/" -> "run_01"
            folder_name = cp["Prefix"].replace(prefix, "").strip("/")
            folder_path = cp["Prefix"]

            # Fetch user_station.json from the folder
            metadata = get_folder_metadata(
                bucket_name, f"{folder_path}user_station.json"
            )
            metadata = json.loads(metadata) if isinstance(metadata, str) else metadata

            if "Error" not in metadata:
                latitude = metadata.get("Latitude")
                longitude = metadata.get("Longitude")
                folders.append(
                    {
                        "Latitude": latitude,
                        "Longitude": longitude,
                        "Folder": folder_name,
                    }
                )
            else:
                folders.append(
                    {"Latitude": None, "Longitude": None, "Folder": folder_name}
                )

    return folders


def get_station_data(bucket_name):
    """Fetch station data from S3 and return as a DataFrame."""
    try:
        obj = s3_client.get_object(Bucket=bucket_name, Key="processed/stations.csv")
        df = pd.read_csv(obj["Body"])
        return df
    except Exception as e:
        st.error(f"Error loading station data from S3: {e}")
        return pd.DataFrame()  # Return empty DataFrame on error


def get_folder_metadata(bucket_name, bucket_path):
    """
    Fetches and parses a metadata JSON file from a specific S3 path.
    """
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=bucket_path)
        metadata_content = response["Body"].read().decode("utf-8")
        return json.loads(metadata_content)
    except Exception as e:
        return {"Error": f"Could not load metadata: {str(e)}"}
