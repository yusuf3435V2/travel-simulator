"""Obtain tube line information from the TFL API."""

import requests as req

BASE_URL = "https://api.tfl.gov.uk/Line/Mode/tube"

# From https://api-portal.tfl.gov.uk/api-details#api=Line&operation=Line_MetaModes


def get_lines() -> list[str]:
    """Get all tube lines from the TFL API."""
    response = req.get(BASE_URL)
    if response.status_code == 200:
        return [line["id"] for line in response.json()]
    else:
        raise Exception(f"Failed to fetch lines: {response.status_code}")


if __name__ == "__main__":
    lines = get_lines()
    print(lines)
