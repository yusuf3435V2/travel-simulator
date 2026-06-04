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
python choropleth_pipline.py
```

Output: `outputs/choropleth.geojson` saved to S3

## What This Does

- Downloads London borough boundaries from ArcGIS Hub
- Loads tube station data from S3
- Counts stations per borough via spatial join
- Saves result as GeoJSON to S3 for use in dashboards

## Requirements

- AWS S3 access (configured via `~/.aws/credentials` or environment variables)
- Tube station data must be in S3 at `processed/stations.csv`

## Files

- **`download_boundaries.sh`**: Downloads boundary data - run this first
- **`choropleth_pipeline.py`**: Main pipeline - then run this
