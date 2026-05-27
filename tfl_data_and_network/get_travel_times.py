"""Gets travel times between connected nodes in the graph."""
import logging
from api_utils import make_api_call_with_retry, setup_logger


def extract_travel_time_data(start_station_id: str, end_station_id: str) -> dict:
    """Fetch travel time data with retry logic for rate limits."""
    url = f"https://api.tfl.gov.uk/Journey/JourneyResults/{start_station_id}/to/{end_station_id}"
    logging.debug("Fetching travel time data from URL: %s", url)
    return make_api_call_with_retry(url)


def get_duration_data_from_api_data(travel_time_data: dict) -> int:
    """Extract the duration data from the travel time data."""
    if "journeys" in travel_time_data and len(travel_time_data["journeys"]) > 0:
        duration = travel_time_data["journeys"][0]["duration"]
        logging.info("Successfully extracted duration: %s minutes", duration)
        if duration >= 10:
            logging.warning(
                "Duration of %s minutes seems unusually long for adjacent stations.", duration)
        return duration
    else:
        logging.error("No journeys found in the travel time data.")
        return 2  # Return a default value of 2 minutes if no journey data is found


def get_duration_data(start_station_id: str, end_station_id: str) -> int:
    logging.info(
        "Getting duration data from %s to %s", start_station_id, end_station_id)
    travel_time_data = extract_travel_time_data(
        start_station_id, end_station_id)
    return get_duration_data_from_api_data(travel_time_data)


if __name__ == "__main__":
    setup_logger()
    logging.info("Starting get_travel_times script")
    duration = get_duration_data(
        "940GZZLUHPK", "940GZZLUNHG")
    logging.info("Travel time: %s minutes", duration)
    print(duration)
