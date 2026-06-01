"""KML export generation for Google Earth Pro."""
from io import BytesIO
import zipfile
import geopandas as gpd
import simplekml
from shapely.geometry import Point
from coverage_context import load_stations_from_s3


def get_affected_stations(
    proposed_lat: float,
    proposed_lon: float,
    bucket_name: str = "c23-travel-simulation-bucket",
    stations_key: str = "processed/stations.csv",
    radius_m: int = 800,
) -> tuple:
    """Return affected stations and catchment geometry."""

    stations_df = load_stations_from_s3(
        bucket_name=bucket_name,
        key=stations_key,
    )

    stations_gdf = gpd.GeoDataFrame(
        stations_df,
        geometry=gpd.points_from_xy(
            stations_df["Longitude"],
            stations_df["Latitude"],
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

    affected_stations = stations_gdf[stations_gdf.within(catchment)]

    catchment_gdf = gpd.GeoDataFrame(
        {"name": ["Walking Catchment"]},
        geometry=[catchment],
        crs="EPSG:27700",
    ).to_crs("EPSG:4326")

    return affected_stations.to_crs("EPSG:4326"), catchment_gdf


def generate_kml_bytes(
    proposed_lat: float,
    proposed_lon: float,
    selected_line: str,
    bucket_name: str = "c23-travel-simulation-bucket",
    stations_key: str = "processed/stations.csv",
    radius_m: int = 800,
) -> bytes:
    """Generate a KML file showing proposed station, catchment and affected stops."""

    affected_stations, catchment_gdf = get_affected_stations(
        proposed_lat=proposed_lat,
        proposed_lon=proposed_lon,
        bucket_name=bucket_name,
        stations_key=stations_key,
        radius_m=radius_m,
    )

    kml = simplekml.Kml()

    proposed = kml.newpoint(
        name="Proposed Station",
        coords=[(proposed_lon, proposed_lat)],
    )
    proposed.description = f"Proposed station on the {selected_line} line."
    proposed.style.iconstyle.color = simplekml.Color.green
    proposed.style.iconstyle.scale = 1.2

    catchment_polygon = catchment_gdf.geometry.iloc[0]

    polygon = kml.newpolygon(
        name=f"{radius_m}m Walking Catchment",
        outerboundaryis=[
            (lon, lat)
            for lon, lat in catchment_polygon.exterior.coords
        ],
    )
    polygon.description = (
        f"Approximate {radius_m}m walking catchment around the proposed station."
    )
    polygon.style.polystyle.color = simplekml.Color.changealphaint(
        80,
        simplekml.Color.green,
    )
    polygon.style.linestyle.color = simplekml.Color.green
    polygon.style.linestyle.width = 3

    for _, row in affected_stations.iterrows():
        point = kml.newpoint(
            name=row["Name"],
            coords=[(row["Longitude"], row["Latitude"])],
        )
        point.description = (
            f"Existing stop within catchment. "
            f"Line: {row.get('Line_id', 'Unknown')}"
        )
        point.style.iconstyle.color = simplekml.Color.red
        point.style.iconstyle.scale = 0.9

    return kml.kml().encode("utf-8")


def generate_kmz_bytes(
    proposed_lat: float,
    proposed_lon: float,
    selected_line: str,
    bucket_name: str = "c23-travel-simulation-bucket",
    stations_key: str = "processed/stations.csv",
    radius_m: int = 800,
) -> bytes:
    """Generate a KMZ file containing the KML."""

    kml_bytes = generate_kml_bytes(
        proposed_lat=proposed_lat,
        proposed_lon=proposed_lon,
        selected_line=selected_line,
        bucket_name=bucket_name,
        stations_key=stations_key,
        radius_m=radius_m,
    )

    buffer = BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as kmz:
        kmz.writestr("doc.kml", kml_bytes)

    buffer.seek(0)
    return buffer.read()
