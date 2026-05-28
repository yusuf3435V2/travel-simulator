"""Tests for collecting passengers at stations."""

from collect_passengers import load_user_information
import pytest
import pandas as pd


@pytest.fixture()
def traveller_data():
    return [
        {
            "passenger_id": "pass_001",
            "origin_lat": 51.5074,
            "origin_lng": -0.1278,
            "boarding_stop_id": "940GZZDLABC",
            "alighting_stop_id": "940GZZDLCAC",
            "route_id": "piccadilly",
            "hour_of_day": 8,
            "journey_time_mins": 35,
            "day_type": "weekday",
        },
        {
            "passenger_id": "pass_002",
            "origin_lat": 51.5151,
            "origin_lng": -0.1415,
            "boarding_stop_id": "940GZZDLBNE",
            "alighting_stop_id": "940GZZDLDPK",
            "route_id": "central",
            "hour_of_day": 9,
            "journey_time_mins": 22,
            "day_type": "weekday",
        },
        {
            "passenger_id": "pass_003",
            "origin_lat": 51.5011,
            "origin_lng": -0.1245,
            "boarding_stop_id": "910GABWDX",
            "alighting_stop_id": "910GCHDWL",
            "route_id": "district",
            "hour_of_day": 17,
            "journey_time_mins": 45,
            "day_type": "weekday",
        },
        {
            "passenger_id": "pass_004",
            "origin_lat": 51.5284,
            "origin_lng": -0.0833,
            "boarding_stop_id": "940GZZDLCLC",
            "alighting_stop_id": "940GZZDLDLT",
            "route_id": "northern",
            "hour_of_day": 7,
            "journey_time_mins": 18,
            "day_type": "weekday",
        },
        {
            "passenger_id": "pass_005",
            "origin_lat": 51.4934,
            "origin_lng": -0.1462,
            "boarding_stop_id": "910GCTSTMD",
            "alighting_stop_id": "910GILFORD",
            "route_id": "victoria",
            "hour_of_day": 14,
            "journey_time_mins": 50,
            "day_type": "weekday",
        },
    ]


def test_collect_passengers_correct_type(traveller_data):
    """test that the passengers are being collected appropriately."""
    assert isinstance(load_user_information(traveller_data), pd.DataFrame)


def test_collect_passengers_correct_columns(traveller_data):
    """columns are all in the correct format."""
    for column in [
        "passenger_id",
        "origin_lat",
        "origin_lng",
        "boarding_stop_id",
        "alighting_stop_id",
        "route_id",
        "journey_time_mins",
    ]:
        assert column in load_user_information(traveller_data).columns
