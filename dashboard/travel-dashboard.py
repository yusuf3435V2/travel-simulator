"""Streamlit entrypoint.

Delegates to dashboard.py so `streamlit run travel-dashboard.py` launches the
actual travel simulation dashboard.
"""

from pathlib import Path
from runpy import run_path

run_path(str(Path(__file__).with_name("dashboard.py")), run_name="__main__")
    - Explore a [New York City rideshare dataset](https://github.com/streamlit/demo-uber-nyc-pickups)
"""
)
