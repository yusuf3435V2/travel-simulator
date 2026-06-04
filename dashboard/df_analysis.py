import pandas as pd
import numpy as np
import altair as alt

# Create a color scale based on the time spent difference


def logistic(x: float) -> float:
    """Logistic function used to map time differences to switching probabilities."""
    return 1 / (1 + np.exp(-x))


def get_color(time_spent_diff, greatest_timesave):
    """Color code based on time spent difference."""
    if pd.isna(time_spent_diff):
        return "blue"  # No impact data
    elif time_spent_diff == greatest_timesave:
        return "red"
    elif time_spent_diff > 0:
        return "orange"
    else:
        return "green"


def remove_uninfluenced_stations(comparison_df) -> pd.DataFrame:
    """Filter out stations that have no change in demand."""
    # This would be where user station does not exist in the altered
    # simulation, so we only want to show stations that are affected
    return comparison_df[
        (comparison_df["nearest_station_altered"] != "User Station")
        & (comparison_df["alighting_station_altered"] != "User Station")
    ].copy()


def get_passenger_station_counts(comparison_df) -> pd.DataFrame:
    """Get the count of passengers associated with each station."""
    origin_counts = comparison_df["nearest_station_baseline"].value_counts()
    destination_counts = comparison_df["alighting_station_baseline"].value_counts()
    station_counts = origin_counts.add(destination_counts, fill_value=0).reset_index()
    station_counts.columns = ["Station", "Passenger Count"]
    return station_counts


def get_affected_routes(comparison_df) -> pd.DataFrame:
    """Get all affected routes by proposed station. We also want to combine backwards and forwards affected routes to get a full picture of the impact."""
    comparison_df = comparison_df.copy()
    comparison_df[["station_alpha", "station_omega"]] = np.sort(
        comparison_df[["nearest_station_baseline", "alighting_station_baseline"]],
        axis=1,
    )

    # 2. Combine them into a single clean route identifier string
    comparison_df["bidirectional_route"] = (
        comparison_df["station_alpha"] + " ⇄ " + comparison_df["station_omega"]
    )

    # 3. Now perform your standard groupby on the unified key!
    summary_df = comparison_df.groupby("bidirectional_route").agg(
        total_impacted_routes=("route_id", "count"),
        avg_time_difference=("time_spent_diff", "mean"),
        maximum_time_difference=("time_spent_diff", "max"),
        minimum_time_difference=("time_spent_diff", "min"),
    )
    summary_df = summary_df.rename(
        columns={
            "total_impacted_routes": "Total Affected Routes",
            "avg_time_difference": "Average Time Spent Difference (mins)",
            "maximum_time_difference": "Maximum Time Spent Difference (mins)",
            "minimum_time_difference": "Minimum Time Spent Difference (mins)",
        }
    )
    summary_df.index.name = "Route"
    return summary_df


def change_standard_deviation_to_zero_if_nan(df, column_name):
    """Replace NaN standard deviation values with zero."""
    df[column_name] = df[column_name].fillna(0)
    return df


def add_dataframes(df1, df2, fill_value=0):
    """Add two DataFrames together, filling missing values with a specified fill_value."""
    return df1.add(df2, fill_value=fill_value)




def get_demand_impact_ranges(comparison_df) -> pd.DataFrame:
    """Get the range of demand impacts across all stations."""
    passenger_station_counts = get_passenger_station_counts(comparison_df)
    df = comparison_df.assign(switch_prob=logistic(-comparison_df["time_spent_diff"]))[
        ["alighting_station_altered", "nearest_station_baseline", "switch_prob"]
    ]
    station_probs = df.melt(
        id_vars="switch_prob",
        value_vars=["alighting_station_altered", "nearest_station_baseline"],
        value_name="Station",
    )[["Station", "switch_prob"]]
    station_impact = (
        station_probs.groupby("Station")["switch_prob"]
        .agg(["sum", "std"])
        .reset_index()
    )
    total_passengers = passenger_station_counts["Passenger Count"].sum()

    station_impact = change_standard_deviation_to_zero_if_nan(station_impact, "std")
    station_impact["lower_bound"] = station_impact["sum"] - 1.96 * station_impact["std"]
    station_impact["upper_bound"] = station_impact["sum"] + 1.96 * station_impact["std"]
    station_impact["lower_bound_percentage"] = (
        station_impact["lower_bound"] / total_passengers
    )
    station_impact["upper_bound_percentage"] = (
        station_impact["upper_bound"] / total_passengers
    )
    station_impact["Demand Change Range (%)"] = station_impact.apply(
        lambda row: (
            f"{row['lower_bound_percentage']:.4%} - {row['upper_bound_percentage']:.4%}"
        ),
        axis=1,
    )
    station_impact = station_impact[
        ~station_impact["Station"].isin(["User Station", "User Proposed Station"])
    ]
    station_impact = station_impact[np.isfinite(station_impact["upper_bound_percentage"])]
    station_impact.drop(
        columns=[
            "sum",
            "std",
            "lower_bound",
            "upper_bound",
            "lower_bound_percentage",
            "upper_bound_percentage",
        ],
        inplace=True,
    )
    station_impact = station_impact.set_index("Station")

    return station_impact


