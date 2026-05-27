"""Obtain a sequence of stops for a given route and direction."""


import logging
from api_utils import make_api_call_with_retry
from get_lines import get_lines

# From https://api-portal.tfl.gov.uk/api-details#api=Line&operation=Line_RouteSequenceByPathIdPathDirectionQueryServiceTypesQueryExcludeCrowding

possible_directions = ["inbound"]
BASE_URL = "https://api.tfl.gov.uk/Line/{id}/Route/Sequence/{direction}"


def get_sequenced_stops(line_id: str, direction: str) -> list[list[str]]:
    """Get a sequence of stops (stationIDs) for a given line and direction."""
    url = BASE_URL.format(id=line_id, direction=direction)
    logging.info(f"Fetching sequenced stops from {url}")
    data = make_api_call_with_retry(url)

    if isinstance(data, dict) and "orderedLineRoutes" in data:
        return [
            data["orderedLineRoutes"][i]["naptanIds"]
            for i in range(len(data["orderedLineRoutes"]))
        ]
    return []


if __name__ == "__main__":
    possible_lines = get_lines()
    for line_id in possible_lines:
        direction = "inbound"
        stops = get_sequenced_stops(line_id, direction)
        print(stops)
