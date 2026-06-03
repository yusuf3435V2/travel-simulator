# Choropleth Map Generation

This module creates interactive choropleth maps of London showing tube station density by administrative boundary.


## Usage

### Prerequisites:

If working with an empty S3 bucket, follow these steps:
1. Download GeoJson data from:
    - https://geoportal.statistics.gov.uk/datasets/a5c9ff451d9a4ba08d9680b3869c9d8f_0/explore?location=51.495104%2C-0.108864%2C10
    in order to get initial boundary data. Save as boundaryData.geojson locally.
2. Run the data_functions.py file to make use of the boundaryData.geojson and upload it to the cloud.
3. Ensure the S3 bucket contains stations.csv from the tfl_data_and_network folder ETL.

Those are the two data files required to allow the entire endmap.py script pipeline to work.

### Quick Start

```bash
python endmap.py
```

Generates `choropleth_cloud.html` using data from S3 (with API fallback for stations).


## File Structure

### Core Modules

- **`endmap.py`**: Main orchestration module with two pipelines
  - `choropleth_creation()`: Local pipeline using cached boundary and station data
  - `choropleth_creation_cloud()`: Cloud pipeline using S3-stored data (default)

- **`data_functions.py`**: Data loading and processing utilities
  - Boundary data loading (local cache or GeoJSON → pickle)
  - Station data fetching (Mainly through S3, there is an API however it is outdated)
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

### S3 Bucket Structure

```
s3://c23-travel-simulation-bucket/
├── processed/
│   ├── boundaryData.pkl
│   ├── boundaryClean.pkl
│   └── stations.csv
└── outputs/
    └── choropleth.geojson
```

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

## Notes

- Boundary data is required to be downloaded from the ONS website first.
- Stations csv are loaded primarily from the S3. API gives different data.
- TFL API endpoint used is deprecated; consider updating to current version
- Station coordinates are averaged by `commonName` (handles duplicate stop IDs)
- All geometries use EPSG:4326 (WGS84) CRS
- Column names standardized: `Longitude`, `Latitude`, `station_count`
