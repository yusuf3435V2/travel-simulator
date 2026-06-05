"""Previous simulations viewer page for the travel simulation dashboard."""

# Standard library imports
from Run_Simulations import (
    render_visualization_charts,
    render_affected_routes_summary,
    render_demand_impact_ranges,
)
import json
import os
from typing import Dict, Any

# Third-party imports
import dotenv
import streamlit as st
from streamlit_folium import st_folium

# Local imports
from df_analysis import (
    get_total_time_spent_diff,
    get_greatest_time_spent_diff,
    get_percentage_of_affected_routes,
    create_top_affected_routes_chart,
    create_station_demand_impact_chart,
    create_top_time_saving_routes_chart,
)
from folium_functions import plot_original_station_point, create_folium_map
from s3_utils import (
    get_station_data,
    get_folder_metadata,
    get_comparison_csv,
    get_simulation_folders,
)

# Import reusable render functions from main dashboard
import sys
from pathlib import Path

parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))


# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

dotenv.load_dotenv()

BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
BASE_PREFIX = "raw/"

# ============================================================================
# FOLDER SELECTION FUNCTIONS
# ============================================================================


def fetch_simulation_folders() -> list:
    """Fetch available simulation folders from S3."""
    with st.spinner("Fetching available simulations from S3..."):
        return get_simulation_folders(BUCKET_NAME, BASE_PREFIX)


def render_folder_selector(available_folders: list) -> str:
    """Render folder selection dropdown and return selected folder name."""
    selected_folder = st.selectbox(
        "Select a Simulation Run:",
        options=available_folders,
        index=0,
        format_func=lambda x: x["Folder"],
    )["Folder"]

    st.write(f"Selected Folder: `{selected_folder}`")
    return selected_folder


# ============================================================================
# METADATA FUNCTIONS
# ============================================================================


def load_simulation_metadata(metadata_key: str) -> Dict[str, Any]:
    """Load and parse simulation metadata from S3."""
    with st.spinner("Loading metadata..."):
        metadata = get_folder_metadata(BUCKET_NAME, metadata_key)
        return json.loads(metadata) if isinstance(metadata, str) else metadata


def render_metadata_display(metadata: Dict[str, Any]) -> None:
    """Render metadata summary with latitude, longitude, and line info."""
    col1, col2, col3 = st.columns(3)

    with col1:
        lat_val = metadata.get("Latitude", "N/A")
        if isinstance(lat_val, (int, float)):
            st.write(f"**Latitude**  \n{lat_val:.10f}")
        else:
            st.write(f"**Latitude**  \n{lat_val}")

    with col2:
        lon_val = metadata.get("Longitude", "N/A")
        if isinstance(lon_val, (int, float)):
            st.write(f"**Longitude**  \n{lon_val:.10f}")
        else:
            st.write(f"**Longitude**  \n{lon_val}")

    with col3:
        st.write(f"**Line**  \n{metadata.get('Line_id', 'N/A')}")


# ============================================================================
# COMPARISON DATA FUNCTIONS
# ============================================================================


def load_comparison_data(comparison_csv_key: str):
    """Load comparison CSV data from S3."""
    with st.spinner("Loading comparison data..."):
        return get_comparison_csv(BUCKET_NAME, comparison_csv_key)


# ============================================================================
# RESULTS DISPLAY FUNCTIONS
# ============================================================================


def render_impact_map(comparison_df, metadata: Dict[str, Any]) -> None:
    """Render the simulation impact map with station data."""
    st.subheader("Simulation Impact Map")

    if comparison_df.empty:
        st.warning("Cannot create map without comparison data.")
        return

    station_data = get_station_data(BUCKET_NAME)
    if station_data.empty:
        st.warning("Cannot create map without station data.")
        return

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


def render_impact_metrics(comparison_df, metadata: Dict[str, Any]) -> None:
    """Render overall impact metrics."""
    st.subheader("Overall Impact Metrics")

    if comparison_df.empty:
        st.warning("No data available for metrics calculation.")
        return

    total_time_diff = get_total_time_spent_diff(comparison_df)
    greatest_time_diff = get_greatest_time_spent_diff(comparison_df)
    percentage_affected = get_percentage_of_affected_routes(
        comparison_df, metadata.get("number_of_passengers", 0)
    )

    st.metric("Total Time Spent Difference (mins)", f"{total_time_diff:.2f}")
    st.metric("Greatest Time Spent Difference (mins)",
              f"{greatest_time_diff:.2f}")
    st.metric("Percentage of Affected Routes", f"{percentage_affected:.2f}%")


def render_simulation_results(selected_folder: str, metadata: Dict[str, Any]) -> None:
    """Render complete simulation results and analysis."""
    comparison_csv_key = f"{BASE_PREFIX}{selected_folder}/simulation_comparison.csv"
    comparison_df = load_comparison_data(comparison_csv_key)

    render_visualization_charts(comparison_df)
    render_affected_routes_summary(comparison_df)
    render_demand_impact_ranges(comparison_df)
    render_impact_map(comparison_df, metadata)
    render_impact_metrics(comparison_df, metadata)


# ============================================================================
# MAIN PAGE FUNCTION
# ============================================================================


def previous_simulations_page() -> None:
    """Main page function orchestrating the previous simulations viewer."""
    st.title("Previous Simulations Dashboard")

    available_folders = fetch_simulation_folders()

    if not available_folders:
        st.warning("No simulation folders found.")
        return

    selected_folder = render_folder_selector(available_folders)

    st.subheader("Simulation Metadata")
    metadata_key = f"{BASE_PREFIX}{selected_folder}/user_station.json"
    metadata = load_simulation_metadata(metadata_key)
    render_metadata_display(metadata)

    render_simulation_results(selected_folder, metadata)


# ============================================================================
# PAGE ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    previous_simulations_page()
