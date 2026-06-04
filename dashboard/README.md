# Dashboard

The Travel Simulator Dashboard is an interactive Streamlit application for visualizing simulation results, analyzing passenger flows, and evaluating the impact of proposed transit network changes.

## Running the Dashboard

### Prerequisites

- Python 3.8+
- All dependencies from `requirements.txt` installed
- AWS credentials configured (for S3 access to simulation results)
- Google Cloud credentials (for Earth Engine integration in analysis features)

### Local Execution

From the repository root:
```bash
streamlit run dashboard/dashboard.py
```

Or from the dashboard directory:
```bash
cd dashboard
streamlit run dashboard.py
```

The dashboard will be available at `http://localhost:8501`

### Docker Execution

Build and run the dashboard in a Docker container:
```bash
docker build -f dashboard/Dockerfile -t travel-simulator-dashboard .
docker run -p 8501:8501 --env-file .env travel-simulator-dashboard
```

Note: The `--env-file .env` flag is required to pass AWS and Google Cloud credentials to the container.

### Command-Line Options

Common Streamlit options:
```bash
# Run on specific port
streamlit run dashboard/dashboard.py --server.port 8000

## Dashboard Scripts

### **dashboard.py**
Main entry point and orchestrator for the multi-page interface.
- Handles user input for proposed station locations (latitude, longitude, name)
- Manages simulation run selection and comparison (baseline vs. altered)
- Orchestrates visualization layout and main dashboard rendering

### **analysis.py**
Advanced analysis and report generation utilities.
- Google Earth Engine integration for environmental context analysis
- OpenAI-powered generation of analysis summaries and recommendations
- PDF report generation using ReportLab with coverage and land use context

### **coverage_context.py**
Station coverage and accessibility analysis.
- Calculates 800m walking radius catchment areas around stations
- Performs spatial analysis using GeoPandas to identify accessible populations
- Generates coverage statistics and accessibility metrics

### **df_analysis.py**
DataFrame comparison and analysis utilities.
- Compares passenger flows and journey times between baseline and altered simulations
- Calculates time savings/degradation per route and station demand impacts
- Provides color-coding logic (green for improvements, orange/red for degradation)

### **folium_functions.py**
Interactive map visualization components.
- Creates Folium-based transport network maps with customizable layers
- Overlays proposed station markers and 800m catchment circles
- Color-codes stations by passenger impact with interactive popups

### **kml_export.py**
KML file generation for external GIS applications.
- Exports proposed stations, affected stations, and coverage areas to KML format
- Supports custom styling and icons for Google Earth and ArcGIS visualization

### **s3_utils.py**
AWS S3 integration for cloud data access.
- Loads simulation results and station reference data from S3 buckets
- Caches downloaded data locally for improved performance
- Handles S3 authentication and error handling

### **stations_choropleth.py**
Choropleth map generation for borough-level analysis.
- Loads pre-generated choropleth GeoJSON from S3 with borough boundaries
- Overlays station markers color-coded by impact metrics
- Provides layer controls for filtering by line and impact magnitude

### **pages/2_previous_simulations.py**
Historical analysis and archival page (Streamlit multi-page feature).
- Displays list of all previous simulation runs with metadata
- Enables comparison of results across different proposed stations
- Provides access to archived analysis reports and insights

## Metrics Calculation

See [METRICS.md](METRICS.md) for detailed metrics calculations including journey time, coverage, passenger impact, and demand analysis.

## Data Flow

```
┌──────────────────────┐
│  Simulation Results  │
│  (CSV from S3)       │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────┐
│  DataFrame Analysis      │
│  (df_analysis.py)        │
│  - Comparison            │
│  - Filtering             │
│  - Calculations          │
└──────────┬───────────────┘
           │
      ┌────┴─────┬─────────┬──────────┐
      ▼          ▼         ▼          ▼
  Maps      Metrics   Coverage    Reports
(folium)   (analysis)(context)  (analysis.py)
      │          │         │          │
      └────┬─────┴─────────┴──────────┘
           ▼
    Dashboard UI
    (Streamlit)
```

## Performance Optimization

- **Caching**: Streamlit `@st.cache_data` for expensive computations
- **S3 Caching**: Local file caching of downloaded simulation results
- **Lazy Loading**: Only load data when user navigates to sections
- **Data Sampling**: Option to sample large datasets for faster rendering

## Troubleshooting

### Map Not Loading
- Verify Folium installation: `pip install folium`
- Check internet connection for tile loading
- Ensure coordinates are valid (latitude: -90 to 90, longitude: -180 to 180)

### S3 Connection Errors
- Verify AWS credentials: `aws configure`
- Check S3 bucket name and permissions
- Ensure bucket contains expected CSV files

### Analysis Features Not Working
- Verify Google Cloud credentials for Earth Engine
- Check OpenAI API key for report generation
- Ensure environment variables are set in `.env`

## Configuration

Environment variables (set in `.env`):
- `AWS_REGION`: AWS region for S3 access
- `S3_BUCKET`: S3 bucket containing simulation results
- `GOOGLE_CLOUD_PROJECT`: Google Cloud project ID
- `GOOGLE_APPLICATION_CREDENTIALS_JSON`: Service account JSON
- `OPENAI_API_KEY`: OpenAI API key for analysis
