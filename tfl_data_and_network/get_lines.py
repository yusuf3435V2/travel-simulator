"""Obtain tube line information from the TFL API."""


import logging
from api_utils import make_api_call_with_retry

BASE_URL = "https://api.tfl.gov.uk/Line/Mode/tube"

# From https://api-portal.tfl.gov.uk/api-details#api=Line&operation=Line_MetaModes


def get_lines() -> list[str]:
    """Get all tube lines from the TFL API."""
    logging.info(f"Fetching lines from {BASE_URL}")
    data = make_api_call_with_retry(BASE_URL)
    if isinstance(data, list):
        return [line["id"] for line in data]
    elif isinstance(data, dict) and "id" in data:
        return [data["id"]]
    return []


if __name__ == "__main__":
    lines = get_lines()
    print(lines)
