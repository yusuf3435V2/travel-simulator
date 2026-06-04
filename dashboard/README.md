# Dashboard

Interactive Streamlit application for visualizing simulation results, analyzing passenger flows, and evaluating the impact of proposed transit network changes.

**Primary deployment**: AWS ECS Fargate running Streamlit (see [infrastructure README](../infrastructure/README.md#dashboard-ecs-deployment))

**Local usage**: Direct Python execution for development

## Quick Start

### ECS Deployment

See the [infrastructure README](../infrastructure/README.md#dashboard-ecs-deployment) for deployment steps.

**Access dashboard**: Find the ECS service's public IP in the AWS console and navigate to `http://<public-ip>:8501`

### Local Execution

From the repository root:
```bash
streamlit run dashboard/dashboard.py
```

Access at `http://localhost:8501`

### Docker Execution

Build and run locally:
```bash
docker build -f dashboard/Dockerfile -t travel-simulator-dashboard .
docker run -p 8501:8501 --env-file .env travel-simulator-dashboard
```

## Core Functionality

- **Visualization**: Multi-page interface displaying simulation results and network impact analysis
- **User Input**: Accepts proposed station coordinates and metadata
- **Simulation Selection**: Compares baseline vs. altered network scenarios
- **Analysis**: Integrates Google Earth Engine for environmental context and OpenAI for report generation
- **Export**: KML export for external GIS tools, PDF report generation
- **Historical View**: Separate page for reviewing previous simulation runs

## Module Overview

**dashboard.py**
Main entry point and orchestrator for the multi-page interface. Handles user input for proposed stations, simulation selection, and layout orchestration.

**analysis.py**
Advanced analysis and report generation. Google Earth Engine integration, OpenAI-powered insights, and PDF report generation via ReportLab.

**coverage_context.py**
Station coverage and accessibility analysis using 800m walking radius. Performs spatial analysis with GeoPandas to identify catchment areas and generate coverage statistics.

**df_analysis.py**
DataFrame utilities for comparing baseline and altered simulations. Handles passenger impact analysis, journey time statistics, and color-coding logic for visualization.

**folium_functions.py**
Interactive map visualization using Folium. Creates station markers, 800m catchment circles, and network visualization with click-enabled popups.

**kml_export.py**
KML file generation for external GIS applications. Exports proposed stations, affected stations, and coverage areas with custom styling for Google Earth and ArcGIS.

**s3_utils.py**
AWS S3 integration for loading simulation results, station data, and simulation metadata from cloud storage with caching and error handling.

**stations_choropleth.py**
Choropleth map generation. Loads pre-generated choropleth GeoJSON from S3 and overlays station markers color-coded by impact metrics.

**pages/2_previous_simulations.py**
Historical analysis page. Lists previous simulation runs, enables comparison across proposed stations, and archives past analysis results.

## Metrics Calculation

See [METRICS.md](METRICS.md) for detailed metrics calculations including journey time, coverage, passenger impact, and demand analysis.

## Development & Testing

Run tests to validate functionality before deployment:

```bash
pytest dashboard/tests/ -v
```

Tests cover:
- DataFrame analysis and comparison logic
- S3 utilities and data loading
- Map visualization and KML export
- Coverage context calculations

## Configuration

Environment variables (set in `.env` or container):
- `AWS_REGION`: AWS region for S3 access
- `S3_BUCKET_NAME`: S3 bucket containing simulation results
- `GOOGLE_CLOUD_PROJECT`: Google Cloud project ID for Earth Engine
- `GOOGLE_APPLICATION_CREDENTIALS_JSON`: Service account JSON (if using Earth Engine)
- `OPENAI_API_KEY`: OpenAI API key for analysis features (optional)

AWS S3 access on ECS is provided via task role (no explicit AWS_ACCESS_KEY_ID/SECRET needed).

## Troubleshooting

**Map not displaying**
- Verify Folium installation: `pip install folium`
- Check internet connection for tile loading
- Ensure coordinates are valid (latitude: -90 to 90, longitude: -180 to 180)

**S3 connection errors**
- Verify AWS credentials: `aws configure`
- Check S3 bucket name and permissions
- Ensure bucket contains expected CSV files at correct paths

**Analysis features not working**
- Verify Google Cloud credentials for Earth Engine
- Check OpenAI API key for report generation
- Ensure all environment variables are set
