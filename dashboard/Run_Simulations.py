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


# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

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

LINE_TO_ID_MAPPING = {
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

# ============================================================================
# AWS SETUP
# ============================================================================

dotenv.load_dotenv()

lambda_client = boto3.client("lambda")
s3_client = boto3.client("s3")
BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "your-simulation-bucket-name")

script_dir = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(script_dir, "lss_logo.png")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def check_s3_for_completion(bucket: str, key: str) -> bool:
    """Check if simulation output exists in S3 without downloading full payload."""
    try:
        print("Checking S3 for key: %s" % key)
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError:
        return False


# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================


def initialize_session_state() -> None:
    """Initialize all session state variables for the dashboard."""
    if "proposed_lat" not in st.session_state:
        st.session_state.proposed_lat = None

    if "proposed_lon" not in st.session_state:
        st.session_state.proposed_lon = None

    if "selected_line" not in st.session_state:
        st.session_state.selected_line = TUBE_AND_RAIL_LINES[0]
        st.session_state.selected_line_id = LINE_TO_ID_MAPPING[TUBE_AND_RAIL_LINES[0]]

    if "simulation_running" not in st.session_state:
        st.session_state.simulation_running = False

    if "simulation_finished" not in st.session_state:
        st.session_state.simulation_finished = False

    if "pdf_bytes" not in st.session_state:
        st.session_state.pdf_bytes = None

    if "kmz_bytes" not in st.session_state:
        st.session_state.kmz_bytes = None

    if "input_method" not in st.session_state:
        st.session_state.input_method = "Type latitude/longitude"


def set_input_method(method: str) -> None:
    """Update input method and reset simulation state."""
    st.session_state.input_method = method
    st.session_state.simulation_finished = False
    st.session_state.pdf_bytes = None
    st.session_state.kmz_bytes = None


# ============================================================================
# SIDEBAR FUNCTIONS
# ============================================================================


def render_sidebar_header() -> None:
    """Render the sidebar header with logo and divider."""
    st.sidebar.image(logo_path, width=500)
    st.sidebar.divider()


def render_location_input_section(input_disabled: bool) -> None:
    """Render the location input method selection section."""
    st.sidebar.markdown("## Controls")
    st.sidebar.markdown("### 1. Choose proposed station location")

    method_col1, method_col2 = st.sidebar.columns(2)

    with method_col1:
        st.sidebar.button(
            "Type lat/lon",
            disabled=input_disabled,
            width='stretch',
            on_click=set_input_method,
            args=("Type latitude/longitude",),
        )

    with method_col2:
        st.sidebar.button(
            "Click map",
            disabled=input_disabled,
            width='stretch',
            on_click=set_input_method,
            args=("Click on map",),
        )


def render_typed_coordinates_input(input_disabled: bool) -> None:
    """Render manual coordinate input fields."""
    typed_lat = st.sidebar.number_input(
        "Latitude",
        value=51.5072,
        format="%.6f",
        disabled=input_disabled,
        key="typed_lat",
    )

    typed_lon = st.sidebar.number_input(
        "Longitude",
        value=-0.1276,
        format="%.6f",
        disabled=input_disabled,
        key="typed_lon",
    )

    if st.sidebar.button("Use coordinates", disabled=input_disabled):
        st.session_state.proposed_lat = typed_lat
        st.session_state.proposed_lon = typed_lon
        st.session_state.simulation_finished = False
        st.session_state.pdf_bytes = None
        st.session_state.kmz_bytes = None
        st.rerun()


def render_line_selection(input_disabled: bool) -> None:
    """Render train line selection dropdown."""
    st.sidebar.markdown("### 2. Choose proposed train line")

    selected_line = st.sidebar.selectbox(
        "Which line would the proposed station be on?",
        TUBE_AND_RAIL_LINES,
        index=TUBE_AND_RAIL_LINES.index(st.session_state.selected_line),
        disabled=input_disabled,
        label_visibility="collapsed",
    )

    if not input_disabled and selected_line != st.session_state.selected_line:
        st.session_state.selected_line = selected_line
        st.session_state.selected_line_id = LINE_TO_ID_MAPPING[selected_line]
        st.session_state.simulation_finished = False
        st.session_state.pdf_bytes = None
        st.session_state.kmz_bytes = None


