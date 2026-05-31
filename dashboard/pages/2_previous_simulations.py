import boto3
import streamlit as st
import json
import dotenv
import os
import pandas as pd
from io import StringIO
import folium
from streamlit_folium import st_folium

# Initialize S3 Client
s3_client = boto3.client("s3")


@st.cache_data(ttl=3600)  # Caches results for 1 hour
def get_simulation_folders(bucket_name, prefix=""):
    """
    Lists 'folders' (common prefixes) at a specific path in an S3 bucket.
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
            folders.append(folder_name)

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


# Create a color scale based on the time spent difference
def get_color(time_spent_diff, greatest_timesave):
    """Color code based on time spent difference."""
    if pd.isna(time_spent_diff):
        return "blue"  # No impact data
    elif time_spent_diff == greatest_timesave:
        return "red"
    elif time_spent_diff > 0:
        return "orange"
    else:
        return "green"


def remove_uninfluenced_stations(comparison_df) -> pd.DataFrame:
    """Filter out stations that have no change in demand."""
    # This would be where user station does not exist in the altered
    # simulation, so we only want to show stations that are affected
    return comparison_df[
        (comparison_df["nearest_station_altered"] != "User Station")
        & (comparison_df["alighting_station_altered"] != "User Station")
    ].copy()


def find_station_demand_changes(comparison_df):
    """Identify stations with the greatest increase or decrease in demand."""
    if comparison_df.empty:
        return pd.DataFrame()  # Return empty DataFrame if no data

    # Group by nearest station and sum the time spent differences
    station_impact_initial = comparison_df.groupby("nearest_station_baseline")[
        "time_spent_diff"
    ].sum()
    station_impact_ending = comparison_df.groupby("alighting_station_altered")[
        "time_spent_diff"
    ].sum()
    station_impact = station_impact_initial.add(station_impact_ending, fill_value=0)

    # Sort to find stations with greatest increase and decrease in demand
    station_impact = station_impact.sort_values()
    return station_impact.reset_index().rename(
        columns={
            "nearest_station_baseline": "Station",
            "time_spent_diff": "Total Time Spent Difference",
        }
    )


@st.cache_data(ttl=10)  # Cache the map creation for 10 seconds
def create_folium_map(station_data, comparison_df):
    """Creates a Folium map with station markers colored by impact."""
    # Create a base map centered around London
    m = folium.Map(location=[51.5074, -0.1278], zoom_start=12)

    # Merge station data with comparison data to get impact info
    station_demand_changes = find_station_demand_changes(comparison_df)
    merged_data = pd.merge(
        station_data,
        station_demand_changes,
        right_on="Station",
        left_on="Name",
        how="left",
    )
    greatest_timesave = station_demand_changes["Total Time Spent Difference"].min()

    for _, row in merged_data.iterrows():
        color = get_color(row["Total Time Spent Difference"], greatest_timesave)
        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=5,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=f"{row['Name']} (Time Spent Difference: {row['Total Time Spent Difference']:.2f} mins)",
        ).add_to(m)

    return m


def get_total_time_spent_diff(comparison_df):
    """Calculate the total time spent difference across all routes."""
    if comparison_df.empty:
        return 0
    return comparison_df["time_spent_diff"].sum()


def get_greatest_time_spent_diff(comparison_df):
    """Calculate the greatest time spent difference across all routes."""
    if comparison_df.empty:
        return 0
    return comparison_df[
        "time_spent_diff"
    ].min()  # Assuming negative is greatest timesave


def get_percentage_of_affected_routes(comparison_df, number_of_routes: int) -> float:
    """Calculate the percentage of routes affected by the proposed station."""
    if comparison_df.empty or number_of_routes == 0:
        return 0.0
    affected_routes = comparison_df.shape[0]
    return (affected_routes / number_of_routes) * 100


def plot_original_station_point(metadata, folium_map):
    """Plots the proposed station location on the map."""
    if "Latitude" not in metadata or "Longitude" not in metadata:
        st.warning(
            "Metadata does not contain Latitude and Longitude for the proposed station."
        )
        return folium_map
    lat = metadata.get("Latitude")
    lon = metadata.get("Longitude")
    folium.Marker(
        location=[lat, lon], icon=folium.Icon(color="purple"), popup="Proposed Station"
    ).add_to(folium_map)
    return folium_map


# Configuration
dotenv.load_dotenv()
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
BASE_PREFIX = "raw/"  # Leave empty "" if folders are at the root

st.title("Simulation Dashboard")

# 1. Fetch folders (Cached)
with st.spinner("Fetching available simulations from S3..."):
    available_folders = get_simulation_folders(BUCKET_NAME, BASE_PREFIX)

if not available_folders:
    st.warning("No simulation folders found.")
else:
    # 2. Dropdown Selector
    selected_folder = st.selectbox(
        "Select a Simulation Run:", options=available_folders, index=0
    )

    st.write(f"Selected Folder: `{selected_folder}`")

    # 3. Construct path to the metadata file inside the chosen folder
    metadata_key = f"{BASE_PREFIX}{selected_folder}/user_station.json"
    comparison_csv_key = f"{BASE_PREFIX}{selected_folder}/simulation_comparison.csv"

    st.subheader("Simulation Metadata")

    with st.spinner("Loading metadata..."):
        metadata = json.loads(get_folder_metadata(BUCKET_NAME, metadata_key))

        # Pretty print the JSON metadata on the dashboard
        st.json(metadata)

    st.subheader("Affected Routes")
    with st.spinner("Loading comparison data..."):
        comparison_df = get_comparison_csv(BUCKET_NAME, comparison_csv_key)

        if not comparison_df.empty:
            st.dataframe(comparison_df)
        else:
            st.warning("No comparison data available.")

    st.subheader("Simulation Impact Map")
    if not comparison_df.empty:
        station_data = get_station_data(BUCKET_NAME)
        if not station_data.empty:
            folium_map = create_folium_map(station_data, comparison_df)
            folium_map = plot_original_station_point(metadata, folium_map)
            st_folium(folium_map, width=700, height=500)
        else:
            st.warning("Cannot create map without station data.")
    else:
        st.warning("Cannot create map without comparison data.")

    st.subheader("Overall Impact Metrics")
    total_time_diff = get_total_time_spent_diff(comparison_df)
    greatest_time_diff = get_greatest_time_spent_diff(comparison_df)
    percentage_affected = get_percentage_of_affected_routes(
        comparison_df, metadata.get("number_of_passengers", 0)
    )
    st.metric("Total Time Spent Difference (mins)", f"{total_time_diff:.2f}")
    st.metric("Greatest Time Spent Difference (mins)", f"{greatest_time_diff:.2f}")
    st.metric("Percentage of Affected Routes", f"{percentage_affected:.2f}%")
