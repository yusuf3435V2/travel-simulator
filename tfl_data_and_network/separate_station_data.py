"""Script to separate station data into individual files for each station, saved into a directory called 'stations'."""

import os
import requests
import pandas as pd

BASE_URL = "https://api.tfl.gov.uk/StopPoint/Mode/tube"


def download_and_extract_station_data() -> dict:
    """Download the station data zip file and extract it into the 'stations' directory."""
    response = requests.get(BASE_URL)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to fetch station data: {response.status_code}")


def get_relevant_station_data(station_data: dict) -> list[dict]:
    """Extract relevant station data from the full dataset."""
    relevant_data = []
    for station in station_data["stopPoints"]:
        print(station.keys())
        if "stationNaptan" not in station:
            continue
        relevant_data.append(
            {
                "UniqueId": station["stationNaptan"],
                "Name": station["commonName"],
                "Latitude": station["lat"],
                "Longitude": station["lon"],
            }
        )
    return relevant_data


if __name__ == "__main__":
    station_data = get_relevant_station_data(download_and_extract_station_data())
    os.makedirs("stations", exist_ok=True)
    station_df = pd.DataFrame(station_data)
    station_df.to_csv("stations/Stations.csv", index=False)
