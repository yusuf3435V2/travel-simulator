"""Tests for pure functions in dashboard/df_analysis.py."""

import sys
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import pytest

DASHBOARD_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DASHBOARD_DIR))

from df_analysis import (  # noqa: E402
    add_dataframes,
    change_standard_deviation_to_zero_if_nan,
    create_station_demand_impact_chart,
    create_top_affected_routes_chart,
    create_top_time_saving_routes_chart,
    get_affected_routes,
    get_color,
    get_demand_impact_ranges,
    get_greatest_time_spent_diff,
    get_passenger_station_counts,
    get_percentage_of_affected_routes,
    get_total_time_spent_diff,
    remove_uninfluenced_stations,
)


@pytest.mark.parametrize(
    "time_spent_diff, greatest_timesave, expected_colour",
    [
        (np.nan, -5, "blue"),
        (-5, -5, "red"),
        (3, -5, "orange"),
        (-2, -5, "green"),
    ],
)
def test_get_color(time_spent_diff, greatest_timesave, expected_colour):
    assert get_color(time_spent_diff, greatest_timesave) == expected_colour


def test_remove_uninfluenced_stations_removes_user_station_rows(
    comparison_df_df_analysis,
):
    result = remove_uninfluenced_stations(comparison_df_df_analysis)

    assert len(result) == 1
    assert result.iloc[0]["route_id"] == 3


def test_get_passenger_station_counts(comparison_df_df_analysis):
    result = get_passenger_station_counts(comparison_df_df_analysis)

    assert set(result.columns) == {"Station", "Passenger Count"}
    assert result.loc[result["Station"] == "A", "Passenger Count"].iloc[0] == 3
    assert result.loc[result["Station"] == "B", "Passenger Count"].iloc[0] == 2
    assert result.loc[result["Station"] == "C", "Passenger Count"].iloc[0] == 1


def test_get_affected_routes_combines_bidirectional_routes(comparison_df_df_analysis):
    result = get_affected_routes(comparison_df_df_analysis)

    assert "A ⇄ B" in result.index
    assert result.loc["A ⇄ B", "Total Affected Routes"] == 2
    assert result.loc["A ⇄ B", "Average Time Spent Difference (mins)"] == -4.0


def test_change_standard_deviation_to_zero_if_nan():
    df = pd.DataFrame({"std": [np.nan, 2.0]})

    result = change_standard_deviation_to_zero_if_nan(df, "std")

    assert result["std"].tolist() == [0.0, 2.0]


def test_add_dataframes_with_fill_value():
    df1 = pd.DataFrame({"value": [1]}, index=["A"])
    df2 = pd.DataFrame({"value": [2]}, index=["B"])

    result = add_dataframes(df1, df2, fill_value=0)

    assert result.loc["A", "value"] == 1
    assert result.loc["B", "value"] == 2


def test_get_demand_impact_ranges_returns_station_ranges(comparison_df_df_analysis):
    result = get_demand_impact_ranges(comparison_df_df_analysis)

    assert "Demand Change Range (%)" in result.columns
    assert "User Station" not in result.index
    assert "User Proposed Station" not in result.index


def test_total_time_spent_diff(comparison_df_df_analysis):
    assert get_total_time_spent_diff(comparison_df_df_analysis) == -6.0


def test_total_time_spent_diff_empty_dataframe():
    assert get_total_time_spent_diff(pd.DataFrame()) == 0


def test_greatest_time_spent_diff(comparison_df_df_analysis):
    assert get_greatest_time_spent_diff(comparison_df_df_analysis) == -5.0


def test_greatest_time_spent_diff_empty_dataframe():
    assert get_greatest_time_spent_diff(pd.DataFrame()) == 0


@pytest.mark.parametrize(
    "number_of_routes, expected_percentage",
    [
        (0, 0.0),
        (6, 50.0),
        (3, 100.0),
    ],
)
def test_get_percentage_of_affected_routes(
    comparison_df_df_analysis,
    number_of_routes,
    expected_percentage,
):
    result = get_percentage_of_affected_routes(
        comparison_df_df_analysis, number_of_routes
    )

    assert result == expected_percentage


def test_create_top_affected_routes_chart_returns_altair_chart(
    comparison_df_df_analysis,
):
    result = create_top_affected_routes_chart(comparison_df_df_analysis)

    assert isinstance(result, alt.Chart)


def test_create_top_time_saving_routes_chart_returns_altair_chart(
    comparison_df_df_analysis,
):
    result = create_top_time_saving_routes_chart(comparison_df_df_analysis)

    assert isinstance(result, alt.Chart)


def test_create_station_demand_impact_chart_returns_altair_chart(
    comparison_df_df_analysis,
):
    result = create_station_demand_impact_chart(comparison_df_df_analysis)

    assert isinstance(result, alt.Chart)