def render_simulation_controls(input_disabled: bool) -> None:
    """Render simulation confirmation and execution controls."""
    st.sidebar.markdown("### 3. Confirm and run")

    if st.session_state.proposed_lat is None or st.session_state.proposed_lon is None:
        st.sidebar.warning("Choose a location first")
    else:
        st.sidebar.info(
            f"📍 {st.session_state.proposed_lat:.4f}, {st.session_state.proposed_lon:.4f}"
        )
        st.sidebar.info(f"🚆 {st.session_state.selected_line}")

        if not st.session_state.simulation_running:
            if st.sidebar.button("Run simulation", type="primary", width='stretch'):
                st.session_state.simulation_running = True
                st.session_state.simulation_finished = False
                st.session_state.pdf_bytes = None
                st.rerun()
        else:
            st.sidebar.button("Processing in AWS...",
                              disabled=True, width='stretch')


def render_sidebar(input_disabled: bool) -> None:
    """Render the complete sidebar with all controls."""
    render_sidebar_header()
    render_location_input_section(input_disabled)

    if st.session_state.input_method == "Type latitude/longitude":
        render_typed_coordinates_input(input_disabled)

    st.markdown(
        '### Borough-based Station Density Map with Train Stations and Lines')
    if st.session_state.input_method == "Click on map":
        st.sidebar.markdown("Select location on map to the right →")

    render_line_selection(input_disabled)
    render_simulation_controls(input_disabled)


# ============================================================================
# LOCATION SELECTOR FUNCTIONS
# ============================================================================


def render_location_selector_map(input_disabled: bool) -> None:
    """Render the interactive map for selecting proposed station location."""
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

    if not input_disabled and map_data and map_data.get("last_clicked"):
        st.session_state.proposed_lat = map_data["last_clicked"]["lat"]
        st.session_state.proposed_lon = map_data["last_clicked"]["lng"]
        st.session_state.simulation_finished = False
        st.session_state.pdf_bytes = None
        st.session_state.kmz_bytes = None
        st.rerun()


# ============================================================================
# SIMULATION EXECUTION FUNCTIONS
# ============================================================================


def trigger_lambda_simulation() -> str:
    """Trigger AWS Lambda simulation with current proposed station parameters."""
    unique_id = str(uuid.uuid4())
    target_key = f"raw/{unique_id}/simulation_comparison.csv"

    print("Running following station")
    print({
        "UniqueId": unique_id,
        "Latitude": st.session_state.proposed_lat,
        "Longitude": st.session_state.proposed_lon,
        "Line_id": st.session_state.selected_line_id,
        "Name": "User Proposed Station",
    })

    with st.spinner("Invoking remote AWS Lambda engine..."):
        lambda_client.invoke(
            FunctionName=os.environ.get("SIMULATION_LAMBDA_ARN"),
            InvocationType="Event",
            Payload=json.dumps({
                "UniqueId": unique_id,
                "Latitude": st.session_state.proposed_lat,
                "Longitude": st.session_state.proposed_lon,
                "Line_id": st.session_state.selected_line_id,
                "Name": "User Proposed Station",
            }),
        )
        st.toast("Lambda successfully triggered!")

    return target_key


def poll_simulation_completion(target_key: str, max_retries: int = 60) -> bool:
    """Poll S3 for simulation completion with progress updates."""
    start_time = time.time()
    status_placeholder = st.empty()

    with st.spinner("Simulation running..."):
        for _ in range(max_retries):
            elapsed = int(time.time() - start_time)
            minutes = elapsed // 60
            seconds = elapsed % 60
            status_placeholder.text(f"⏱️ Running for {minutes}m {seconds}s")

            if check_s3_for_completion(BUCKET_NAME, target_key):
                status_placeholder.success(
                    f"✓ Simulation complete! Total time: {minutes}m {seconds}s"
                )
                return True

            time.sleep(5)

    return False


def execute_simulation() -> bool:
    """Execute the complete simulation workflow."""
    st.session_state.target_key = trigger_lambda_simulation()

    simulation_success = poll_simulation_completion(st.session_state.target_key)

    if not simulation_success:
        st.error("❌ Simulation timed out or failed to write results back to S3.")
        st.session_state.simulation_running = False
        st.rerun()
        return False

    # Generate PDF and KMZ reports
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
    return True


# ============================================================================
# RESULTS DISPLAY FUNCTIONS
# ============================================================================


def render_results_header() -> None:
    """Render the results header with proposed station details."""
    left, centre, right = st.columns([3, 4, 2])
    with centre:
        st.subheader("Simulation Results")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.write(f"**Latitude**  \n{st.session_state.proposed_lat:.10f}")
        with col2:
            st.write(f"**Longitude**  \n{st.session_state.proposed_lon:.10f}")
        with col3:
            st.write(f"**Line**  \n{st.session_state.selected_line.title()}")


