"""Obtain tube line information from the TFL API."""


import logging
from api_utils import make_api_call_with_retry, setup_logger

BASE_URL = "https://api.tfl.gov.uk/Line/Mode/tube"

# "https://api.tfl.gov.uk/Line/Mode/tube,elizabeth-line,dlr"
# From https://api-portal.tfl.gov.uk/api-details#api=Line&operation=Line_MetaModes


def get_lines(mode: str = "tube") -> list[str]:
    """Get all tube lines from the TFL API."""
    url = f"https://api.tfl.gov.uk/Line/Mode/{mode}"
    logging.info("Fetching %s lines from TFL API", mode)
    data = make_api_call_with_retry(url)
    if isinstance(data, list):
        lines = [line["id"] for line in data]
        logging.info("Successfully fetched %s lines", len(lines))
        return lines
    logging.warning("No lines found or data in unexpected format")
    return []


if __name__ == "__main__":
    setup_logger()
    station_lines = get_lines()
    print(station_lines)
