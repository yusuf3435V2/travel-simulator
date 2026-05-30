"""Tests for the connect_nearby_stations function."""

import pytest
import networkx as nx
import pandas as pd

from connect_nearby_stations import connect_nearby_stations, unsuffix_name


@pytest.mark.parametrize(
    "input_name, expected_output",
    [
        ("Baker Street Underground Station", "Baker Street"),
        ("Canary Wharf DLR Station", "Canary Wharf"),
        ("Paddington Elizabeth Line Station", "Paddington"),
        ("Stratford (London) Rail Station", "Stratford"),
        ("King's Cross St. Pancras Underground Station", "King's Cross St. Pancras"),
        ("Oxford Circus", "Oxford Circus"),  # No suffix
        ("Paddington (H&C Line)-Underground", "Paddington"),  # Suffix with parentheses
        (
            "Hammersmith (Dist&Picc Line) Underground Station",
            "Hammersmith",
        ),  # Suffix with parentheses
    ],
)
def test_unsuffix_name(input_name, expected_output):
    """Test unsuffix_name function with various station names."""
    assert unsuffix_name(input_name) == expected_output


def test_connect_nearby_stations_adds_single_transfer_edge_for_same_name_only():
    """Connect same unsuffixed names with one transfer edge and keep others disconnected."""
    graph = nx.MultiGraph()
    station_data = pd.DataFrame(
        [
            {
                "UniqueId": "PAD_1",
                "Name": "Paddington Underground Station",
                "Line_id": "bakerloo",
            },
            {
                "UniqueId": "PAD_1",
                "Name": "Paddington Underground Station",
                "Line_id": "district",
            },
            {
                "UniqueId": "PAD_2",
                "Name": "Paddington (H&C Line)-Underground",
                "Line_id": "circle",
            },
            {
                "UniqueId": "PAD_2",
                "Name": "Paddington (H&C Line)-Underground",
                "Line_id": "hammersmith-city",
            },
            {
                "UniqueId": "OXF_1",
                "Name": "Oxford Circus Underground Station",
                "Line_id": "central",
            },
            {
                "UniqueId": "OXF_1",
                "Name": "Oxford Circus Underground Station",
                "Line_id": "victoria",
            },
            {"UniqueId": "WAT_1", "Name": "Waterloo Underground Station", "Line_id": "northern"},
        ]
    )

    updated_graph = connect_nearby_stations(graph, station_data)

    assert updated_graph.has_edge("PAD_1", "PAD_2")
    assert updated_graph.number_of_edges("PAD_1", "PAD_2") == 1
    edge_data = list(updated_graph.get_edge_data("PAD_1", "PAD_2").values())[0]
    assert edge_data["duration"] == 0
    assert edge_data["line_id"] == "transfer"

    assert not updated_graph.has_edge("PAD_1", "OXF_1")
    assert not updated_graph.has_edge("PAD_2", "WAT_1")
