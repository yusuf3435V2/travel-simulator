import pandas as pd

# Create a color scale based on the time spent difference


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
