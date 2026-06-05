"""Tests for dashboard/Run_Simulations.py - verifying refactored function structure."""

from pathlib import Path

DASHBOARD_FILE = Path(__file__).resolve().parents[1] / "Run_Simulations.py"


def read_dashboard_code() -> str:
    """Read Run_Simulations.py as text."""
    return DASHBOARD_FILE.read_text(encoding="utf-8")


def test_dashboard_file_exists():
    """Test that Run_Simulations.py file exists."""
    assert DASHBOARD_FILE.exists()


def test_dashboard_has_required_imports():
    """Test that dashboard imports required libraries."""
    code = read_dashboard_code()

    assert "import streamlit as st" in code
    assert "from analysis import generate_recommendation_pdf" in code
    assert "from kml_export import generate_kmz_bytes" in code
    assert "import boto3" in code


def test_dashboard_has_all_render_functions():
    """Test that all render functions are defined."""
    code = read_dashboard_code()

    render_functions = [
        "def render_sidebar(",
        "def render_location_selector_map(",
        "def render_results(",
        "def render_visualization_charts(",
        "def render_affected_routes_summary(",
        "def render_demand_impact_ranges(",
    ]

    for func in render_functions:
        assert func in code, f"Missing function: {func}"


def test_dashboard_has_main_orchestration_functions():
    """Test that main orchestration functions exist."""
    code = read_dashboard_code()

    assert "def initialize_session_state()" in code
    assert "def dashboard()" in code
    assert "def execute_simulation(" in code


def test_dashboard_has_entry_point():
    """Test that dashboard has proper entry point."""
    code = read_dashboard_code()

    assert 'if __name__ == "__main__":' in code
    assert "dashboard()" in code


def test_dashboard_initializes_session_state_keys():
    """Test that required session state keys are initialized."""
    code = read_dashboard_code()

    required_keys = [
        "proposed_lat",
        "proposed_lon",
        "selected_line",
        "simulation_running",
        "simulation_finished",
    ]

    for key in required_keys:
        assert f'"{key}" not in st.session_state' in code
