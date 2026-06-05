# Fixtures


import pytest
import sys
import os
import networkx as nx
import pandas as pd

# Add the simulation module directory to sys.path so tests can import local modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from collect_passengers import load_graphml, assign_unique_id_to_routes, TravelModel


@pytest.fixture
def mock_graph_xml() -> str:
    """Provides a sample GraphML content for testing."""
    return """<?xml version='1.0' encoding='utf-8'?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">
  <key id="d1" for="edge" attr.name="duration" attr.type="long" />
  <key id="d0" for="edge" attr.name="line_id" attr.type="string" />
  <graph edgedefault="undirected">
    <node id="station1" />
    <node id="station2" />
    <edge source="station1" target="station2">
      <data key="d0">metropolitan</data>
      <data key="d1">2</data>
    </edge>
  </graph>
</graphml>"""


@pytest.fixture
def csv_content() -> str:
    """Provides a sample CSV content for testing."""
    return "col1,col2\n1,a\n2,b\n3,c\n"


@pytest.fixture
def aws_credentials(monkeypatch):
    """Mock AWS credentials."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def sample_data() -> pd.DataFrame:
    """Fixture for sample passenger data."""
    return pd.read_csv("simulation/test_data/sample_passengers.csv")


@pytest.fixture
def sample_stations() -> nx.Graph:
    """Fixture for sample station graph (5 stations). With duration weight on each edge."""
    graph = nx.Graph()
    graph.add_edge("StationA", "StationB", duration=5, line="piccadilly")
    graph.add_edge("StationB", "StationC", duration=10, line="piccadilly")
    graph.add_edge("StationC", "StationD", duration=15, line="piccadilly")
    graph.add_edge("StationD", "StationE", duration=20, line="piccadilly")
    graph.add_edge("StationA", "StationC", duration=7, line="district")
    return graph


@pytest.fixture
def sample_graph_for_tube() -> nx.Graph:
    """Fixture for loading the actual tube network graph."""
    return load_graphml("simulation/test_data/tube_network.graphml")


@pytest.fixture
def sample_station_data() -> pd.DataFrame:
    """Fixture for sample station data."""
    data = pd.read_csv("simulation/test_data/Stations.csv")
    return data


@pytest.fixture
def sample_station_graph() -> nx.Graph:
    """Fixture for loading the actual tube network graph."""
    return load_graphml("simulation/test_data/tube_network.graphml")


@pytest.fixture
def sample_passenger_data_with_ids(sample_data) -> pd.DataFrame:
    """Fixture for sample passenger data with route IDs."""
    return assign_unique_id_to_routes(sample_data)


@pytest.fixture
def model_with_sample_graph(sample_stations, sample_station_data) -> TravelModel:
    """Fixture for creating a TravelModel with sample graph."""
    model = TravelModel(sample_stations, sample_station_data)

    return model
