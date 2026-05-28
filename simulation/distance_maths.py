"""Mathematical functions for calculating distances and paths between stations."""

import math

RADIUS_OF_EARTH = 6371


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float):
    """Determine Haversine distance from one pair of latitude longitude to another (in km)"""

    # distance between latitudes
    # and longitudes
    dLat = (lat2 - lat1) * math.pi / 180.0
    dLon = (lon2 - lon1) * math.pi / 180.0

    # convert to radians
    lat1 = (lat1) * math.pi / 180.0
    lat2 = (lat2) * math.pi / 180.0

    # apply formulae
    a = pow(math.sin(dLat / 2), 2) + pow(math.sin(dLon / 2), 2) * math.cos(
        lat1
    ) * math.cos(lat2)
    c = 2 * math.asin(math.sqrt(a))
    return RADIUS_OF_EARTH * c
