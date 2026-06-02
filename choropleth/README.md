# Choropleth Map Generation

This module creates interactive choropleth maps of London showing tube station density by administrative boundary.

## File Structure

### Core Modules

- **`endmap.py`**: Main orchestration module with two pipelines
  - `choropleth_creation()`: Local pipeline using cached boundary and station data
  - `choropleth_creation_cloud()`: Cloud pipeline using S3-stored data (default)

- **`data_functions.py`**: Data loading and processing utilities
  - Boundary data loading (local cache or GeoJSON → pickle)
  - Station data fetching (TFL API, CSV cache, S3 integration)
  - S3 operations (upload/download boundary, station, and choropleth data)
  - GeoDataFrame helpers

### Data Files

- **`boundaryData.geojson`**: London administrative boundaries (ONS data)
- **`boundaryData.pkl`**: Cached pickle version (auto-generated from GeoJSON)
- **`stations.csv`**: Cached normalized tube stop coordinates
- **`normalised_stops.csv`**: Alternative stations cache file

### Output Files

- **`choropleth_local.html`**: Map using local data
- **`choropleth_cloud.html`**: Map using S3 data (default output)
- **`combined_map.html`**: Multi-map combination (future)

## Configuration

### AWS S3 Credentials

The cloud pipeline requires AWS S3 access. Configure credentials via one of:

1. **Environment variables** (recommended):
   ```bash
   export AWS_ACCESS_KEY_ID=your_key
   export AWS_SECRET_ACCESS_KEY=your_secret
   export AWS_DEFAULT_REGION=us-east-1
   ```

2. **AWS credentials file** (`~/.aws/credentials`):
   ```
   [default]
   aws_access_key_id = your_key
   aws_secret_access_key = your_secret
   ```

3. **IAM role** (if running on EC2/Lambda)

### S3 Bucket Structure

```
s3://c23-travel-simulation-bucket/
├── processed/
│   ├── boundaryData.pkl
│   └── stations.csv
└── outputs/
    └── choropleth.geojson
```

## Usage

### Quick Start

```bash
python endmap.py
```

Generates `choropleth_cloud.html` using data from S3 (with API fallback for stations).

### Local Pipeline

```python
from endmap import choropleth_creation, STOPS_URL

choropleth_creation(STOPS_URL)  # Generates choropleth_local.html
```

### Custom Cloud Pipeline

```python
from endmap import choropleth_creation_cloud, STOPS_URL

choropleth_creation_cloud(
    STOPS_URL,
    boundary_s3_path="processed/boundaryData.pkl",
    station_s3_path="processed/stations.csv",
    choropleth_s3_path="outputs/choropleth.geojson"
)
```

## Dependencies

See `requirements.txt` for full list. Key packages:
- `geopandas`: Spatial data operations
- `folium`: Interactive map visualization
- `boto3`: AWS S3 integration
- `pandas`: Data processing
- `requests`: API calls

## Pipeline Overview

1. **Load boundaries**: From local cache or S3 (filtered to London E09 areas)
2. **Load stations**: From CSV cache or S3 (fetches from TFL API if unavailable)
3. **Spatial join**: Count stations within each boundary zone
4. **Save result**: GeoDataFrame persisted to S3 as GeoJSON
5. **Visualize**: Create Folium choropleth map (colored by station count)
6. **Export**: Save interactive HTML map

## Notes

- TFL API endpoint used is deprecated; consider updating to current version
- Station coordinates are averaged by `commonName` (handles duplicate stop IDs)
- All geometries use EPSG:4326 (WGS84) CRS
- Column names standardized: `Longitude`, `Latitude`, `station_count`
