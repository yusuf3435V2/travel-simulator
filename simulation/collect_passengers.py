"""Collect passengers and their journeys from the TFL API load them as agents in the simulation."""

import networkx as nx
import mesa
import matplotlib.pyplot as plt
import json
import pandas as pd


def load_sample_demand() -> list[dict]:
    """Load sample demand defined in the simulation directory."""
    with open("simulation/sample_demand.json", "r") as f:
        data = json.load(f)
    return data


def load_user_information(data: list[dict]) -> pd.DataFrame:
    """Load user information from a JSON file."""
    return pd.DataFrame(data)


def get_line_switches(path: list[str], graph: nx.Graph) -> list[tuple[str, str, str]]:
    """Get line switches in a given path and return a list of tuples containing the station, line switched from, and line switched to."""
    line_switches = []
    for i in range(len(path) - 1):
        station1 = path[i]
        station2 = path[i + 1]
        edge_data = graph.get_edge_data(station1, station2)
        if edge_data:
            line = edge_data.get("line")
            if i > 0:
                previous_edge_data = graph.get_edge_data(path[i - 1], station1)
                previous_line = (
                    previous_edge_data.get("line") if previous_edge_data else None
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
    station_data["Distance"] = (
        (station_data["Latitude"] - lat) ** 2 + (station_data["Longitude"] - lng) ** 2
    ) ** 0.5
    nearest_station = station_data.loc[station_data["Distance"].idxmin()]
    return nearest_station["UniqueId"] if not nearest_station.empty else None


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
            edge_line = edge_data.get("line", "")
            duration = float(edge_data.get("duration", 0))

            # Cost is duration + penalty if we're changing lines
            edge_cost = duration
            if current_line is not None and current_line != edge_line:
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
        super().__init__(unique_id, model)
        self.origin_lat = origin_lat
        self.origin_lng = origin_lng
        self.passenger_id = passenger_id
        self.destination_lat = destination_lat
        self.destination_lng = destination_lng
        self.day_type = day_type
        self.time_spent = 0

    def look_for_nearest_stop(self):
        """Look for the nearest stop to the passenger's origin."""
        pass

    def walk_to_station(self):
        """Simulate the passenger walking to the nearest station."""
        pass

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
        pass

    def walk_to_destination(self):
        """Simulate the passenger walking from the station to their final destination."""
        pass

    def travel(self):
        """Simulate the passenger's travel from origin to destination."""
        self.walk_to_station()
        self.wait_for_transport()
        self.travel_on_transport()
        self.walk_to_destination()

    def step(self):
        """Advance the agent's state by one step."""
        self.look_for_nearest_stop()
        self.travel()


class TravelModel(mesa.Model):
    """A model which combines passenger agents and their overall movement."""

    def __init__(self):
        super().__init__()
        self.num_agents = 10
        self.G = nx.read_graphml("stations/tube_network.graphml")
        self.station_data = pd.read_csv("stations/station_data.csv")

    def step(self):
        """Advance the model by one step."""
        for agent in self.schedule.agents:
            agent.step()


if __name__ == "__main__":
    df = load_user_information(load_sample_demand())
    print(df.head())
