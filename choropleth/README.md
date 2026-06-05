# Choropleth Map Generation

Generates interactive choropleth maps of London showing tube station density by borough. Downloads borough boundaries, performs spatial analysis, and outputs GeoJSON for dashboard visualization.

**Primary deployment**: AWS Lambda with ECR (see [infrastructure README](../infrastructure/README.md))

**Local usage**: Direct Python execution for development

## Quick Start

### Lambda Deployment

See the [infrastructure README](../infrastructure/README.md#choropleth-pipeline-lambda) for deployment steps.

**Lambda invocation** (no parameters required):
```bash
aws lambda invoke --function-name c23-travel-simulator-choropleth-pipeline response.json
aws logs tail /aws/lambda/c23-travel-simulator-choropleth-pipeline --follow
```

**What it produces** (saved to S3):
- `outputs/choropleth.geojson` - GeoJSON with borough boundaries and station density counts

### Local Usage

Run the pipeline locally:
```bash
bash download_boundaries.sh  # Download borough boundaries once
python choropleth_pipeline.py
```

## Core Functionality

- **Boundary Data**: Downloads London borough boundaries from ArcGIS Hub
- **Spatial Analysis**: Loads tube station data from S3, counts stations per borough via spatial join
- **Output**: Saves GeoJSON with borough features and station density metrics to S3
- **Dependencies**: Requires `processed/stations.csv` in S3 (created by TFL data pipeline)

## Module Overview

**choropleth_pipeline.py**
Main orchestration script. Downloads boundary data, loads stations from S3, performs spatial join, and uploads GeoJSON to S3. Contains Lambda handler: `lambda_handler()`.

**download_boundaries.sh**
Bash script to download London borough boundaries from ArcGIS Hub. Run once to create local `boundaryData.geojson`.

## Configuration

- **S3 bucket**: Hardcoded as `c23-travel-simulation-bucket` in `choropleth_pipeline.py`
- **AWS credentials**: Configured via `~/.aws/credentials` or environment variables
- **Python dependencies**: See `requirements.txt`
