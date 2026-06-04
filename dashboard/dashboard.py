"""The main dashboard for the travel simulation app"""

# Standard library imports
import json
import os
import time
import uuid

# Third-party imports
import boto3
import dotenv
import folium
import streamlit as st
from botocore.exceptions import ClientError
from streamlit_folium import st_folium

# Local imports
from analysis import generate_recommendation_pdf
from df_analysis import (
    get_total_time_spent_diff,
    get_greatest_time_spent_diff,
    get_percentage_of_affected_routes,
    get_affected_routes,
    get_demand_impact_ranges,
    create_top_affected_routes_chart,
    create_station_demand_impact_chart,
    create_top_time_saving_routes_chart
)
from folium_functions import plot_original_station_point, create_folium_map
from kml_export import generate_kmz_bytes
from s3_utils import (
    get_station_data,
    get_comparison_csv,
)
from stations_choropleth import create_choropleth


# Helper to look for simulation outputs without downloading full payloads
def check_s3_for_completion(bucket, key):
    try:
        print("Checking S3 for key: %s" % key)
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError:
        return False


st.set_page_config(
    page_title="London Station Simulation",
    page_icon="🚆",
    layout="centered",
)

st.markdown(
    """
    <style>
    .main {
        background-color: #f5f8fc;
    }

    .lss-hero {
        background: linear-gradient(135deg, #003b8f 0%, #0057c2 100%);
        padding: 28px 32px;
        border-radius: 18px;
        margin-bottom: 24px;
        color: white;
    }

    .lss-hero h1 {
        margin-bottom: 4px;
        font-size: 2.4rem;
        font-weight: 800;
    }

    .lss-hero p {
        font-size: 1.05rem;
        opacity: 0.95;
    }

    .step-card {
        background-color: white;
        padding: 20px;
        border-radius: 14px;
        border: 1px solid #d9e4f5;
        margin-bottom: 18px;
        box-shadow: 0 2px 8px rgba(0, 59, 143, 0.08);
    }

    .section-title {
        color: #003b8f;
        font-weight: 700;
        margin-bottom: 8px;
    }

    div.stButton > button:first-child {
        background-color: #003b8f;
        color: white;
        border-radius: 10px;
        border: none;
        padding: 0.6rem 1.2rem;
        font-weight: 700;
    }

    div.stButton > button:first-child:hover {
        background-color: #0057c2;
        color: white;
    }

    div[data-testid="stMetric"] {
        background-color: white;
        border: 1px solid #d9e4f5;
        padding: 16px;
        border-radius: 14px;
    }

    .block-container {
        max-width: 1100px;
        margin: auto;
        padding-top: 2rem;

    }
    </style>
    """,
    unsafe_allow_html=True,
)


col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.image("dashboard/lss_logo.png", width=700)

st.markdown(
    """
    <div style="
        width: 80%;
        height: 4px;
        margin: 10px auto 30px auto;
        background: linear-gradient(
            90deg,
            transparent 0%,
            #003b8f 15%,
            #0057c2 50%,
            #003b8f 85%,
            transparent 100%
        );
        border-radius: 10px;
    ">
    </div>
    """,
    unsafe_allow_html=True,
)

dotenv.load_dotenv()

# Global AWS Configuration
lambda_client = boto3.client("lambda")
s3_client = boto3.client("s3")
BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "your-simulation-bucket-name")

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

if "proposed_lat" not in st.session_state:
    st.session_state.proposed_lat = None

if "proposed_lon" not in st.session_state:
    st.session_state.proposed_lon = None

if "selected_line" not in st.session_state:
    st.session_state.selected_line = TUBE_AND_RAIL_LINES[0]
    st.session_state.selected_line_id = line_to_id_mapping[TUBE_AND_RAIL_LINES[0]]

if "simulation_running" not in st.session_state:
    st.session_state.simulation_running = False

if "simulation_finished" not in st.session_state:
    st.session_state.simulation_finished = False

if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None

if "kmz_bytes" not in st.session_state:
    st.session_state.kmz_bytes = None

INPUT_DISABLED = st.session_state.simulation_running



if "input_method" not in st.session_state:
    st.session_state.input_method = "Type latitude/longitude"


def set_input_method(method):
    st.session_state.input_method = method
    st.session_state.simulation_finished = False
    st.session_state.pdf_bytes = None
    st.session_state.kmz_bytes = None


