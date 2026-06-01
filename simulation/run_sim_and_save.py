from collect_passengers import (
    run_simulation_baseline,
    run_simulation_with_user_station,
    assign_unique_id_to_routes,
)
from result_analysis import compare_simulations
from s3_utils_sim import (
    load_env_variables,
    check_baseline_exists_in_s3,
    load_results_from_s3,
    save_dataframe_to_s3,
    fetch_graph_from_s3,
    fetch_station_data_from_s3,
    fetch_passenger_data_from_s3,
    save_json_to_s3,
)
import time
import logging
import json
import os


def lambda_handler(event, context):
    # Run the baseline simulation and save results
    running_time = time.time()
    graph = fetch_graph_from_s3(load_env_variables())
    station_data = fetch_station_data_from_s3(load_env_variables())
    passenger_data = fetch_passenger_data_from_s3(load_env_variables())
    if not check_baseline_exists_in_s3():
        logging.info(
            "Baseline simulation results not found in S3. Running baseline simulation..."
        )
        baseline_results = run_simulation_baseline(graph, station_data, passenger_data)
        save_dataframe_to_s3(
            baseline_results,
            load_env_variables(),
            "raw/BASELINE.csv",
        )
    else:
        logging.info(
            "Baseline simulation results already exist in S3. Skipping baseline simulation."
        )
        print("LOADING BASELINE FILE")
        baseline_results = load_results_from_s3(
            load_env_variables(), "raw/BASELINE.csv"
        )
    event["number_of_passengers"] = len(baseline_results)
    # Run the altered simulation with user station and save results
    simulated_output = run_simulation_with_user_station(
        graph, station_data, [event], passenger_data
    )
    save_dataframe_to_s3(
        simulated_output,
        load_env_variables(),
        f"raw/{int(running_time)}/simulation_results_with_user_station.csv",
    )
    save_json_to_s3(
        json.dumps(event),
        load_env_variables(),
        f"raw/{int(running_time)}/user_station.json",
    )
    # Compare the baseline and altered simulation results
    baseline_vs_simulated = compare_simulations(baseline_results, simulated_output)
    comparison_path = "simulation/simulation_comparison.csv"
    baseline_vs_simulated.to_csv(comparison_path, index=False)
    save_dataframe_to_s3(
        baseline_vs_simulated,
        load_env_variables(),
        f"raw/{int(running_time)}/simulation_comparison.csv",
    )
    # Save JSON of station data to S3 for frontend use
