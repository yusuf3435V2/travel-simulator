"""The main dashboard for the travel simulation app"""

import json
import time
import folium
import streamlit as st
from streamlit_folium import st_folium
from analysis import generate_recommendation_pdf
from botocore.exceptions import ClientError
import boto3
import os
import dotenv
from s3_utils import (
    get_station_data,
    get_comparison_csv,
)
from folium_functions import plot_original_station_point, create_folium_map
from df_analysis import (
    get_total_time_spent_diff,
    get_greatest_time_spent_diff,
    get_percentage_of_affected_routes,
)
import uuid

st.set_page_config(page_title="Travel Simulation Dashboard", layout="wide")

st.title("Travel Simulation Dashboard")
st.write(
    "Choose a proposed station location by typing coordinates or clicking on the map, "
    "then select the train line and run the simulation."
)
dotenv.load_dotenv()

# Global AWS Configuration
lambda_client = boto3.client("lambda")
s3_client = boto3.client("s3")
BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "your-simulation-bucket-name")
# Replace this file name with the exact file your simulation Lambda produces upon completion

TUBE_AND_RAIL_LINES = [
    "Bakerloo",
    "Central",
    "Circle",
    "District",
    "Hammersmith & City",
    "Jubilee",
    "Metropolitan",
    "Northern",
    "Piccadilly",
    "Victoria",
    "Waterloo & City",
    "DLR",
    "Elizabeth line",
]

line_to_id_mapping = {
    "Bakerloo": "bakerloo",
    "Central": "central",
    "Circle": "circle",
    "District": "district",
    "Hammersmith & City": "hammersmith-city",
    "Jubilee": "jubilee",
    "Metropolitan": "metropolitan",
    "Northern": "northern",
    "Piccadilly": "piccadilly",
    "Victoria": "victoria",
    "Waterloo & City": "waterloo-city",
    "DLR": "dlr",
    "Elizabeth line": "elizabeth",
}


# Helper to look for simulation outputs without downloading full payloads
def check_s3_for_completion(bucket, key):
    try:
        print(f"Checking S3 for key: {key}")
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError:
        return False


# Initialize Session States
if "proposed_lat" not in st.session_state:
    st.session_state.proposed_lat = None

if "proposed_lon" not in st.session_state:
    st.session_state.proposed_lon = None

if "selected_line" not in st.session_state:
    st.session_state.selected_line = TUBE_AND_RAIL_LINES[0]
    st.session_state.selected_line_id = line_to_id_mapping[
        st.session_state.selected_line
    ]

if "simulation_running" not in st.session_state:
    st.session_state.simulation_running = False

if "simulation_finished" not in st.session_state:
    st.session_state.simulation_finished = False

if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None

if "target_key" not in st.session_state:
    st.session_state.target_key = None

INPUT_DISABLED = st.session_state.simulation_running


st.subheader("1. Choose proposed station location")

input_method = st.radio(
    "How would you like to choose the location?",
    ["Type latitude/longitude", "Click on map"],
    disabled=INPUT_DISABLED,
)

if input_method == "Type latitude/longitude":
    col1, col2 = st.columns(2)

    with col1:
        typed_lat = st.number_input(
            "Latitude",
            value=51.5072,
            format="%.6f",
            disabled=INPUT_DISABLED,
        )

    with col2:
        typed_lon = st.number_input(
            "Longitude",
            value=-0.1276,
            format="%.6f",
            disabled=INPUT_DISABLED,
        )

    if st.button("Use typed coordinates", disabled=INPUT_DISABLED):
        st.session_state.proposed_lat = typed_lat
        st.session_state.proposed_lon = typed_lon
        st.session_state.simulation_finished = False
        st.session_state.pdf_bytes = None

else:
    st.write("Click on the map to set the proposed station location.")

    m = folium.Map(
        location=[51.5072, -0.1276],
        zoom_start=11,
    )

    if st.session_state.proposed_lat is not None:
        folium.Marker(
            [
                st.session_state.proposed_lat,
                st.session_state.proposed_lon,
            ],
            popup="Proposed Station",
            icon=folium.Icon(color="green", icon="star"),
        ).add_to(m)

    map_data = st_folium(
        m,
        height=600,
        width=1200,
        key="location_picker_map",
    )

    if not INPUT_DISABLED and map_data and map_data.get("last_clicked"):
        st.session_state.proposed_lat = map_data["last_clicked"]["lat"]
        st.session_state.proposed_lon = map_data["last_clicked"]["lng"]
        st.session_state.simulation_finished = False
        st.session_state.pdf_bytes = None
        st.rerun()

st.subheader("2. Choose proposed train line")

selected_line = st.selectbox(
    "Which line would the proposed station be on?",
    TUBE_AND_RAIL_LINES,
    index=TUBE_AND_RAIL_LINES.index(st.session_state.selected_line),
    disabled=INPUT_DISABLED,
)
print(f"Selected line: {selected_line}")