unused_left, centre, unused_right = st.columns([3, 4, 2])
with centre:
    st.markdown(
        '<h3 class="section-title">1. Choose proposed station location</h3>',
        unsafe_allow_html=True,
    )

unused_left, centre, unused_right = st.columns([3, 4, 2])
with centre:

    method_col1, method_col2 = st.columns(2)

    with method_col1:
        st.button(
            "Type latitude/longitude",
            disabled=INPUT_DISABLED,
            use_container_width=True,
            on_click=set_input_method,
            args=("Type latitude/longitude",),
        )

    with method_col2:
        st.button(
            "Click on map",
            disabled=INPUT_DISABLED,
            use_container_width=True,
            on_click=set_input_method,
            args=("Click on map",),
        )


if st.session_state.input_method == "Type latitude/longitude":
    col1, col2 = st.columns([5, 5])

    with col1:
        typed_lat = st.number_input(
            "Latitude",
            value=51.5072,
            format="%.6f",
            disabled=INPUT_DISABLED,
            key="typed_lat",
        )

    with col2:
        typed_lon = st.number_input(
            "Longitude",
            value=-0.1276,
            format="%.6f",
            disabled=INPUT_DISABLED,
            key="typed_lon",
        )

    left, centre, right = st.columns([5, 4, 2])

    with centre:
        if st.button("Use typed coordinates", disabled=INPUT_DISABLED):
            st.session_state.proposed_lat = typed_lat
            st.session_state.proposed_lon = typed_lon
            st.session_state.simulation_finished = False
            st.session_state.pdf_bytes = None
            st.session_state.kmz_bytes = None
            st.rerun()

elif st.session_state.input_method == "Click on map":
    unused_left, centre, unused_right = st.columns([3, 4, 2])

    with centre:

        with st.spinner("Loading map..."):
            m = create_choropleth()

        if m is None:
            st.error("Could not load choropleth map.")
            st.stop()

        if st.session_state.proposed_lat is not None:
            proposed_location = [
                st.session_state.proposed_lat,
                st.session_state.proposed_lon,
            ]

            folium.Marker(
                proposed_location,
                popup="Proposed Station",
                icon=folium.Icon(color="green", icon="star"),
            ).add_to(m)

            folium.Circle(
                location=proposed_location,
                radius=800,
                popup="800m walking catchment",
                color="green",
                fill=True,
                fill_color="green",
                fill_opacity=0.15,
                weight=2,
            ).add_to(m)

    left, centre, right = st.columns([1, 20, 1])

    
    map_data = st_folium(
        m,
        height=600,
        use_container_width=True,
        key="location_picker_map",
        returned_objects=["last_clicked"],
    )

    if not INPUT_DISABLED and map_data and map_data.get("last_clicked"):
        st.session_state.proposed_lat = map_data["last_clicked"]["lat"]
        st.session_state.proposed_lon = map_data["last_clicked"]["lng"]
        st.session_state.simulation_finished = False
        st.session_state.pdf_bytes = None
        st.session_state.kmz_bytes = None
        st.rerun()

    # Click handling is performed above; avoid duplicated state updates/reruns.


unused_left, centre, unused_right = st.columns([3, 4, 2])

with centre:
    st.markdown('<h3 class="section-title">2. Choose proposed train line</h3>',
                unsafe_allow_html=True)

    selected_line = st.selectbox(
        "Which line would the proposed station be on?",
        TUBE_AND_RAIL_LINES,
        index=TUBE_AND_RAIL_LINES.index(st.session_state.selected_line),
        disabled=INPUT_DISABLED,
    )
# Debug logging removed (Streamlit reruns frequently).

if not INPUT_DISABLED and selected_line != st.session_state.selected_line:
    st.session_state.selected_line = selected_line
    st.session_state.selected_line_id = line_to_id_mapping[selected_line]
    st.session_state.simulation_finished = False
    st.session_state.pdf_bytes = None
    st.session_state.kmz_bytes = None

left, centre, right = st.columns([3, 4, 2])

with centre:
    st.markdown('<h3 class="section-title">3. Confirm and run simulation</h3>',
                unsafe_allow_html=True)

