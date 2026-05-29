"""Script for saving simulation results to S3."""

from s3_utils import load_env_variables, load_results_from_s3


if __name__ == "__main__":
    # Define the file path, bucket name, and S3 key
    # bucket_name = load_env_variables()
    # file_path = "simulation/simulation_results.csv"
    # s3_key = f"raw/{int(time.time())}_simulation_results.csv"

    # # Save the results to S3
    # save_results_to_s3(file_path, bucket_name, s3_key)
    print(
        load_results_from_s3(
            load_env_variables(), "raw/1780054354_simulation_results_BASELINE.csv"
        ).head()
    )
