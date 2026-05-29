import folium
import pandas as pd


def plot_simulation_data_points(passenger_info: pd.DataFrame):
    """
    Plots the simulation data points on a map using Folium.

    Parameters:
    - passenger_info: DataFrame containing the simulation results with 'latitude' and 'longitude' columns.

    Returns:
    - A Folium map object with the plotted data points.
    """
    # Create a base map centered around the average location of the data points
    avg_lat = passenger_info["origin_lat"].mean()
    avg_lon = passenger_info["origin_lng"].mean()
    sim_map = folium.Map(location=[avg_lat, avg_lon], zoom_start=12)

    # Add simulation data points to the map
    for _, row in passenger_info.iterrows():
        folium.CircleMarker(
            location=[row["origin_lat"], row["origin_lng"]],
            radius=5,
            color="blue",
            fill=True,
            fill_color="blue",
            fill_opacity=0.6,
            popup=f"Route ID: Time Spent: {row['journey_time_mins']} mins",
        ).add_to(sim_map)

        folium.CircleMarker(
            location=[row["destination_lat"], row["destination_lng"]],
            radius=5,
            color="red",
            fill=True,
            fill_color="red",
            fill_opacity=0.6,
            popup=f"Route ID: Time Spent: {row['journey_time_mins']} mins",
        ).add_to(sim_map)

    return sim_map


if __name__ == "__main__":
    # Load simulation results and station data from CSV files
    passenger_info = pd.read_csv("simulation/passengers.csv").sample(
        100
    )  # Sample 100 passengers for plotting

    # Plot the simulation data points on the map
    sim_map = plot_simulation_data_points(passenger_info)

    # Save the map to an HTML file
    sim_map.save("simulation/simulation_map.html")
