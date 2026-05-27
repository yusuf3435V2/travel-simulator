"""Obtain a sequence of stops for a given route and direction."""


import logging
from api_utils import make_api_call_with_retry, setup_logger
from get_lines import get_lines

# From https://api-portal.tfl.gov.uk/api-details#api=Line&operation=Line_RouteSequenceByPathIdPathDirectionQueryServiceTypesQueryExcludeCrowding

possible_directions = ["inbound"]
BASE_URL = "https://api.tfl.gov.uk/Line/{id}/Route/Sequence/{direction}"


def get_line_stops_data(line_id: str, direction: str) -> dict:
    """Fetch line stops data with retry logic for rate limits."""
    url = BASE_URL.format(id=line_id, direction=direction)
    logging.info(
        "Fetching sequenced stops for line %s in %s direction", line_id, direction)
    return make_api_call_with_retry(url)


def get_sequenced_stops(data: dict) -> list[list[str]]:
    """Get a sequence of stops (stationIDs) for a given line and direction."""
    if isinstance(data, dict) and "orderedLineRoutes" in data:
        stops_list = [stops["naptanIds"]
                      for stops in data["orderedLineRoutes"]]
        logging.info(
            "Successfully fetched %s route(s) with %s total stops", len(stops_list), sum(len(s) for s in stops_list))
        return stops_list
    logging.warning("No orderedLineRoutes found in data")
    return []


if __name__ == "__main__":
    setup_logger()
    possible_lines = get_lines()
    if possible_lines:
        print(get_sequenced_stops(
            get_line_stops_data(possible_lines[0], "all")))
    # for line_id in possible_lines:
    #     direction = "inbound"
    #     stops = get_sequenced_stops(line_id, direction)
    #     print(stops)
