"""Tests for the connect_nearby_stations function."""

import pytest

from connect_nearby_stations import unsuffix_name


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
