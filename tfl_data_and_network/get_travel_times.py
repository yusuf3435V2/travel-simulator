"""Gets travel times between connected nodes in the graph."""
import requests
import logging


def setup_logger(log_level: str = "INFO") -> None:
    """
    Configure logging with the specified log_level: 
    (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(levelname)s - %(message)s',
        encoding="utf-8"
    )


def extract_travel_time_data(start_station: str, end_station: str) -> dict:
    """Download the station data zip file and extract it into the 'stations' directory."""
    url = f"https://api.tfl.gov.uk/Journey/JourneyResults/{start_station}/to/{end_station}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(
            f"Failed to fetch station data: {response.status_code}")
        return {}


def get_duration_data_from_api_data(travel_time_data: dict) -> int:
    """Extract the duration data from the travel time data."""
    if "journeys" in travel_time_data and len(travel_time_data["journeys"]) > 0:
        return travel_time_data["journeys"][0]["duration"]
    else:
        logging.error("No journeys found in the travel time data.")
        return 2  # Return a default value of 2 minutes if no journey data is found


def get_duration_data(start_station: str, end_station: str) -> int:
    travel_time_data = extract_travel_time_data(start_station, end_station)
    return get_duration_data_from_api_data(travel_time_data)


if __name__ == "__main__":
    setup_logger()
    print(get_duration_data(
        "embankment underground station", "charing cross underground station"))
