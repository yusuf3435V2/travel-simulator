"""The main dashboard for the travel simulation app"""

import json
import time
import folium
import streamlit as st
from streamlit_folium import st_folium
from analysis import generate_recommendation_pdf
from botocore.exceptions import ClientError
import requests as req
import boto3
import os
import dotenv

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
TARGET_OUTPUT_KEY = "raw/user_station_1/simulation_comparison.csv"

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


# Helper to look for simulation outputs without downloading full payloads
def check_s3_for_completion(bucket, key):
    try:
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

if "simulation_running" not in st.session_state:
    st.session_state.simulation_running = False

if "simulation_finished" not in st.session_state:
    st.session_state.simulation_finished = False

if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None

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

if not INPUT_DISABLED and selected_line != st.session_state.selected_line:
    st.session_state.selected_line = selected_line
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
        with st.spinner("Invoking remote AWS Lambda engine..."):
            lambda_client.invoke(
                FunctionName=os.environ.get("SIMULATION_LAMBDA_ARN"),
                InvocationType="Event",  # Asynchronous invocation
                Payload=json.dumps(
                    {
                        "UniqueId": "user_station_1",
                        "Latitude": st.session_state.proposed_lat,
                        "Longitude": st.session_state.proposed_lon,
                        "Line_id": st.session_state.selected_line,
                        "Name": "User Proposed Station",
                    }
                ),
            )
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

            if check_s3_for_completion(BUCKET_NAME, TARGET_OUTPUT_KEY):
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
