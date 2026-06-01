"""Simple tests for dashboard/dashboard.py without running Streamlit UI."""

from pathlib import Path
DASHBOARD_FILE = Path(__file__).resolve().parents[1] / "dashboard.py"


def read_dashboard_code() -> str:
    """Read dashboard.py as text."""
    return DASHBOARD_FILE.read_text(encoding="utf-8")


def test_dashboard_file_exists():
    assert DASHBOARD_FILE.exists()


def test_dashboard_imports_report_and_kmz_generators():
    code = read_dashboard_code()

    assert "from analysis import generate_recommendation_pdf" in code
    assert "from kml_export import generate_kmz_bytes" in code


def test_dashboard_initialises_required_session_state_keys():
    code = read_dashboard_code()

    required_keys = [
        "proposed_lat",
        "proposed_lon",
        "selected_line",
        "simulation_running",
        "simulation_finished",
        "pdf_bytes",
        "kmz_bytes",
    ]

    for key in required_keys:
        assert f'"{key}" not in st.session_state' in code


def test_dashboard_clears_pdf_and_kmz_when_location_changes():
    code = read_dashboard_code()

    assert "st.session_state.pdf_bytes = None" in code
    assert "st.session_state.kmz_bytes = None" in code


def test_dashboard_generates_pdf_and_kmz_after_simulation():
    code = read_dashboard_code()

    assert "generate_recommendation_pdf(" in code
    assert "generate_kmz_bytes(" in code


def test_dashboard_has_download_buttons_for_pdf_and_kmz():
    code = read_dashboard_code()

    assert 'label="Download recommendation report"' in code
    assert 'file_name="travel_simulation_recommendation.pdf"' in code
    assert 'mime="application/pdf"' in code

    assert 'label="Download Google Earth KMZ"' in code
    assert 'file_name="travel_simulation_google_earth.kmz"' in code
    assert 'mime="application/vnd.google-earth.kmz"' in code


def test_dashboard_reruns_after_map_click():
    code = read_dashboard_code()

    assert "st.rerun()" in code
