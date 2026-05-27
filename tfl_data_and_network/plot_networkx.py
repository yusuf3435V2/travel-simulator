import os
import logging
import pandas as pd
import networkx as nx
import folium
from api_utils import setup_logger
from create_stations_network import create_station_network, load_station_network, load_station_data


def create_colour_scheme():
    """Create a colour scheme for the different lines."""
    return {
        "bakerloo": "brown",
        "central": "red",
        "circle": "yellow",
        "district": "green",
        "hammersmith-city": "pink",
        "jubilee": "grey",
        "metropolitan": "purple",
        "northern": "black",
        "piccadilly": "darkblue",
        "victoria": "lightblue",
        "waterloo-city": "cyan",
    }


def plot_station_network(network: nx.Graph, station_data: pd.DataFrame) -> folium.Map:
    """Plot the station network using Folium with colored edges."""
    color_scheme = create_colour_scheme()

    # Calculate center of map
    center_lat = station_data['Latitude'].mean()
    center_lon = station_data['Longitude'].mean()

    # Create Folium map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

    # Add stations as markers
    for _, row in station_data.iterrows():
        folium.CircleMarker(
            location=[row['Latitude'], row['Longitude']],
            radius=1,
            popup=row['Name'],
            color='blue',
            fill=True,
            fillColor='blue',
            fillOpacity=0.4
        ).add_to(m)

    # Add edges colored by line
    for source, target, data in network.edges(data=True):
        line_id = data.get('line_id', 'unknown')
        line_color = color_scheme.get(line_id, 'black')

        source_row = station_data[station_data['UniqueId'] == source]
        target_row = station_data[station_data['UniqueId'] == target]

        if not source_row.empty and not target_row.empty:
            coords = [
                [source_row.iloc[0]['Latitude'], source_row.iloc[0]['Longitude']],
                [target_row.iloc[0]['Latitude'], target_row.iloc[0]['Longitude']]
            ]

            folium.PolyLine(coords, color=line_color,
                            weight=2, opacity=0.7).add_to(m)

    logging.info(
        f"Plotted {len(station_data)} stations and {network.number_of_edges()} edges")
    return m


if __name__ == "__main__":
    setup_logger()
    logging.info("Loading station network and data")
    network = load_station_network()
    station_data = load_station_data()

    logging.info("Plotting station network")
    m = plot_station_network(network, station_data)
    m.save("stations/tube_network_map.html")
    logging.info("Map saved to stations/tube_network_map.html")