if not INPUT_DISABLED and selected_line != st.session_state.selected_line:
    st.session_state.selected_line = selected_line
    st.session_state.selected_line_id = line_to_id_mapping[selected_line]
    st.session_state.simulation_finished = False
    st.session_state.pdf_bytes = None


st.subheader("3. Confirm and run simulation")

if st.session_state.proposed_lat is None or st.session_state.proposed_lon is None:
    st.warning("Please choose a proposed station location first.")
else:
    st.info(
        f"Selected location: "
        f"{st.session_state.proposed_lat:.6f}, "
        f"{st.session_state.proposed_lon:.6f}"
    )

    st.info(f"Selected line: {st.session_state.selected_line}")

    # Render Active or Disabled button based on execution locker
    if not st.session_state.simulation_running:
        if st.button("Confirm and run simulation", type="primary"):
            st.session_state.simulation_running = True
            st.session_state.simulation_finished = False
            st.session_state.pdf_bytes = None
            st.rerun()  # Instantly refreshes UI to gray out input components and lock button
    else:
        st.button("Simulation Processing in AWS...", disabled=True)

    # Passive Background Polling Engine Execution Block
    if st.session_state.simulation_running and not st.session_state.simulation_finished:
        current_time = int(time.time())
        unique_id = str(uuid.uuid4())
        st.session_state.target_key = f"raw/{unique_id}/simulation_comparison.csv"  # Adjust this path based on your Lambda's output structure
        print("Running following station")
        print(
            {
                "UniqueId": unique_id,
                "Latitude": st.session_state.proposed_lat,
                "Longitude": st.session_state.proposed_lon,
                "Line_id": st.session_state.selected_line_id,
                "Name": "User Proposed Station",
            }
        )
        with st.spinner("Invoking remote AWS Lambda engine..."):
            lambda_client.invoke(
                FunctionName=os.environ.get("SIMULATION_LAMBDA_ARN"),
                InvocationType="Event",  # Asynchronous invocation
                Payload=json.dumps(
                    {
                        "UniqueId": unique_id,
                        "Latitude": st.session_state.proposed_lat,
                        "Longitude": st.session_state.proposed_lon,
                        "Line_id": st.session_state.selected_line_id,
                        "Name": "User Proposed Station",
                    }
                ),
            )
            st.session_state.simulation_running = True
            st.toast("Lambda successfully triggered!")

        # Visual elements tracking progress loop
        status_message = st.empty()
        progress_bar = st.progress(0)

        max_retries = 60  # 5 Minutes Max (60 attempts * 5 seconds sleep)
        simulation_success = False

        for attempt in range(max_retries):
            status_message.text(
                f"⏳ Processing simulation pipeline... Checking S3 for outputs (Attempt {attempt + 1}/{max_retries})"
            )
            progress_bar.progress(min((attempt + 1) / max_retries, 0.95))

            if check_s3_for_completion(BUCKET_NAME, st.session_state.target_key):
                simulation_success = True
                break

            time.sleep(5)

        status_message.empty()
        progress_bar.empty()

        if simulation_success:
            # Code block for compiling the final localized PDF report on completion
            # st.session_state.pdf_bytes = generate_recommendation_pdf(
            #     proposed_lat=st.session_state.proposed_lat,
            #     proposed_lon=st.session_state.proposed_lon,
            #     selected_line=st.session_state.selected_line,
            # )
            st.session_state.simulation_running = False
            st.session_state.simulation_finished = True
            st.success("Simulation finished successfully!")
            st.balloons()
            st.rerun()
        else:
            st.error("❌ Simulation timed out or failed to write results back to S3.")
            st.session_state.simulation_running = False
            st.rerun()


if st.session_state.simulation_finished:
    st.subheader("Simulation Results")

    st.write("Results parsed directly from complete run metrics:")

    st.write(
        {
            "proposed_lat": st.session_state.proposed_lat,
            "proposed_lon": st.session_state.proposed_lon,
            "selected_line": st.session_state.selected_line,
        }
    )

    if st.session_state.target_key is None:
        st.error("Target key not found. Please run the simulation again.")
    else:
        metadata = {
            "Latitude": st.session_state.proposed_lat,
            "Longitude": st.session_state.proposed_lon,
            "Line_id": st.session_state.selected_line_id,
            "Name": "User Proposed Station",
            "number_of_passengers": 32000,  # Placeholder, replace with actual metadata
        }
        comparison_df = get_comparison_csv(BUCKET_NAME, st.session_state.target_key)

    if st.session_state.pdf_bytes:
        st.download_button(
            label="Download recommendation report",
            data=st.session_state.pdf_bytes,
            file_name="travel_simulation_recommendation.pdf",
            mime="application/pdf",
        )

    if st.button("Reset Dashboard for New Run"):
        st.session_state.simulation_finished = False
        st.session_state.simulation_running = False
        st.session_state.pdf_bytes = None
        st.rerun()

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
