import pandas as pd
import numpy as np

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
        std_time_difference=("time_spent_diff", "std"),
        upper_bound_time_difference=(
            "time_spent_diff",
            lambda x: x.mean() + 1.96 * x.std(ddof=1) / np.sqrt(len(x)),
        ),
        lower_bound_time_difference=(
            "time_spent_diff",
            lambda x: x.mean() - 1.96 * x.std(ddof=1) / np.sqrt(len(x)),
        ),
        maximum_time_difference=("time_spent_diff", "max"),
        minimum_time_difference=("time_spent_diff", "min"),
    )
    summary_df = summary_df.drop(
        [
            "std_time_difference",
            "upper_bound_time_difference",
            "lower_bound_time_difference",
        ],
        axis=1,
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
