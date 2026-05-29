"""Minimal coverage context analysis for the dashboard."""

from io import StringIO
import boto3
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point


def load_stations_from_s3(bucket_name: str, key: str) -> pd.DataFrame:
    """Load station CSV from S3 into a pandas DataFrame."""
    s3 = boto3.client("s3")

    response = s3.get_object(
        Bucket=bucket_name,
        Key=key,
    )

    csv_text = response["Body"].read().decode("utf-8")
    return pd.read_csv(StringIO(csv_text))


def create_coverage_context(stations_df: pd.DataFrame, proposed_lat: float, proposed_lon: float, radius_m: int = 800,) -> dict:
    """Create a simple coverage context around the proposed station location."""

    stations_gdf = gpd.GeoDataFrame(
        stations_df,
        geometry=gpd.points_from_xy(
            stations_df["Longitude"],
            stations_df["Latitude"]
        ),
        crs="EPSG:4326",
    ).to_crs("EPSG:27700")

    proposed_gdf = gpd.GeoDataFrame(
        {"name": ["Proposed Station"]},
        geometry=[Point(proposed_lon, proposed_lat)],
        crs="EPSG:4326",
    ).to_crs("EPSG:27700")

    proposed_point = proposed_gdf.geometry.iloc[0]
    catchment = proposed_point.buffer(radius_m)

    stations_gdf["distance_m"] = stations_gdf.geometry.distance(proposed_point)

    stations_within = stations_gdf[stations_gdf.within(catchment)]

    nearest_station = stations_gdf.sort_values("distance_m").iloc[0]

    station_name_col = "Name"

    stations_within_count = stations_within[station_name_col].nunique()

    affected_lines = (
        stations_within["Line_id"]
        .dropna()
        .unique()
        .tolist()
    )

    if stations_within_count == 0:
        coverage_level = "Low"
    elif stations_within_count <= 2:
        coverage_level = "Medium"
    else:
        coverage_level = "High"

    return {
        "stations_within_catchment": int(stations_within_count),
        "nearest_station_name": nearest_station[station_name_col],
        "nearest_station_distance_m": round(float(nearest_station["distance_m"]), 1),
        "affected_lines": affected_lines,
        "coverage_level": coverage_level,
    }


def get_coverage_context_from_s3(
    proposed_lat: float,
    proposed_lon: float,
    bucket_name: str = "c23-travel-simulation-bucket",
    stations_key: str = "processed/stations.csv",
    radius_m: int = 800,
) -> dict:
    """Load station data from S3 and return coverage context."""
    stations_df = load_stations_from_s3(
        bucket_name=bucket_name,
        key=stations_key,
    )

    return create_coverage_context(
        stations_df=stations_df,
        proposed_lat=proposed_lat,
        proposed_lon=proposed_lon,
        radius_m=radius_m,
    )



if __name__ == "__main__":
    context = get_coverage_context_from_s3(
        proposed_lat=51.5074,
        proposed_lon=-0.1278,
    )

    print("\nCoverage Context:")
    print(context)

