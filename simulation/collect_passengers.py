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

    def look_for_nearest_stop(self):
        """Look for the nearest stop to the passenger's origin."""
        pass

    def walk_to_station(self):        
        """Simulate the passenger walking to the nearest station."""
        pass

    def wait_for_transport(self):
        """Simulate the passenger waiting for transport at the station. cool but gonna ignore for now"""
        pass

    def travel_on_transport(self):
        """Simulate the passenger traveling on transport from the station to their destination."""
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

    def 


if __name__ == "__main__":
    df = load_user_information(load_sample_demand())
    print(df.head())