def get_total_time_spent_diff(comparison_df):
    """Calculate the total time spent difference across all routes."""
    if comparison_df.empty:
        return 0
    return comparison_df["time_spent_diff"].sum()


def get_greatest_time_spent_diff(comparison_df):
    """Calculate the greatest time spent difference across all routes."""
    if comparison_df.empty:
        return 0
    return comparison_df[
        "time_spent_diff"
    ].min()  # Assuming negative is greatest timesave


def get_percentage_of_affected_routes(comparison_df, number_of_routes: int) -> float:
    """Calculate the percentage of routes affected by the proposed station."""
    if comparison_df.empty or number_of_routes == 0:
        return 0.0
    affected_routes = comparison_df.shape[0]
    return (affected_routes / number_of_routes) * 100


def create_top_affected_routes_chart(comparison_df: pd.DataFrame) -> alt.Chart:
    """Create a bar chart showing the routes with the most affected passenger journeys."""

    df = comparison_df.copy()

    df[["station_alpha", "station_omega"]] = pd.DataFrame(
        sorted([a, b])
        for a, b in zip(
            df["nearest_station_baseline"],
            df["alighting_station_baseline"],
        )
    )

    df["route"] = df["station_alpha"] + " ⇄ " + df["station_omega"]

    route_summary = (
        df.groupby("route")
        .size()
        .reset_index(name="affected_journeys")
        .sort_values("affected_journeys", ascending=False)
        .head(10)
    )

    return (
        alt.Chart(route_summary)
        .mark_bar()
        .encode(
            x=alt.X("affected_journeys:Q", title="Affected journeys"),
            y=alt.Y("route:N", sort="-x", title="Route"),
            tooltip=["route", "affected_journeys"],
        )
        .properties(
            title="Top 10 Most Affected Routes",
            height=350,
        )
    )


def create_top_time_saving_routes_chart(comparison_df: pd.DataFrame) -> alt.Chart:
    """Create a bar chart showing bidirectional routes with the largest average time saving."""

    df = comparison_df.copy()

    df[["station_alpha", "station_omega"]] = np.sort(
        df[["nearest_station_baseline", "alighting_station_baseline"]],
        axis=1,
    )

    df["route"] = (
        df["station_alpha"].astype(str)
        + " ⇄ "
        + df["station_omega"].astype(str)
    )

    route_summary = (
        df.groupby("route")
        .agg(
            average_time_difference_mins=("time_spent_diff", "mean"),
            affected_journeys=("route", "count"),
        )
        .reset_index()
    )

    # Negative time_spent_diff means time saved.
    route_summary["average_time_saved_mins"] = (
        -route_summary["average_time_difference_mins"]
    )

    route_summary = (
        route_summary[route_summary["average_time_saved_mins"] > 0]
        .sort_values("average_time_saved_mins", ascending=False)
        .head(10)
    )

    return (
        alt.Chart(route_summary)
        .mark_bar(color="skyblue")
        .encode(
            x=alt.X(
                "average_time_saved_mins:Q",
                title="Average time saved minutes",
            ),
            y=alt.Y(
                "route:N",
                sort="-x",
                title="Route",
            ),
            tooltip=[
                "route",
                "average_time_saved_mins",
                "affected_journeys",
            ],
        )
        .properties(
            title="Bidirectional Routes With Highest Average Time Saving",
            height=350,
        )
    )


def create_station_demand_impact_chart(comparison_df: pd.DataFrame) -> alt.Chart:
    """Create a bar chart showing stations with the highest total time impact."""

    df = comparison_df.copy()

    origin_impact = (
        df.groupby("nearest_station_baseline")["time_spent_diff"]
        .sum()
        .reset_index()
        .rename(
            columns={
                "nearest_station_baseline": "station",
                "time_spent_diff": "total_time_impact_mins",
            }
        )
    )

    destination_impact = (
        df.groupby("alighting_station_baseline")["time_spent_diff"]
        .sum()
        .reset_index()
        .rename(
            columns={
                "alighting_station_baseline": "station",
                "time_spent_diff": "total_time_impact_mins",
            }
        )
    )

    station_summary = (
        pd.concat([origin_impact, destination_impact])
        .groupby("station")["total_time_impact_mins"]
        .sum()
        .reset_index()
    )

    station_summary["absolute_impact"] = station_summary[
        "total_time_impact_mins"
    ].abs()

    station_summary = (
        station_summary.sort_values("absolute_impact", ascending=False)
        .head(10)
    )

    return (
        alt.Chart(station_summary)
        .mark_bar(color="#ADE8F4")
        .encode(
            x=alt.X("total_time_impact_mins:Q",
                    title="Total time impact minutes"),
            y=alt.Y("station:N", sort="-x", title="Station"),
            tooltip=[
                "station",
                "total_time_impact_mins",
            ],
        )
        .properties(
            title="Stations With Highest Overall Impact",
            height=350,
        )
    )
