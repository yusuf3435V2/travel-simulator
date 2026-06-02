import streamlit as st
import folium
import pandas as pd
from df_analysis import get_color


def plot_original_station_point(metadata, folium_map):
    """Plots the proposed station location and 800m catchment on the map."""

    if "Latitude" not in metadata or "Longitude" not in metadata:
        st.warning(
            "Metadata does not contain Latitude and Longitude for the proposed station."
        )
        return folium_map

    lat = metadata.get("Latitude")
    lon = metadata.get("Longitude")

    proposed_location = [lat, lon]

    folium.Marker(
        location=proposed_location,
        icon=folium.Icon(color="purple"),
        popup="Proposed Station",
    ).add_to(folium_map)

    folium.Circle(
        location=proposed_location,
        radius=800,
        popup="800m walking catchment",
        color="purple",
        fill=True,
        fill_color="purple",
        fill_opacity=0.15,
        weight=2,
    ).add_to(folium_map)

    return folium_map


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
