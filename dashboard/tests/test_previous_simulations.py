"""Tests for pages/2_previous_simulations.py - verifying refactored function structure."""

from pathlib import Path

PREVIOUS_SIM_FILE = Path(__file__).resolve().parents[1] / "pages" / "2_previous_simulations.py"


def read_previous_sim_code() -> str:
    """Read 2_previous_simulations.py as text."""
    return PREVIOUS_SIM_FILE.read_text(encoding="utf-8")


def test_previous_simulations_file_exists():
    """Test that 2_previous_simulations.py file exists."""
    assert PREVIOUS_SIM_FILE.exists()


def test_previous_simulations_has_required_imports():
    """Test that required libraries are imported."""
    code = read_previous_sim_code()

    assert "import streamlit as st" in code
    assert "from s3_utils import" in code
    assert "from df_analysis import" in code


def test_previous_simulations_imports_render_functions():
    """Test that reusable render functions are imported from Run_Simulations."""
    code = read_previous_sim_code()

    assert "from Run_Simulations import" in code
    assert "render_visualization_charts" in code
    assert "render_affected_routes_summary" in code
    assert "render_demand_impact_ranges" in code


def test_previous_simulations_has_core_functions():
    """Test that core page functions exist."""
    code = read_previous_sim_code()

    core_functions = [
        "def fetch_simulation_folders(",
        "def render_folder_selector(",
        "def load_simulation_metadata(",
        "def render_metadata_display(",
        "def load_comparison_data(",
        "def render_impact_map(",
        "def render_impact_metrics(",
        "def render_simulation_results(",
    ]

    for func in core_functions:
        assert func in code, f"Missing function: {func}"


def test_previous_simulations_has_main_page_function():
    """Test that main page function exists."""
    code = read_previous_sim_code()

    assert "def previous_simulations_page()" in code


def test_previous_simulations_has_entry_point():
    """Test that page has proper entry point."""
    code = read_previous_sim_code()

    assert 'if __name__ == "__main__":' in code
    assert "previous_simulations_page()" in code


def test_previous_simulations_uses_s3_config():
    """Test that S3 configuration is defined."""
    code = read_previous_sim_code()

    assert "BUCKET_NAME = os.getenv(\"S3_BUCKET_NAME\")" in code
    assert "BASE_PREFIX = \"raw/\"" in code


def test_previous_simulations_loads_data_from_s3():
    """Test that S3 data loading functions are called."""
    code = read_previous_sim_code()

    s3_functions = [
        "get_simulation_folders(",
        "get_folder_metadata(",
        "get_comparison_csv(",
    ]

    for func in s3_functions:
        assert func in code
