# Choropleth Map Generation

Creates an interactive choropleth map of London showing tube station density by borough.

## Quick Start

Navigate to the choropleth directory to begin.

1. Download boundary data:
```bash
bash download_boundaries.sh
```

2. Run the pipeline:
```bash
python choropleth_pipeline.py
```

Output: GeoJSON saved to S3 at `s3://c23-travel-simulation-bucket/outputs/choropleth.geojson`


## What This Does

- Downloads London borough boundaries from ArcGIS Hub
- Loads tube station data from S3
- Counts stations per borough via spatial join
- Saves result as GeoJSON to S3 for use in dashboards

## Requirements

- AWS S3 access (configured via `~/.aws/credentials` or environment variables)
- Tube station data must be in S3 at `processed/stations.csv`
- S3 bucket path is hardcoded in `choropleth_pipeline.py` (update if needed)
- Python dependencies: see `requirements.txt`

## File Structure

- **`download_boundaries.sh`**: Bash script to download boundary data (run first)
- **`choropleth_pipeline.py`**: Main Python pipeline (run after bash script)
- **`requirements.txt`**: Python dependencies
- **`Dockerfile`**: Container configuration for cloud deployment
- **`boundaryData.geojson`**: Downloaded boundary data (created by bash script)
