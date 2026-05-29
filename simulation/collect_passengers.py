"""Collect passengers and their journeys from the TFL API load them as agents in the simulation."""

import networkx as nx
import mesa
import pandas as pd
from distance_maths import haversine_distance

# Here are some speeds of different methods of getting to the station.
WALK_SPEED = 5 / 60
BIKE_SPEED = 20 / 60
BUS_SPEED = 30 / 60


def load_user_information(file_path: str) -> pd.DataFrame:
    """Load user information from a CSV file."""
    return pd.read_csv(file_path)


def load_graphml(file_path: str) -> nx.Graph:
    """Load a graph from a GraphML file."""
    return nx.read_graphml(file_path)


def add_station_to_stations_data(
    station_data: pd.DataFrame,
    station_id: str,
    lat: float,
    lng: float,
    line: str,
    station_name: str = "User Station",
) -> pd.DataFrame:
    """Add a station to the stations data DataFrame."""
    new_station = {
        "UniqueId": station_id,
        "Name": station_name,
        "Latitude": lat,
        "Longitude": lng,
        "Line_id": line,
    }
    station_data = pd.concat(
        [station_data, pd.DataFrame([new_station])], ignore_index=True
    )
    return station_data


def add_station_to_network(
    graph: nx.Graph,
    station_id: str,
    lat: float,
    lng: float,
    line: str,
    station_data: pd.DataFrame,
    station_name: str = "User Station",
) -> None:
    """Add a station to the network graph."""
    graph.add_node(station_id, name=station_name)
    closest_stations = find_closest_consecutive_stations(graph, lat, lng, station_data)
    print(f"found closest stations: {closest_stations} for new station {station_id}")
    if closest_stations is not None:
        closest_station, neighbor_station = closest_stations

        time_between_stations = graph.get_edge_data(
            closest_station, neighbor_station
        ).get("duration", 0)
        graph.add_edge(
            station_id,
            closest_station,
            line_id=line,
            duration=time_between_stations / 2,
        )
        graph.add_edge(
            station_id,
            neighbor_station,
            line_id=line,
            duration=time_between_stations / 2,
        )
        graph.remove_edge(closest_station, neighbor_station)  # Remove the original edge


def find_closest_consecutive_stations(
    graph: nx.Graph, lat: float, lng: float, station_data: pd.DataFrame
) -> tuple[str, str] | None:
    """Find the closest consecutive stations in the graph to a given latitude and longitude."""
    closest_station = None
    closest_distance = float("inf")

    for node in graph.nodes(data=True):
        if node[0].startswith("user_station"):
            continue  # Skip user-added stations to avoid connecting to them
        station_id = node[0]
        print(f"checking station {station_id} for closest station")
        station_latlong = get_station_latlong(station_id, station_data)
        if station_latlong is not None:
            station_lat, station_lng = station_latlong
            print(station_lat, station_lng)
            distance = haversine_distance(lat, lng, station_lat, station_lng)
            if distance < closest_distance:
                closest_distance = distance
                closest_station = station_id
    print(closest_station, closest_distance)
    if closest_station is not None:
        neighbors = list(graph.neighbors(closest_station))
        if neighbors:
            return closest_station, neighbors[
                0
            ]  # Return the closest station and one of its neighbors

    return None


def assign_unique_id_to_routes(passenger_data: pd.DataFrame) -> pd.DataFrame:
    """Assign a unique ID to each route in the passenger data."""
    passenger_data["route_id"] = passenger_data.index
    return passenger_data


def get_station_name_from_id(station_id: str, station_data: pd.DataFrame) -> str | None:
    """Get the station name given a station ID."""
    station_info = station_data[station_data["UniqueId"] == station_id]
    if not station_info.empty:
        return station_info.iloc[0]["Name"]
    return None


def get_line_switches(path: list[str], graph: nx.Graph) -> list[tuple[str, str, str]]:
    """Get line switches in a given path and return a list of tuples containing the station, line switched from, and line switched to."""
    line_switches = []
    for i in range(len(path) - 1):
        station1 = path[i]
        station2 = path[i + 1]
        edge_data = graph.get_edge_data(station1, station2)
        if edge_data:
            line = edge_data.get("line") or edge_data.get("line_id")
            if i > 0:
                previous_edge_data = graph.get_edge_data(path[i - 1], station1)
                previous_line = (
                    (
                        previous_edge_data.get("line")
                        or previous_edge_data.get("line_id")
                    )
                    if previous_edge_data
                    else None
                )
                if previous_line and line and previous_line != line:
                    line_switches.append((station1, previous_line, line))
    return line_switches


def get_station_latlong(
    station_id: str, station_data: pd.DataFrame
) -> tuple[float, float] | None:
    """Get the latitude and longitude of a station given its ID."""
    station_info = station_data[station_data["UniqueId"] == station_id]
    if not station_info.empty:
        lat = station_info.iloc[0]["Latitude"]
        lng = station_info.iloc[0]["Longitude"]
        return lat, lng
    return None


