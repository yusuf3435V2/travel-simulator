"""Analysis and report generation for the Travel Simulation dashboard."""
from io import BytesIO
import ee
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
import os
from dotenv import load_dotenv
from openai import OpenAI
from coverage_context import get_coverage_context_from_s3

def get_google_cloud_project() -> str:
    """Load Google Cloud project ID from environment."""

    load_dotenv()

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")

    if not project_id:
        raise ValueError(
            "GOOGLE_CLOUD_PROJECT not found in .env"
        )

    return project_id

def initialise_earth_engine() -> None:
    """Initialise Google Earth Engine."""

    project_id = get_google_cloud_project()

    try:
        ee.Initialize(project=project_id)

    except Exception:
        ee.Authenticate()
        ee.Initialize(project=project_id)


def get_land_use_percentages(
    lat: float,
    lon: float,
    radius_m: int = 400,
) -> pd.DataFrame:
    """Calculate land-use percentages inside the catchment."""

    initialise_earth_engine()

    catchment = ee.Geometry.Point([lon, lat]).buffer(radius_m)

    landcover = (
        ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
        .filterBounds(catchment)
        .filterDate("2024-01-01", "2025-12-31")
        .select("label")
        .mode()
    )

    area_image = ee.Image.pixelArea().addBands(landcover)

    stats = area_image.reduceRegion(
        reducer=ee.Reducer.sum().group(
            groupField=1,
            groupName="land_use_class",
        ),
        geometry=catchment,
        scale=10,
        maxPixels=1e9,
    )

    groups = stats.get("groups").getInfo()

    class_names = {
        0: "Water",
        1: "Trees",
        2: "Grass",
        3: "Flooded vegetation",
        4: "Crops",
        5: "Shrub and scrub",
        6: "Built-up",
        7: "Bare ground",
        8: "Snow and ice",
    }

    rows = []

    for group in groups:
        class_id = int(group["land_use_class"])
        area_sqm = group["sum"]

        rows.append({
            "land_use": class_names.get(class_id, "Unknown"),
            "area_sqm": area_sqm,
        })

    land_use_df = pd.DataFrame(rows)

    land_use_df["percentage"] = (
        land_use_df["area_sqm"] / land_use_df["area_sqm"].sum() * 100
    ).round(2)

    return land_use_df.sort_values("percentage", ascending=False)


def explain_coverage(coverage_context: dict) -> str:
    """Create coverage explanation text."""

    station_count = coverage_context["stations_within_catchment"]
    nearest_station = coverage_context["nearest_station_name"]
    nearest_distance = coverage_context["nearest_station_distance_m"]
    coverage_level = coverage_context["coverage_level"]
    affected_lines = coverage_context.get("affected_lines", [])

    affected_lines_text = ", ".join(
        affected_lines) if affected_lines else "no nearby lines"

    if coverage_level == "High":
        return (
            f"The proposed location already has strong rail coverage. There are "
            f"{station_count} existing stations within the catchment, and the nearest "
            f"station is {nearest_station}, approximately {nearest_distance}m away. "
            f"The nearby network includes {affected_lines_text}. This suggests that a "
            f"new station would need to be justified by demand, interchange benefits "
            f"or capacity relief rather than a simple coverage gap."
        )

    if coverage_level == "Medium":
        return (
            f"The proposed location has moderate rail coverage. There are "
            f"{station_count} existing stations within the catchment, and the nearest "
            f"station is {nearest_station}, approximately {nearest_distance}m away. "
            f"The nearby network includes {affected_lines_text}. A new station may improve "
            f"accessibility, but the case depends on whether it serves demand not already "
            f"captured by nearby stations."
        )

    return (
        f"The proposed location appears to have weak rail coverage. There are only "
        f"{station_count} existing stations within the catchment, and the nearest station "
        f"is {nearest_station}, approximately {nearest_distance}m away. This suggests "
        f"the proposal may address an accessibility gap, especially if land-use patterns "
        f"indicate nearby residential, commercial or employment activity."
    )


def explain_land_use(land_use_df: pd.DataFrame) -> str:
    """Create land-use explanation text."""

    built_up = land_use_df.loc[
        land_use_df["land_use"] == "Built-up",
        "percentage",
    ].sum()

    green = land_use_df.loc[
        land_use_df["land_use"].isin(["Trees", "Grass", "Shrub and scrub"]),
        "percentage",
    ].sum()

    water = land_use_df.loc[
        land_use_df["land_use"] == "Water",
        "percentage",
    ].sum()

    if built_up >= 60:
        return (
            f"The catchment is highly built-up, with {built_up:.1f}% classified as "
            f"built-up land. This suggests the area may contain dense residential, "
            f"commercial or employment activity, which can support stronger potential "
            f"transport demand."
        )

    if green >= 50:
        return (
            f"The catchment is dominated by green/open land, with {green:.1f}% made up "
            f"of trees, grass or shrubland. This may explain weaker coverage or lower "
            f"station priority, unless the area includes major parks, attractions, housing "
            f"edges or employment sites."
        )

    if water >= 30:
        return (
            f"Water covers {water:.1f}% of the catchment. This reduces the practical "
            f"walkable area and may partly explain why rail coverage appears weaker."
        )

    top_row = land_use_df.iloc[0]

    return (
        f"The catchment has a mixed land-use profile. The largest category is "
        f"{top_row['land_use']} at {top_row['percentage']:.1f}%. This means the "
        f"coverage judgement should be interpreted alongside passenger demand and "
        f"nearby station accessibility."
    )



