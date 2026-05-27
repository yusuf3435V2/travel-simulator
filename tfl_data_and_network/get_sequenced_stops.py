"""Obtain a sequence of stops for a given route and direction."""

import requests
from get_lines import get_lines

# From https://api-portal.tfl.gov.uk/api-details#api=Line&operation=Line_RouteSequenceByPathIdPathDirectionQueryServiceTypesQueryExcludeCrowding

BASE_URL = "https://api.tfl.gov.uk/Line/{id}/Route/Sequence/{direction}"


def get_sequenced_stops(line_id: str, direction: str) -> list[str]:
    """Get a sequence of stops (stationIDs) for a given line and direction."""

    url = BASE_URL.format(id=line_id, direction=direction)
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data["orderedLineRoutes"][0]["naptanIds"]
    else:
        raise Exception(f"Failed to fetch sequenced stops: {response.status_code}")


if __name__ == "__main__":
    possible_lines = get_lines()
    for line_id in possible_lines:
        direction = "inbound"
        stops = get_sequenced_stops(line_id, direction)
        print(stops)
