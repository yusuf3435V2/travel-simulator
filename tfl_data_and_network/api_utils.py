"""Utility functions for API calls with retry logic and rate limit handling."""

import requests
import logging
import time
from typing import Any


def setup_logger(log_level: str = "INFO") -> None:
    """Configure logging with the specified log_level: (DEBUG, INFO, WARNING, ERROR, CRITICAL)"""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(levelname)s - %(message)s',
        encoding="utf-8"
    )


def make_api_call_with_retry(url: str, max_retries: int = 7) -> dict | list | Any:
    """Make an API call with exponential backoff retry logic for rate limits."""
    logging.debug(f"Starting API call to: {url}")
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:  # Rate limited
                wait_time = min(2 ** attempt, 64)
                logging.warning(
                    f"Rate limited (429). Waiting {wait_time} seconds before retry "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(wait_time)
            else:
                logging.error(
                    f"API request failed with status code: {response.status_code}")
                return {}
        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed: {e}")
            if attempt < max_retries - 1:
                wait_time = min(2 ** attempt, 64)
                logging.warning(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                return {}

    logging.error(f"Failed to complete API call after {max_retries} attempts")
    return {}
