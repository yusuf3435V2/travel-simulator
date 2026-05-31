"""The main dashboard for the travel simulation app"""

import time
import folium
import streamlit as st
from streamlit_folium import st_folium
from analysis import generate_recommendation_pdf

st.set_page_config(page_title="Travel Simulation Dashboard", layout="wide")

st.title("Travel Simulation Dashboard")
st.write(
    "Choose a proposed station location by typing coordinates or clicking on the map, "
    "then select the train line and run the simulation."
)

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

    if st.button("Confirm and run simulation", disabled=INPUT_DISABLED):
        st.session_state.simulation_running = True
        st.session_state.simulation_finished = False
        st.session_state.pdf_bytes = None

        with st.spinner("Running simulation and generating report..."):
            # This is where the simulation function will go.
            time.sleep(3)

            st.session_state.pdf_bytes = generate_recommendation_pdf(
                proposed_lat=st.session_state.proposed_lat,
                proposed_lon=st.session_state.proposed_lon,
                selected_line=st.session_state.selected_line,
            )

        st.session_state.simulation_running = False
        st.session_state.simulation_finished = True

        st.success("Simulation finished.")


if st.session_state.simulation_finished:
    st.subheader("Simulation Results")

    st.write("Placeholder results will appear here.")

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
