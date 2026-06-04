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
    layout="wide",
)

# Construct logo path relative to this script's location
script_dir = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(script_dir, "lss_logo.png")
st.logo(logo_path, size="large")

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


st.sidebar.image(logo_path, width=500)

st.sidebar.divider()

st.sidebar.markdown("## Controls")

st.sidebar.markdown("### 1. Choose proposed station location")

method_col1, method_col2 = st.sidebar.columns(2)

with method_col1:
    st.sidebar.button(
        "Type lat/lon",
        disabled=INPUT_DISABLED,
        width='stretch',
        on_click=set_input_method,
        args=("Type latitude/longitude",),
    )

with method_col2:
    st.sidebar.button(
        "Click map",
        disabled=INPUT_DISABLED,
        width='stretch',
        on_click=set_input_method,
        args=("Click on map",),
    )

st.markdown('### Borough-based Station Density Map with Train Stations and Lines')
if st.session_state.input_method == "Type latitude/longitude":
    typed_lat = st.sidebar.number_input(
        "Latitude",
        value=51.5072,
        format="%.6f",
        disabled=INPUT_DISABLED,
        key="typed_lat",
    )

    typed_lon = st.sidebar.number_input(
        "Longitude",
        value=-0.1276,
        format="%.6f",
        disabled=INPUT_DISABLED,
        key="typed_lon",
    )

    if st.sidebar.button("Use coordinates", disabled=INPUT_DISABLED):
        st.session_state.proposed_lat = typed_lat
        st.session_state.proposed_lon = typed_lon
        st.session_state.simulation_finished = False
        st.session_state.pdf_bytes = None
        st.session_state.kmz_bytes = None
        st.rerun()

elif st.session_state.input_method == "Click on map":

    st.sidebar.markdown("Select location on map to the right →")


# Main content area - Interactive station selection map
    st.markdown('#### Click to Select Your Proposed Station')

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

with centre:
    map_data = st_folium(
        m,
        height=600,
        width='stretch',
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


st.sidebar.markdown("### 2. Choose proposed train line")

selected_line = st.sidebar.selectbox(
    "Which line would the proposed station be on?",
    TUBE_AND_RAIL_LINES,
    index=TUBE_AND_RAIL_LINES.index(st.session_state.selected_line),
    disabled=INPUT_DISABLED,
    label_visibility="collapsed",
)
# Debug logging removed (Streamlit reruns frequently).

if not INPUT_DISABLED and selected_line != st.session_state.selected_line:
    st.session_state.selected_line = selected_line
    st.session_state.selected_line_id = line_to_id_mapping[selected_line]
    st.session_state.simulation_finished = False
    st.session_state.pdf_bytes = None
    st.session_state.kmz_bytes = None

st.sidebar.markdown("### 3. Confirm and run")

if st.session_state.proposed_lat is None or st.session_state.proposed_lon is None:
    st.sidebar.warning("Choose a location first")
else:
    st.sidebar.info(
        f"📍 {st.session_state.proposed_lat:.4f}, {st.session_state.proposed_lon:.4f}"
    )
    st.sidebar.info(f"🚆 {st.session_state.selected_line}")

    # Render Active or Disabled button based on execution locker
    if not st.session_state.simulation_running:
        if st.sidebar.button("Run simulation", type="primary", width='stretch'):
            st.session_state.simulation_running = True
            st.session_state.simulation_finished = False
            st.session_state.pdf_bytes = None
            st.rerun()  # Instantly refreshes UI to gray out input components and lock button
    else:
        st.sidebar.button("Processing in AWS...",
                          disabled=True, width='stretch')

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
        start_time = time.time()
        status_placeholder = st.empty()

        with st.spinner("Simulation running..."):
            max_retries = 60  # 5 Minutes Max (60 attempts * 5 seconds sleep)
            simulation_success = False

            for attempt in range(max_retries):
                elapsed = int(time.time() - start_time)
                minutes = elapsed // 60
                seconds = elapsed % 60
                status_placeholder.text(
                    f"⏱️ Running for {minutes}m {seconds}s")

                if check_s3_for_completion(BUCKET_NAME, st.session_state.target_key):
                    simulation_success = True
                    break

                time.sleep(5)

        status_placeholder.success(
            f"✓ Simulation complete! Total time: {minutes}m {seconds}s")

        if not simulation_success:
            st.error(
                "❌ Simulation timed out or failed to write results back to S3.")
            st.session_state.simulation_running = False
            st.rerun()
        else:
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


if st.session_state.simulation_finished:
    left, centre, right = st.columns([3, 4, 2])
    with centre:

        st.subheader("Simulation Results")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"**Latitude**  \n{st.session_state.proposed_lat:.10f}")
        with col2:
            st.write(f"**Longitude**  \n{st.session_state.proposed_lon:.10f}")
        with col3:
            st.write(f"**Line**  \n{st.session_state.selected_line}")

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
        comparison_df = get_comparison_csv(
            BUCKET_NAME, st.session_state.target_key)

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
            width='stretch',
        )

        st.altair_chart(
            create_top_time_saving_routes_chart(comparison_df),
            width='stretch',
        )

        st.altair_chart(
            create_station_demand_impact_chart(comparison_df),
            width='stretch',
        )

    st.subheader("Affected Routes Summary")
    if not comparison_df.empty:
        affected_routes_summary = get_affected_routes(comparison_df)
        st.dataframe(affected_routes_summary, width='stretch')
    else:
        st.warning("No comparison data available to summarize affected routes.")
    st.subheader("Estimated Demand Impact Ranges")
    if not comparison_df.empty:
        demand_impact_ranges = get_demand_impact_ranges(comparison_df)
        st.dataframe(demand_impact_ranges, width='stretch')
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
