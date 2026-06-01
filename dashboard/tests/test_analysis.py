"""Tests for pure functions in dashboard/analysis.py."""

import sys
from pathlib import Path
import pandas as pd
import pytest

DASHBOARD_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DASHBOARD_DIR))

from analysis import (  # noqa: E402
    build_recommendation_text,
    create_pdf_report,
    explain_coverage,
    explain_land_use,
)


@pytest.mark.parametrize(
    "coverage_level, expected_phrase",
    [
        ("High", "already has strong rail coverage"),
        ("Medium", "has moderate rail coverage"),
        ("Low", "appears to have weak rail coverage"),
    ],
)
def test_explain_coverage_for_different_levels(coverage_level, expected_phrase):
    coverage_context = {
        "stations_within_catchment": 2,
        "nearest_station_name": "Test Station",
        "nearest_station_distance_m": 350.5,
        "affected_lines": ["central", "district"],
        "coverage_level": coverage_level,
    }

    result = explain_coverage(coverage_context)

    assert expected_phrase in result
    assert "Test Station" in result
    assert "350.5m" in result


def test_explain_coverage_handles_no_affected_lines():
    coverage_context = {
        "stations_within_catchment": 0,
        "nearest_station_name": "Nearest Test Station",
        "nearest_station_distance_m": 1200,
        "affected_lines": [],
        "coverage_level": "Low",
    }

    result = explain_coverage(coverage_context)

    assert "weak rail coverage" in result
    assert "Nearest Test Station" in result
    assert "1200m" in result


@pytest.mark.parametrize(
    "land_use_data, expected_phrase",
    [
        (
            [
                {"land_use": "Built-up", "percentage": 70.0},
                {"land_use": "Trees", "percentage": 20.0},
                {"land_use": "Water", "percentage": 10.0},
            ],
            "highly built-up",
        ),
        (
            [
                {"land_use": "Trees", "percentage": 30.0},
                {"land_use": "Grass", "percentage": 25.0},
                {"land_use": "Shrub and scrub", "percentage": 10.0},
                {"land_use": "Built-up", "percentage": 35.0},
            ],
            "dominated by green/open land",
        ),
        (
            [
                {"land_use": "Water", "percentage": 35.0},
                {"land_use": "Built-up", "percentage": 30.0},
                {"land_use": "Grass", "percentage": 35.0},
            ],
            "Water covers",
        ),
        (
            [
                {"land_use": "Grass", "percentage": 40.0},
                {"land_use": "Built-up", "percentage": 35.0},
                {"land_use": "Water", "percentage": 25.0},
            ],
            "mixed land-use profile",
        ),
    ],
)
def test_explain_land_use_categories(land_use_data, expected_phrase):
    land_use_df = pd.DataFrame(land_use_data)

    result = explain_land_use(land_use_df)

    assert expected_phrase in result


def test_build_recommendation_text_contains_core_sections():
    land_use_df = pd.DataFrame(
        [
            {"land_use": "Built-up", "percentage": 77.7},
            {"land_use": "Water", "percentage": 13.7},
        ]
    )

    result = build_recommendation_text(
        proposed_lat=51.5074,
        proposed_lon=-0.1278,
        selected_line="Bakerloo",
        coverage_context={"coverage_level": "High"},
        coverage_explanation="Coverage explanation here.",
        land_use_df=land_use_df,
        land_use_explanation="Land-use explanation here.",
    )

    assert "Travel Simulation Recommendation" in result
    assert "Latitude: 51.5074" in result
    assert "Longitude: -0.1278" in result
    assert "Selected line: Bakerloo" in result
    assert "- Built-up: 77.7%" in result
    assert "Coverage explanation here." in result
    assert "Land-use explanation here." in result


@pytest.mark.parametrize(
    "coverage_level, expected_recommendation",
    [
        ("High", "should not currently be recommended purely on coverage-gap grounds"),
        ("Medium", "may be worth further investigation"),
        ("Low", "should be prioritised for further feasibility analysis"),
    ],
)
def test_build_recommendation_text_changes_by_coverage_level(
    coverage_level,
    expected_recommendation,
):
    land_use_df = pd.DataFrame(
        [{"land_use": "Built-up", "percentage": 60.0}]
    )

    result = build_recommendation_text(
        proposed_lat=51.5,
        proposed_lon=-0.1,
        selected_line="Central",
        coverage_context={"coverage_level": coverage_level},
        coverage_explanation="Coverage text.",
        land_use_df=land_use_df,
        land_use_explanation="Land-use text.",
    )

    assert expected_recommendation in result


def test_create_pdf_report_returns_pdf_bytes():
    report_text = """
Travel Simulation Recommendation

Context:
This is a test report.

Recommendation:
This should generate a PDF.
"""

    pdf_bytes = create_pdf_report(report_text)

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 100
