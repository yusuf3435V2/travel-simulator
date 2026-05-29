"""Mathematical functions for calculating distances and paths between stations."""

import math

RADIUS_OF_EARTH = 6371


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Determine the Haversine distance between two lat/long points (in km)."""

    d_lat = (lat2 - lat1) * math.pi / 180.0
    d_lon = (lon2 - lon1) * math.pi / 180.0

    lat1_rad = lat1 * math.pi / 180.0
    lat2_rad = lat2 * math.pi / 180.0

    a = (math.sin(d_lat / 2) ** 2) + (math.sin(d_lon / 2) ** 2) * math.cos(
        lat1_rad
    ) * math.cos(lat2_rad)
    c = 2 * math.asin(math.sqrt(a))
    return RADIUS_OF_EARTH * c
