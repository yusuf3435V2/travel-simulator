import boto3
import streamlit as st
import json
import dotenv
import os
import pandas as pd
from io import StringIO
import folium
from streamlit_folium import st_folium
from s3_utils import (
    get_station_data,
    get_folder_metadata,
    get_comparison_csv,
    get_simulation_folders,
)
from df_analysis import (
    get_total_time_spent_diff,
    get_greatest_time_spent_diff,
    get_percentage_of_affected_routes,
)
from folium_functions import plot_original_station_point, create_folium_map


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
    )["Folder"]

    st.write(f"Selected Folder: `{selected_folder}`")

    # 3. Construct path to the metadata file inside the chosen folder
    metadata_key = f"{BASE_PREFIX}{selected_folder}/user_station.json"
    comparison_csv_key = f"{BASE_PREFIX}{selected_folder}/simulation_comparison.csv"

    st.subheader("Simulation Metadata")

    with st.spinner("Loading metadata..."):
        metadata = get_folder_metadata(BUCKET_NAME, metadata_key)

        # Pretty print the JSON metadata on the dashboard
        st.json(metadata)
        metadata = json.loads(metadata) if isinstance(metadata, str) else metadata

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
