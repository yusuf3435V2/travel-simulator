"""Tests for collecting passengers at stations."""

from collect_passengers import (
    shortest_path_between_stations,
    shortest_path_length_between_stations,
    get_line_switches,
    total_switch_time,
    get_station_latlong,
    get_nearest_station,
    assign_unique_id_to_routes,
    extract_agent_data,
    create_agents_from_passenger_data,
    TravelModel,
    PassengerAgent,
    load_graphml,
    get_station_name_from_id,
    get_station_distance,
    add_station_to_network,
    add_station_to_stations_data,
    choose_transport_speed,
    determine_travel_time,
    BUS_SPEED,
    BIKE_SPEED,
    WALK_SPEED,
)
from distance_maths import haversine_distance
import pytest
import pandas as pd
import networkx as nx


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Fixture for sample passenger data."""
    return pd.read_csv("simulation/sample_passengers.csv")


@pytest.fixture
def sample_stations() -> nx.Graph:
    """Fixture for sample station graph (5 stations). With duration weight on each edge."""
    G = nx.Graph()
    G.add_edge("StationA", "StationB", duration=5, line="piccadilly")
    G.add_edge("StationB", "StationC", duration=10, line="piccadilly")
    G.add_edge("StationC", "StationD", duration=15, line="piccadilly")
    G.add_edge("StationD", "StationE", duration=20, line="piccadilly")
    G.add_edge("StationA", "StationC", duration=12, line="district")
    return G


@pytest.fixture
def sample_graph_for_tube() -> nx.Graph:
    """Fixture for loading the actual tube network graph."""
    return load_graphml("stations/tube_network.graphml")


@pytest.fixture
def sample_station_data() -> pd.DataFrame:
    """Fixture for sample station data."""
    data = pd.read_csv("stations/Stations.csv")
    return data


def test_get_station_latlong(sample_station_data):
    """Test that the latitude and longitude of a station are retrieved correctly."""
    latlong = get_station_latlong("940GZZLUBNK", sample_station_data)
    assert latlong == (51.513356, -0.088899), (
        f"Expected (51.513356, -0.088899), got {latlong}"
    )


def test_get_station_latlong_invalid_id(sample_station_data):
    """Test that None is returned when an invalid station ID is provided."""
    latlong = get_station_latlong("INVALID_ID", sample_station_data)
    assert latlong is None, f"Expected None, got {latlong}"


def test_shortest_path(sample_stations):
    """Test that the shortest path between two stations is calculated correctly."""
    path = shortest_path_between_stations(sample_stations, "StationA", "StationD")
    assert path == ["StationA", "StationB", "StationC", "StationD"], (
        f"Expected ['StationA', 'StationB', 'StationC', 'StationD'], got {path}"
    )


def test_get_nearest_station(sample_station_data):
    """Test that the nearest station to a given latitude and longitude is retrieved correctly."""
    nearest_station = get_nearest_station(51.513356, -0.088899, sample_station_data)
    assert nearest_station == "940GZZLUBNK", (
        f"Expected '940GZZLUBNK', got {nearest_station}"
    )


def test_choose_transport_speed_walk():
    """Test that walking speed is returned for short distances."""
    distance = 1.0  # 1 km
    speed = choose_transport_speed(distance)
    assert speed == WALK_SPEED, f"Expected {WALK_SPEED}, got {speed}"


def test_choose_transport_speed_bike():
    """Test that bike speed is returned for medium distances."""
    distance = 3.0  # 3 km, between 1.6 and 5
    speed = choose_transport_speed(distance)
    assert speed == BIKE_SPEED, f"Expected {BIKE_SPEED}, got {speed}"


def test_choose_transport_speed_bus():
    """Test that bus speed is returned for long distances."""
    distance = 6.0  # 6 km, > 5
    speed = choose_transport_speed(distance)
    assert speed == BUS_SPEED, f"Expected {BUS_SPEED}, got {speed}"


def test_choose_transport_speed_boundary_walk_to_bike():
    """Test boundary case between walk and bike speed (1.6 km)."""
    distance = 1.6
    speed = choose_transport_speed(distance)
    assert speed == BIKE_SPEED, f"Expected {BIKE_SPEED} at boundary, got {speed}"


def test_choose_transport_speed_boundary_bike_to_bus():
    """Test boundary case between bike and bus speed (5 km)."""
    distance = 5.0
    speed = choose_transport_speed(distance)
    assert speed == BUS_SPEED, f"Expected {BUS_SPEED} at boundary, got {speed}"


def test_determine_travel_time_walk():
    """Test travel time calculation for walking."""
    distance = 1.0  # 1 km
    time = determine_travel_time(distance)
    expected_time = distance / WALK_SPEED
    assert abs(time - expected_time) < 0.01, f"Expected {expected_time}, got {time}"


def test_determine_travel_time_bike():
    """Test travel time calculation for biking."""
    distance = 3.0  # 3 km
    time = determine_travel_time(distance)
    expected_time = distance / BIKE_SPEED
    assert abs(time - expected_time) < 0.01, f"Expected {expected_time}, got {time}"


def test_determine_travel_time_bus():
    """Test travel time calculation for bus."""
    distance = 6.0  # 6 km
    time = determine_travel_time(distance)
    expected_time = distance / BUS_SPEED
    assert abs(time - expected_time) < 0.01, f"Expected {expected_time}, got {time}"


def test_determine_travel_time_zero_distance():
    """Test travel time for zero distance."""
    distance = 0.0
    time = determine_travel_time(distance)
    assert time == 0.0, f"Expected 0.0 minutes for zero distance, got {time}"


def test_determine_travel_time_small_distance():
    """Test travel time for very small distance."""
    distance = 0.1  # 100 meters
    time = determine_travel_time(distance)
    expected_time = distance / WALK_SPEED
    assert abs(time - expected_time) < 0.01, f"Expected {expected_time}, got {time}"
    assert time > 0, "Travel time should be positive for non-zero distance"


def test_shortest_path_no_path(sample_stations):
    """Test that the shortest path function returns an empty list when no path exists."""
    sample_stations.remove_edge("StationC", "StationD")  # Remove edge to create no path
    path = shortest_path_between_stations(sample_stations, "StationA", "StationD")
    assert path == [], f"Expected [], got {path}"


def test_shortest_path_length(sample_stations):
    """Test that the shortest path length between two stations is calculated correctly."""
    length = shortest_path_length_between_stations(
        sample_stations, "StationA", "StationD"
    )
    assert length == 27, f"Expected 27, got {length}"


def test_check_line_switches(sample_stations):
    """Test that line switches are correctly identified in a path."""
    path = ["StationA", "StationC", "StationD"]
    line_switches = get_line_switches(path, sample_stations)
    assert line_switches == [("StationC", "district", "piccadilly")], (
        f"Expected [('StationC', 'district', 'piccadilly')], got {line_switches}"
    )


def test_total_switch_time():
    """Test that total switch time is calculated correctly."""
    line_switches = [
        ("StationC", "district", "piccadilly"),
        ("StationD", "piccadilly", "district"),
    ]
    switch_time = 5
    total_time = total_switch_time(line_switches, switch_time)
    assert total_time == 10, f"Expected 10, got {total_time}"


def test_sample_data_valid_columns(sample_data):
    """Test that sample data contains the expected columns."""
    expected_columns = {
        "passenger_id",
        "origin_lat",
        "origin_lng",
        "destination_lat",
        "destination_lng",
        "day_type",
    }
    for column in expected_columns:
        assert column in sample_data.columns, f"Missing expected column: {column}"


def test_haversine_distance_same():
    """Test that the Haversine distance is calculated correctly."""
    lat1, lon1 = 51.513356, -0.088899  # Bank station
    lat2, lon2 = lat1, lon1  # Same location
    distance = haversine_distance(lat1, lon1, lat2, lon2)
    expected_distance = 0.0  # Distance should be zero for the same location
    assert abs(distance - expected_distance) == 0


def test_haversine_distance_different():
    """Test that the Haversine distance is calculated correctly between London and Paris."""
    lat1, lon1 = 51.5074, -0.1278  # London
    lat2, lon2 = 48.8566, 2.3522  # Paris
    distance = haversine_distance(lat1, lon1, lat2, lon2)
    expected_distance = 343.5  # Approximate distance in kilometers
    assert abs(distance - expected_distance) < 1.0, (
        f"Expected approximately {expected_distance} km, got {distance} km"
    )


def test_assign_unique_id_to_routes(sample_data):
    """Test that unique IDs are assigned to each route."""
    df_with_ids = assign_unique_id_to_routes(sample_data)
    assert "route_id" in df_with_ids.columns, "Expected 'route_id' column in DataFrame"
    assert df_with_ids["route_id"].is_unique, "Expected unique route IDs"


def test_get_station_name_from_id(sample_station_data):
    """Test that the station name is retrieved correctly from its ID."""
    station_name = get_station_name_from_id("940GZZLUBNK", sample_station_data)
    assert station_name is not None, "Expected a station name, got None"
    assert isinstance(station_name, str), "Expected station name to be a string"


def test_get_station_name_from_id_invalid(sample_station_data):
    """Test that None is returned for an invalid station ID."""
    station_name = get_station_name_from_id("INVALID_ID", sample_station_data)
    assert station_name is None, f"Expected None for invalid ID, got {station_name}"


def test_get_station_distance(sample_station_data):
    """Test that the distance between a station and a point is calculated correctly."""
    station_id = "940GZZLUBNK"
    lat, lng = 51.513356, -0.088899  # Bank station coordinates
    distance = get_station_distance(station_id, lat, lng, sample_station_data)
    assert distance is not None, "Expected a distance value"
    assert distance >= 0, "Distance should be non-negative"
    assert distance < 0.1, "Distance should be close to zero for the same location"


def test_get_station_distance_invalid_station(sample_station_data):
    """Test that None is returned when an invalid station ID is provided."""
    distance = get_station_distance(
        "INVALID_ID", 51.513356, -0.088899, sample_station_data
    )
    assert distance is None, f"Expected None for invalid station, got {distance}"


def test_load_graphml():
    """Test that the GraphML file is loaded correctly."""
    graph = load_graphml("stations/tube_network.graphml")
    assert isinstance(graph, nx.Graph), "Expected NetworkX Graph object"
    assert len(graph.nodes()) > 0, "Expected graph to contain nodes"
    assert len(graph.edges()) > 0, "Expected graph to contain edges"


@pytest.fixture
def sample_passenger_data_with_ids(sample_data) -> pd.DataFrame:
    """Fixture for sample passenger data with route IDs."""
    return assign_unique_id_to_routes(sample_data)


@pytest.fixture
def model_with_sample_graph(sample_stations, sample_station_data) -> TravelModel:
    """Fixture for creating a TravelModel with sample graph."""
    model = TravelModel(sample_stations, sample_station_data)

    return model


def test_create_agents_from_passenger_data(
    sample_passenger_data_with_ids, model_with_sample_graph
):
    """Test that agents are correctly created from passenger data."""
    # Select a subset of data for testing
    test_data = sample_passenger_data_with_ids.head(2)

    initial_agent_count = len(model_with_sample_graph.agents)
    create_agents_from_passenger_data(test_data, model_with_sample_graph)
    final_agent_count = len(model_with_sample_graph.agents)

    assert final_agent_count == initial_agent_count + 2, (
        f"Expected 2 agents to be added, but got {final_agent_count - initial_agent_count}"
    )


def test_create_agents_from_passenger_data_agent_attributes(
    sample_passenger_data_with_ids, model_with_sample_graph
):
    """Test that agents created have correct attributes."""
    test_data = sample_passenger_data_with_ids.head(1)
    create_agents_from_passenger_data(test_data, model_with_sample_graph)

    agent = list(model_with_sample_graph.agents)[-1]
    assert isinstance(agent, PassengerAgent), "Expected PassengerAgent instance"
    assert agent.passenger_id == test_data.iloc[0]["passenger_id"]
    assert agent.origin_lat == test_data.iloc[0]["origin_lat"]
    assert agent.destination_lng == test_data.iloc[0]["destination_lng"]


def test_extract_agent_data_empty_model(model_with_sample_graph):
    """Test that extract_agent_data returns an empty DataFrame for a model with no agents."""
    result_df = extract_agent_data(model_with_sample_graph)
    assert isinstance(result_df, pd.DataFrame), "Expected DataFrame object"
    assert len(result_df) == 0, "Expected empty DataFrame for model with no agents"


def test_extract_agent_data_with_agents(
    sample_passenger_data_with_ids, model_with_sample_graph
):
    """Test that extract_agent_data correctly extracts all agent data."""
    test_data = sample_passenger_data_with_ids.head(2)
    create_agents_from_passenger_data(test_data, model_with_sample_graph)

    result_df = extract_agent_data(model_with_sample_graph)
    assert isinstance(result_df, pd.DataFrame), "Expected DataFrame object"
    assert len(result_df) == 2, f"Expected 2 rows, got {len(result_df)}"


def test_extract_agent_data_columns(
    sample_passenger_data_with_ids, model_with_sample_graph
):
    """Test that extract_agent_data includes all required columns."""
    test_data = sample_passenger_data_with_ids.head(1)
    create_agents_from_passenger_data(test_data, model_with_sample_graph)

    result_df = extract_agent_data(model_with_sample_graph)
    expected_columns = {
        "route_id",
        "passenger_id",
        "origin_lat",
        "origin_lng",
        "destination_lat",
        "destination_lng",
        "day_type",
        "nearest_station",
        "alighting_station",
        "time_spent",
        "walk_time",
    }
    for col in expected_columns:
        assert col in result_df.columns, f"Missing expected column: {col}"


def test_add_station_to_station_data(sample_station_data):
    """Test that a new station is added to the station data correctly."""
    new_station = {
        "UniqueId": "user_station_1",
        "Name": "User Station",
        "Latitude": 51.4883367,
        "Longitude": -0.3426345,
        "Line_id": "piccadilly",
    }
    stations = add_station_to_stations_data(
        sample_station_data,
        new_station["UniqueId"],
        new_station["Latitude"],
        new_station["Longitude"],
        new_station["Line_id"],
        new_station["Name"],
    )
    print(stations.tail())
    print(sample_station_data.tail())
    assert len(stations) == len(sample_station_data) + 1, (
        f"Expected {len(sample_station_data) + 1} stations, got {len(stations)}"
    )
    assert stations.iloc[-1]["UniqueId"] == new_station["UniqueId"], (
        f"Expected last station ID to be {new_station['UniqueId']}, got {stations.iloc[-1]['UniqueId']}"
    )
    assert sample_station_data.iloc[:-1].equals(stations.iloc[:-2]), (
        "Existing station data should remain unchanged"
    )


def test_add_station_to_network(sample_graph_for_tube, sample_station_data):
    """Test that a new station is added to the network graph correctly."""
    graph = sample_graph_for_tube.copy()
    original_number_of_nodes = graph.number_of_nodes()
    station_id = "user_station_1"
    lat, lng = 51.4883367, -0.3426345
    line = "piccadilly"
    add_station_to_network(graph, station_id, lat, lng, line, sample_station_data)
    assert station_id in graph.nodes, "New station should be added to the graph"
    assert graph.number_of_nodes() == original_number_of_nodes + 1, (
        f"Expected {original_number_of_nodes + 1} nodes, got {graph.number_of_nodes()}"
    )

    # Assert the new station has 2 connections
    num_connections = graph.degree(station_id)
    assert num_connections == 2, (
        f"Expected 2 connections for {station_id}, got {num_connections}"
    )
