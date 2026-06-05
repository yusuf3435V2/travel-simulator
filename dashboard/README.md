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
streamlit run dashboard/Run_Simulations.py
```

Or from the dashboard directory:
```bash
cd dashboard
streamlit run Run_Simulations.py
```

The dashboard will be available at `http://localhost:8501`

### Docker Execution

Build and run locally:
```bash
docker build -f dashboard/Dockerfile -t travel-simulator-dashboard .
docker run -p 8501:8501 --env-file .env travel-simulator-dashboard
```

### Command-Line Options

Common Streamlit options:
```bash
# Run on specific port
streamlit run dashboard/Run_Simulations.py --server.port 8000

## Dashboard Structure

### **Run_Simulations.py** (Main Entry Point)
The primary dashboard application and entry point. Provides:
- Borough-based station density choropleth map with train stations and lines
- Interactive map interface: click to select proposed station locations
- Sidebar controls for:
  - Latitude/longitude input or map-based selection
  - Tube/rail line selection
  - Simulation execution status with elapsed time display
- Real-time AWS Lambda invocation and S3 result polling
- Comprehensive results display:
  - Simulation metadata (location and line details)
  - Three visualisation charts (affected routes, time savings, demand impact)
  - Affected routes summary and demand impact ranges (expandable dataframes)
  - Interactive impact map with impact legend
  - Overall impact metrics (total time diff, greatest time diff, percentage affected)
- PDF report and KMZ file export
- Dashboard reset functionality

## Supporting Modules

### **df_analysis.py**
DataFrame manipulation and comparison utilities. Handles:
- Passenger impact analysis comparing baseline vs. altered simulations
- Statistical calculations on journey times and passenger flows
- Chart creation functions (Altair) for visualisation:
  - `create_top_affected_routes_chart()`: Routes most impacted by new station
  - `create_top_time_saving_routes_chart()`: Routes with greatest time savings
  - `create_station_demand_impact_chart()`: Station demand changes
- Calculation functions:
  - `get_affected_routes()`: Summary of affected routes
  - `get_demand_impact_ranges()`: Range of demand impacts
  - `get_total_time_spent_diff()`, `get_greatest_time_spent_diff()`, `get_percentage_of_affected_routes()`: Impact metrics

### **folium_functions.py**
Interactive map visualisation utilities. Creates:
- Folium-based interactive maps of the transport network
- Proposed station markers and 800m catchment circles
- Station markers colour-coded by passenger impact
- Line network visualisation
- Click-enabled popups with station details and statistics

### **stations_choropleth.py**
Choropleth map generation for geographic visualisation. Creates:
- Heatmaps showing passenger density by station
- Colour-scaled visualisations of coverage areas
- Geographic boundary layers with station overlays
- Interactive choropleth legends and controls
- `create_choropleth()`: Main function for generating borough-based density maps

### **s3_utils.py**
AWS S3 integration for data access. Handles:
- Loading simulation comparison results from S3 buckets
- Retrieving station reference data from cloud storage
- Folder metadata retrieval for historical simulations
- Managing S3 authentication and error handling

### **analysis.py**
Advanced analysis and report generation utilities. Includes:
- `generate_recommendation_pdf()`: Creates PDF reports of simulation results
- Analysis summary generation
- Coverage context analysis with GIS data

### **kml_export.py**
KML file generation for external GIS applications. Provides:
- `generate_kmz_bytes()`: Export simulation results to KMZ format
- Support for custom styling and icons in KML output
- Integration with external mapping tools (Google Earth, ArcGIS, etc.)

### **coverage_context.py** (Legacy)
Station coverage and accessibility analysis utilities (currently not used in main dashboard)

## File Structure

```
dashboard/
├── Run_Simulations.py                 # Main dashboard entry point
├── pages/
│   └── 2_previous_simulations.py      # Historical simulations sub-page
├── df_analysis.py                     # Chart and metrics calculations
├── folium_functions.py                # Interactive map functions
├── stations_choropleth.py             # Choropleth map generation
├── s3_utils.py                        # AWS S3 utilities
├── analysis.py                        # Report generation
├── kml_export.py                      # KML/KMZ export
├── lss_logo.png                       # Application logo
├── requirements.txt                   # Python dependencies
├── Dockerfile                         # Docker container configuration
├── tests/                             # Unit tests
└── README.md                          # This file
```

## Configuration

### Environment Variables

Required environment variables (set in `.env` file):

```
# AWS Configuration
S3_BUCKET_NAME=c23-travel-simulation-bucket
SIMULATION_LAMBDA_ARN=arn:aws:lambda:eu-west-2:129033205317:function:c23-travel-simulator-simulation

# Google Cloud Configuration (for Earth Engine analysis)
GOOGLE_CLOUD_PROJECT=travel-simulation-497813
GOOGLE_APPLICATION_CREDENTIALS_JSON={service account JSON}

# OpenAI Configuration (for AI-powered analysis summaries)
OPENAI_API_KEY=sk-proj-...
```

### AWS Requirements
- S3 bucket for storing simulation results and station data
- Lambda function ARN for async simulation execution
- Appropriate IAM permissions for S3 and Lambda access

### Google Cloud Requirements
- Google Cloud project with Earth Engine API enabled
- Service account with Earth Engine access (for environmental context analysis)
- Service account credentials in JSON format

### OpenAI Requirements
- Valid OpenAI API key for generating analysis summaries and insights

## Metrics Calculation

- **Visualization**: Multi-page interface displaying simulation results and network impact analysis
- **User Input**: Accepts proposed station coordinates and metadata
- **Simulation Selection**: Compares baseline vs. altered network scenarios
- **Analysis**: Integrates Google Earth Engine for environmental context and OpenAI for report generation
- **Export**: KML export for external GIS tools, PDF report generation
- **Historical View**: Separate page for reviewing previous simulation runs

## Module Overview

**Run_Simulations.py**
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