def build_recommendation_text(
    proposed_lat: float,
    proposed_lon: float,
    selected_line: str,
    coverage_context: dict,
    coverage_explanation: str,
    land_use_df: pd.DataFrame,
    land_use_explanation: str,
) -> str:
    """Build the final report text."""

    land_use_lines = "\n".join(
        f"- {row['land_use']}: {row['percentage']}%"
        for _, row in land_use_df.iterrows()
    )

    coverage_level = coverage_context["coverage_level"]

    if coverage_level == "High":
        recommendation = (
            "The proposed station should not currently be recommended purely on "
            "coverage-gap grounds, because the area already appears well served. "
            "Further justification would need to come from passenger demand, capacity "
            "relief, interchange benefits or strategic network improvements."
        )
    elif coverage_level == "Medium":
        recommendation = (
            "The proposed station may be worth further investigation. Current coverage "
            "is moderate, so the strongest case would depend on whether the proposal "
            "serves demand not already captured by existing nearby stations."
        )
    else:
        recommendation = (
            "The proposed station should be prioritised for further feasibility analysis. "
            "The area appears to have weak existing coverage, and if demand analysis supports "
            "this, the proposal may address a meaningful accessibility gap."
        )

    return f"""
    Travel Simulation Recommendation

    Proposed location:
    Latitude: {proposed_lat}
    Longitude: {proposed_lon}
    Selected line: {selected_line}

    Coverage context:
    {coverage_explanation}

    Land-use breakdown:
    {land_use_lines}

    Land-use context:
    {land_use_explanation}

    Recommendation:
    {recommendation}

    Assumptions and limitations:
    - Coverage level is currently based on the number of existing stations within a 800m catchment.
    - Land-use data is based on broad satellite classification from Google Earth Engine Dynamic World.
    - Built-up land does not distinguish perfectly between residential, commercial and industrial use.
    - This report should be updated once simulation demand impact results are available.
    """


def rewrite_report_with_openai(report_context: str) -> str:
    """Rewrite the calculated report context into a client-ready report."""

    load_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY not found in .env")

    client = OpenAI()

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=f"""
        You are a transport consultant writing a one-page recommendation for a non-technical local authority client.

        Rewrite the report using ONLY the context below.
        Do not invent numbers.
        Do not invent station names.
        Do not invent routes.
        Keep the structure:
        - Context
        - Key findings
        - Recommendation
        - Assumptions and limitations

        Use clear, professional language.

        CONTEXT:
        {report_context}
        """
    )

    return response.output_text


def create_pdf_report(report_text: str) -> bytes:
    """Create a PDF report with wrapped text and proper headings."""

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50,
    )

    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]
    heading_style = styles["Heading2"]
    title_style = styles["Title"]

    story = []

    for line in report_text.split("\n"):
        line = line.strip()

        if not line:
            story.append(Spacer(1, 10))
            continue

        # Main title
        if line == "Travel Simulation Recommendation":
            story.append(Paragraph(line, title_style))
            story.append(Spacer(1, 12))
            continue

        # Handle OpenAI markdown headings like **Context**
        if line.startswith("**") and line.endswith("**"):
            clean_heading = line.replace("**", "")
            story.append(Paragraph(clean_heading, heading_style))
            story.append(Spacer(1, 8))
            continue

        # Handle plain headings like Context:
        if line.endswith(":"):
            story.append(Paragraph(line, heading_style))
            story.append(Spacer(1, 8))
            continue

        story.append(Paragraph(line, normal_style))
        story.append(Spacer(1, 6))

    doc.build(story)

    buffer.seek(0)
    return buffer.read()


def generate_recommendation_pdf(
    proposed_lat: float,
    proposed_lon: float,
    selected_line: str,
    bucket_name: str = "c23-travel-simulation-bucket",
    stations_key: str = "processed/stations.csv",
    radius_m: int = 800,
) -> bytes:
    coverage_context = get_coverage_context_from_s3(
        proposed_lat=proposed_lat,
        proposed_lon=proposed_lon,
        bucket_name=bucket_name,
        stations_key=stations_key,
        radius_m=radius_m,
    )

    coverage_explanation = explain_coverage(coverage_context)

    land_use_df = get_land_use_percentages(
        lat=proposed_lat,
        lon=proposed_lon,
        radius_m=radius_m,
    )

    land_use_explanation = explain_land_use(land_use_df)

    report_text = build_recommendation_text(
        proposed_lat=proposed_lat,
        proposed_lon=proposed_lon,
        selected_line=selected_line,
        coverage_context=coverage_context,
        coverage_explanation=coverage_explanation,
        land_use_df=land_use_df,
        land_use_explanation=land_use_explanation,
    )

    ai_report_text = rewrite_report_with_openai(report_text)

    return create_pdf_report(ai_report_text)



