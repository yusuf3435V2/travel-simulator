"""Pytest configuration - setup path for importing modules."""

import os
import sys

# Add parent directory to path to import modules from tfl_data_and_network
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