if st.session_state.proposed_lat is None or st.session_state.proposed_lon is None:
    with centre:
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
        unused_left, centre, unused_right = st.columns([4.3, 4, 2])
        with centre:
            if st.button("Confirm and run simulation", type="primary"):
                st.session_state.simulation_running = True
                st.session_state.simulation_finished = False
                st.session_state.pdf_bytes = None
                st.rerun()  # Instantly refreshes UI to gray out input components and lock button
    else:
        left, centre, right = st.columns([3, 4, 2])
        st.button("Simulation Processing in AWS...", disabled=True)

    # Passive Background Polling Engine Execution Block
    if st.session_state.simulation_running and not st.session_state.simulation_finished:
        unique_id = str(uuid.uuid4())
        st.session_state.target_key = (
            "raw/%s/simulation_comparison.csv" % unique_id
        )  # Adjust this path based on your Lambda's output structure
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
                f"⏳ Checking S3 for outputs (Attempt {attempt + 1}/{max_retries})"
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
            st.session_state.pdf_bytes = generate_recommendation_pdf(
                proposed_lat=st.session_state.proposed_lat,
                proposed_lon=st.session_state.proposed_lon,
                selected_line=st.session_state.selected_line,
            )

            st.session_state.kmz_bytes = generate_kmz_bytes(
                proposed_lat=st.session_state.proposed_lat,
                proposed_lon=st.session_state.proposed_lon,
                selected_line=st.session_state.selected_line,
            )
            st.session_state.simulation_running = False
            st.session_state.simulation_finished = True
            st.success("Simulation finished successfully!")
            st.balloons()
            st.rerun()
        else:
            st.error(
                "❌ Simulation timed out or failed to write results back to S3.")
            st.session_state.simulation_running = False
            st.rerun()


if st.session_state.simulation_finished:
    left, centre, right = st.columns([3, 4, 2])
    with centre:

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
            st.stop()

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

        if st.session_state.kmz_bytes:
            st.download_button(
                key="download_kmz_button",
                label="Download Google Earth KMZ",
                data=st.session_state.kmz_bytes,
                file_name="travel_simulation_google_earth.kmz",
                mime="application/vnd.google-earth.kmz",
            )

        if st.button("Reset Dashboard for New Run"):
            st.session_state.simulation_finished = False
            st.session_state.simulation_running = False
            st.session_state.pdf_bytes = None
            st.session_state.kmz_bytes = None
            st.rerun()

    if not comparison_df.empty:
        st.subheader("Simulation Visualisations")

        st.altair_chart(
            create_top_affected_routes_chart(comparison_df),
            use_container_width=True,
        )

        st.altair_chart(
            create_top_time_saving_routes_chart(comparison_df),
            use_container_width=True,
        )

        st.altair_chart(
            create_station_demand_impact_chart(comparison_df),
            use_container_width=True,
        )

    st.subheader("Affected Routes Summary")
    if not comparison_df.empty:
        affected_routes_summary = get_affected_routes(comparison_df)
        st.dataframe(affected_routes_summary)
    else:
        st.warning("No comparison data available to summarize affected routes.")
    st.subheader("Estimated Demand Impact Ranges")
    if not comparison_df.empty:
        demand_impact_ranges = get_demand_impact_ranges(comparison_df)
        st.dataframe(demand_impact_ranges)
    else:
        st.warning(
            "No comparison data available to calculate demand impact ranges.")

    st.subheader("Simulation Impact Map")

    if not comparison_df.empty:
        station_data = get_station_data(BUCKET_NAME)
        if not station_data.empty:
            folium_map = create_folium_map(station_data, comparison_df)
            folium_map = plot_original_station_point(metadata, folium_map)
            
            map_col, legend_col = st.columns([3, 1])

            with map_col:
                st_folium(folium_map, width=700, height=500)

            with legend_col:
                st.markdown(
                    """
                    <div style="
                        background-color:white;
                        padding:15px;
                        border-radius:10px;
                        border:1px solid #ddd;
                    ">
                    <h4>Impact Legend</h4>
                    <h5>Average time saved or lost by passengers passing through each station:</h5>

                    <p>🔵 No Effect</p>
                    <p>🟢 Time Saving</p>
                    <p>🔴 Major Time Save</p>
                    <p>🟠 Time Loss</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
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
    st.metric("Greatest Time Spent Difference (mins)",
              f"{greatest_time_diff:.2f}")
    st.metric("Percentage of Affected Routes", f"{percentage_affected:.2f}%")

st.markdown("---")

st.caption(
    "London Station Simulation (LSS) | "
    "Smarter Stations. Better Connections. Stronger London."
)