def render_download_buttons() -> None:
    """Render PDF and KMZ download buttons."""
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


def render_reset_button() -> None:
    """Render button to reset dashboard for new simulation."""
    if st.button("Reset Dashboard for New Run"):
        st.session_state.simulation_finished = False
        st.session_state.simulation_running = False
        st.session_state.pdf_bytes = None
        st.session_state.kmz_bytes = None
        st.rerun()


def render_visualization_charts(comparison_df) -> None:
    """Render simulation visualization charts."""
    if comparison_df.empty:
        st.warning("No visualization data available.")
        return

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


def render_affected_routes_summary(comparison_df) -> None:
    """Render summary of affected routes."""
    st.subheader("Affected Routes Summary")
    if not comparison_df.empty:
        affected_routes_summary = get_affected_routes(comparison_df)
        st.dataframe(affected_routes_summary, width='stretch')
    else:
        st.warning("No comparison data available to summarize affected routes.")


def render_demand_impact_ranges(comparison_df) -> None:
    """Render estimated demand impact ranges."""
    st.subheader("Estimated Demand Impact Ranges")
    if not comparison_df.empty:
        demand_impact_ranges = get_demand_impact_ranges(comparison_df)
        st.dataframe(demand_impact_ranges, width='stretch')
    else:
        st.warning(
            "No comparison data available to calculate demand impact ranges.")


def render_impact_map(comparison_df) -> None:
    """Render the simulation impact map with station data."""
    st.subheader("Simulation Impact Map")

    if comparison_df.empty:
        st.warning("Cannot create map without comparison data.")
        return

    station_data = get_station_data(BUCKET_NAME)
    if station_data.empty:
        st.warning("Cannot create map without station data.")
        return

    metadata = {
        "Latitude": st.session_state.proposed_lat,
        "Longitude": st.session_state.proposed_lon,
        "Line_id": st.session_state.selected_line_id,
        "Name": "User Proposed Station",
        "number_of_passengers": 32000,
    }

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


def render_impact_metrics(comparison_df) -> None:
    """Render overall impact metrics."""
    st.subheader("Overall Impact Metrics")

    if comparison_df.empty:
        st.warning("No data available for metrics calculation.")
        return

    total_time_diff = get_total_time_spent_diff(comparison_df)
    greatest_time_diff = get_greatest_time_spent_diff(comparison_df)
    percentage_affected = get_percentage_of_affected_routes(
        comparison_df, 32000  # Placeholder passenger count
    )

    st.metric("Total Time Spent Difference (mins)", f"{total_time_diff:.2f}")
    st.metric("Greatest Time Spent Difference (mins)",
              f"{greatest_time_diff:.2f}")
    st.metric("Percentage of Affected Routes", f"{percentage_affected:.2f}%")


def render_results() -> None:
    """Render complete simulation results display."""
    render_results_header()

    if st.session_state.target_key is None:
        st.error("Target key not found. Please run the simulation again.")
        st.stop()

    render_download_buttons()
    render_reset_button()

    comparison_df = get_comparison_csv(
        BUCKET_NAME, st.session_state.target_key)

    render_visualization_charts(comparison_df)
    render_affected_routes_summary(comparison_df)
    render_demand_impact_ranges(comparison_df)
    render_impact_map(comparison_df)
    render_impact_metrics(comparison_df)


# ============================================================================
# FOOTER FUNCTIONS
# ============================================================================


def render_footer() -> None:
    """Render the dashboard footer."""
    st.markdown("---")
    st.caption(
        "London Station Simulation (LSS) | "
        "Smarter Stations. Better Connections. Stronger London."
    )


# ============================================================================
# MAIN DASHBOARD FUNCTION
# ============================================================================


def dashboard() -> None:
    """Main dashboard function orchestrating all application components."""
    # Configure Streamlit page settings
    st.set_page_config(
        page_title="London Station Simulation",
        page_icon="🚆",
        layout="wide",
    )
    st.logo(logo_path, size="large")

    # Initialize session state
    initialize_session_state()

    # Determine if input should be disabled
    input_disabled = st.session_state.simulation_running

    # Render sidebar
    render_sidebar(input_disabled)

    # Render location selector map if in click mode
    render_location_selector_map(input_disabled)

    # Handle simulation execution
    if st.session_state.simulation_running and not st.session_state.simulation_finished:
        execute_simulation()

    # Render results if simulation is finished
    if st.session_state.simulation_finished:
        render_results()

    # Render footer
    render_footer()


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    dashboard()
