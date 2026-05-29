import pandas as pd


def compare_simulations(
    results_df1: pd.DataFrame, results_df2: pd.DataFrame
) -> pd.DataFrame:
    """
    Compares two simulation results DataFrames and returns a summary of differences.

    Parameters:
    - results_df1: DataFrame containing results from the first simulation.
    - results_df2: DataFrame containing results from the second simulation.

    Returns:
    - A DataFrame summarizing the differences between the two simulations.
    """
    # Merge the two DataFrames on 'route_id' to compare their attributes
    comparison_df = pd.merge(
        results_df1, results_df2, on="route_id", suffixes=("_sim1", "_sim2")
    )

    # Calculate differences in key attributes (e.g., total_travel_time)
    comparison_df["time_spent_diff"] = (
        comparison_df["time_spent_sim2"] - comparison_df["time_spent_sim1"]
    )

    # You can add more comparisons as needed (e.g., number of line switches, routes taken, etc.)

    return comparison_df[comparison_df["time_spent_diff"] != 0][
        [
            "route_id",
            "time_spent_sim1",
            "time_spent_sim2",
            "time_spent_diff",
        ]
    ]


if __name__ == "__main__":
    # Load simulation results from CSV files
    results_df1 = pd.read_csv("simulation/simulation_results.csv")
    results_df2 = pd.read_csv("simulation/simulation_results_with_user_station.csv")

    # Compare the two simulations
    comparison_df = compare_simulations(results_df1, results_df2)

    # Print the comparison results
    print(comparison_df)