def get_nearest_station(
    lat: float, lng: float, station_data: pd.DataFrame
) -> str | None:
    """Get the nearest station to a given latitude and longitude."""
    if station_data.empty:
        return None

    distances = station_data.apply(
        lambda row: haversine_distance(lat, lng, row["Latitude"], row["Longitude"]),
        axis=1,
    )
    nearest_idx = distances.idxmin()
    return station_data.loc[nearest_idx, "UniqueId"]


def get_station_distance(
    station_id1: str, lat: float, lng: float, station_data: pd.DataFrame
) -> float | None:
    """Get the distance between a station and a given latitude and longitude."""
    station_latlong = get_station_latlong(station_id1, station_data)
    if station_latlong is None:
        return None
    station_lat, station_lng = station_latlong
    return haversine_distance(lat, lng, station_lat, station_lng)


def total_switch_time(
    line_switches: list[tuple[str, str, str]], switch_time: int = 5
) -> int:
    """Calculate the total time spent on line switches given a list of line switches and a fixed switch time."""
    return len(line_switches) * switch_time


def shortest_path_between_stations(
    graph: nx.Graph,
    origin: str,
    destination: str,
    line_change_penalty: float = 5.0,
) -> list[str]:
    """Calculate the shortest path considering line changes as a cost, using
    a modified Dijkstra's algorithm that tracks both the current station
    and the line you're currently on, so line changes incur a penalty.
    """
    import heapq

    # State: (total_cost, current_station, current_line, path)
    # We track the line so we can detect and penalize changes
    initial_state = (0, origin, None, [origin])
    priority_queue = [initial_state]
    visited = set()

    while priority_queue:
        cost, station, current_line, path = heapq.heappop(priority_queue)

        if station == destination:
            return path

        # Avoid revisiting same state (station + line combination)
        state_key = (station, current_line)
        if state_key in visited:
            continue
        visited.add(state_key)

        # Explore all neighboring stations
        for neighbor in graph.neighbors(station):
            edge_data = graph[station][neighbor]
            edge_line = edge_data.get("line") or edge_data.get("line_id")
            duration = float(edge_data.get("duration", 1))

            # Cost is duration + penalty if we're changing lines
            edge_cost = duration
            if (
                current_line is not None
                and edge_line is not None
                and current_line != edge_line
            ):
                edge_cost += line_change_penalty

            new_cost = cost + edge_cost
            new_state = (new_cost, neighbor, edge_line, path + [neighbor])

            heapq.heappush(priority_queue, new_state)

    return []  # No path found


def shortest_path_length_between_stations(
    graph: nx.Graph,
    origin: str,
    destination: str,
) -> int:
    """Calculate the shortest path length between two nodes in the graph."""
    try:
        length = nx.shortest_path_length(
            graph, source=origin, target=destination, weight="duration"
        )
        return length
    except nx.NetworkXNoPath:
        return float("inf")


def choose_transport_speed(distance: float) -> float:
    """choose the transport based on different distances. We say > 1.6 is bike, > 5 is bus"""
    if distance < 1.6:
        return WALK_SPEED
    if distance < 5:
        return BIKE_SPEED
    return BUS_SPEED


def determine_travel_time(distance: float) -> float:
    """Determine travel time adapted for distance"""
    return distance / choose_transport_speed(distance)


class PassengerAgent(mesa.Agent):
    """An agent representing a passenger in the simulation."""

    def __init__(
        self,
        unique_id: int,
        model,
        passenger_id: str,
        origin_lat: float,
        origin_lng: float,
        destination_lat: float,
        destination_lng: float,
        day_type: str,
    ):
        """Passenger agent in simulation. An agent wants to get from an origin to a stop at a certain time."""
        super().__init__(model)
        self.unique_id = unique_id
        self.origin_lat = origin_lat
        self.origin_lng = origin_lng
        self.passenger_id = passenger_id
        self.destination_lat = destination_lat
        self.destination_lng = destination_lng
        self.day_type = day_type
        self.walking_speed = WALK_SPEED
        self.bus_speed = BUS_SPEED
        self.cycle_speed = BIKE_SPEED
        self.nearest_station = None
        self.alighting_station = None
        self.time_spent = 0
        self.transit_time = 0

    def look_for_nearest_stop(self) -> None:
        """Look for the nearest stop to the passenger's origin."""
        nearest_station = get_nearest_station(
            self.origin_lat, self.origin_lng, self.model.station_data
        )
        nearest_destination_station = get_nearest_station(
            self.destination_lat, self.destination_lng, self.model.station_data
        )
        self.nearest_station = nearest_station
        self.alighting_station = nearest_destination_station

    def go_to_nearest_station(self):
        """Simulate the passenger walking to the nearest station."""
        distance_to_station = get_station_distance(
            self.nearest_station,
            self.origin_lat,
            self.origin_lng,
            self.model.station_data,
        )
        self.time_spent += determine_travel_time(
            distance_to_station
        )  # Assuming walking speed of 5 km/h
        self.transit_time += determine_travel_time(distance_to_station)

    def wait_for_transport(self):
        """Simulate the passenger waiting for transport at the station. cool but gonna ignore for now"""
        pass

    def travel_on_transport(self, boarding_stop_id: str, alighting_stop_id: str):
        """Simulate the passenger traveling on transport from the station to their destination."""
        duration = shortest_path_length_between_stations(
            self.model.G,
            origin=boarding_stop_id,
            destination=alighting_stop_id,
        )
        all_switches = get_line_switches(
            shortest_path_between_stations(
                self.model.G,
                origin=boarding_stop_id,
                destination=alighting_stop_id,
            ),
            self.model.G,
        )
        self.time_spent += duration + total_switch_time(all_switches)

    def go_to_destination(self):
        """Simulate the passenger walking from the station to their final destination."""
        alighting_latlong = get_station_latlong(
            self.alighting_station, self.model.station_data
        )
        if alighting_latlong is None:
            return
        alighting_lat, alighting_lng = alighting_latlong
        distance_to_destination = haversine_distance(
            self.destination_lat, self.destination_lng, alighting_lat, alighting_lng
        )
        get_to_destination_time = determine_travel_time(distance_to_destination)
        self.transit_time += get_to_destination_time
        self.time_spent += get_to_destination_time

    def travel(self):
        """Simulate the passenger's travel from origin to destination."""
        self.go_to_nearest_station()
        self.wait_for_transport()
        self.travel_on_transport(self.nearest_station, self.alighting_station)
        self.go_to_destination()

    def step(self):
        """Advance the agent's state by one step."""
        self.look_for_nearest_stop()
        self.travel()
        if self.time_spent > 100:
            print(
                "Passenger {} has been traveling for a long time ({} minutes). Walk time: {} minutes.".format(
                    self.passenger_id, self.time_spent, self.transit_time
                )
            )


