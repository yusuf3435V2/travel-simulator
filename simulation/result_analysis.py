import pandas as pd


def compare_simulations(
    baseline_journeys: pd.DataFrame, altered_journeys: pd.DataFrame
) -> pd.DataFrame:
    """Compares a baseline and altered simulation to identify differences in passenger journeys."""
    # Merge the two DataFrames on 'route_id' to compare their attributes
    comparison_df = pd.merge(
        baseline_journeys,
        altered_journeys,
        on="route_id",
        suffixes=("_baseline", "_altered"),
    )

    # Calculate differences in key attributes (e.g., total_travel_time)
    comparison_df["time_spent_diff"] = (
        comparison_df["time_spent_altered"] - comparison_df["time_spent_baseline"]
    )

    # You can add more comparisons as needed (e.g., number of line switches, routes taken, etc.)
    print(comparison_df.columns)
    return comparison_df[comparison_df["time_spent_diff"] != 0][
        [
            "route_id",
            "origin_lat_baseline",
            "origin_lng_baseline",
            "nearest_station_baseline",
            "alighting_station_baseline",
            "nearest_station_altered",
            "alighting_station_altered",
            "destination_lat_baseline",
            "destination_lng_baseline",
            "time_spent_baseline",
            "time_spent_altered",
            "time_spent_diff",
        ]
    ]


if __name__ == "__main__":
    # Load simulation results from CSV files
    baseline_journeys = pd.read_csv("simulation/simulation_results.csv")
    altered_journeys = pd.read_csv(
        "simulation/simulation_results_with_user_station.csv"
    )

    # Compare the two simulations
    comparison_df = compare_simulations(baseline_journeys, altered_journeys)

    # Print the comparison results
    comparison_df.to_csv("simulation/simulation_comparison.csv", index=False)
