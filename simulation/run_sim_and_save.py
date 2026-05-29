from collect_passengers import run_simulation_baseline, run_simulation_with_user_station
from result_analysis import compare_simulations
from save_results_to_s3 import (
    save_results_to_s3,
    load_env_variables,
    check_baseline_exists_in_s3,
    load_results_from_s3,
)
import time
import logging


if __name__ == "__main__":
    # Run the baseline simulation and save results
    running_time = time.time()
    if not check_baseline_exists_in_s3():
        logging.info(
            "Baseline simulation results not found in S3. Running baseline simulation..."
        )
        run_simulation_baseline()
        save_results_to_s3(
            "simulation/simulation_results.csv",
            load_env_variables(),
            "raw/BASELINE.csv",
        )
    else:
        logging.info(
            "Baseline simulation results already exist in S3. Skipping baseline simulation."
        )
        baseline_results = load_results_from_s3(
            load_env_variables(), "raw/BASELINE.csv"
        )
    example_station = {
        "UniqueId": "user_station_1",
        "Name": "User Station",
        "Latitude": 51.5175221,
        "Longitude": -0.0532169,
        "Line_id": "district",
    }
    # Run the altered simulation with user station and save results
    simulated_output = run_simulation_with_user_station([example_station])
    save_results_to_s3(
        "simulation/simulation_results_with_user_station.csv",
        load_env_variables(),
        f"raw/{int(running_time)}_simulation_results_with_user_station.csv",
    )
    # Compare the baseline and altered simulation results
    baseline_vs_simulated compare_simulations(baseline_results, simulated_output)
    