class TravelModel(mesa.Model):
    """A model which combines passenger agents and their overall movement."""

    def __init__(
        self,
        graph: nx.Graph,
        station_data: pd.DataFrame,
        new_stations: list[dict] = None,
    ):
        super().__init__()
        self.num_agents = 1
        self.station_data = station_data
        self.new_stations = new_stations if new_stations is not None else []
        for station in self.new_stations:
            add_station_to_network(
                graph,
                station["UniqueId"],
                station["Latitude"],
                station["Longitude"],
                station["Line_id"],
                self.station_data,
            )
        self.station_ids = [
            new_station["UniqueId"] for new_station in self.new_stations
        ]
        self.G = graph

    def step(self):
        """Advance the model by one step."""
        for agent in self.agents.shuffle():
            agent.step()


def extract_agent_data(model: TravelModel) -> pd.DataFrame:
    """Extract data from all agents in the model and return as a DataFrame."""
    agent_data = []

    for agent in model.agents:
        agent_data.append(
            {
                "route_id": agent.unique_id,
                "passenger_id": agent.passenger_id,
                "origin_lat": agent.origin_lat,
                "origin_lng": agent.origin_lng,
                "destination_lat": agent.destination_lat,
                "destination_lng": agent.destination_lng,
                "day_type": agent.day_type,
                "nearest_station": get_station_name_from_id(
                    agent.nearest_station, model.station_data
                ),
                "alighting_station": get_station_name_from_id(
                    agent.alighting_station, model.station_data
                ),
                "time_spent": agent.time_spent,
                "walk_time": agent.transit_time,
            }
        )

    return pd.DataFrame(agent_data)


def create_agents_from_passenger_data(passenger_data: pd.DataFrame, model: TravelModel):
    """Create agents from passenger data and add them to the model."""

    for index, row in passenger_data.iterrows():
        agent = PassengerAgent(
            unique_id=row["route_id"],
            model=model,
            passenger_id=row["passenger_id"],
            origin_lat=row["origin_lat"],
            origin_lng=row["origin_lng"],
            destination_lat=row["destination_lat"],
            destination_lng=row["destination_lng"],
            day_type=row["day_type"],
        )

        # In modern Mesa, add the agent directly to the model's AgentSet container
        model.agents.add(agent)


if __name__ == "__main__":
    graph = load_graphml("stations/tube_network.graphml")
    station_data = pd.read_csv("stations/Stations.csv")
    model = TravelModel(graph, station_data)
    passenger_data = assign_unique_id_to_routes(
        load_user_information("simulation/passengers.csv")
    )
    # create_agents_from_passenger_data(passenger_data, model)

    # # Run simulation
    # model.step()

    # # Extract results
    # results_df = extract_agent_data(model)
    # print(results_df)

    # # Optionally save to CSV
    # results_df.to_csv("simulation/simulation_results.csv", index=False)
    new_station = {
        "UniqueId": "user_station_1",
        "Name": "User Station",
        "Latitude": 51.5175221,
        "Longitude": -0.0532169,
        "Line_id": "district",
    }
    station_data = add_station_to_stations_data(
        station_data,
        new_station["UniqueId"],
        new_station["Latitude"],
        new_station["Longitude"],
        new_station["Line_id"],
        new_station["Name"],
    )
    model_new = TravelModel(graph, station_data, new_stations=[new_station])
    create_agents_from_passenger_data(passenger_data, model_new)
    model_new.step()
    results_df_new = extract_agent_data(model_new)
    results_df_new.to_csv(
        "simulation/simulation_results_with_user_station.csv", index=False
    )
