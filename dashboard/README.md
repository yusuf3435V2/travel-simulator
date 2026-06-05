# Dashboard

The Travel Simulator Dashboard is an interactive Streamlit multi-page application for visualising simulation results, analysing passenger flows, and evaluating the impact of proposed transit network changes.

## Running the Dashboard

### Prerequisites

- Python 3.8+
- All dependencies from `requirements.txt` installed
- AWS credentials configured (for S3 access to simulation results)
- Environment variables set: `S3_BUCKET_NAME`, `SIMULATION_LAMBDA_ARN`

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

Build and run the dashboard in a Docker container:
```bash
docker build -f dashboard/Dockerfile -t travel-simulator-dashboard .
docker run -p 8501:8501 travel-simulator-dashboard
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

### Journey Time Metrics

**Total Travel Time**: Sum of all time components
```
Total Time = Walking Time (Origin→Station) + 
             Transit Time (Station→Station) + 
             Walking Time (Station→Destination)
```

**Walking Time**: Calculated based on distance and fixed walking speed (5 km/h)
```
Walking Time (minutes) = Distance (km) / 5 * 60
```

**Transit Time**: 
- Sum of edge durations along the path
- Plus 5-minute penalty for each line change/transfer
- Calculated using modified Dijkstra's algorithm

### Passenger Impact Metrics

**Baseline Journey Time**: Time spent without the proposed station
- Recorded from baseline simulation results
- Stored in `time_spent` field

**Altered Journey Time**: Time spent with the proposed station
- Recorded from altered simulation results
- Passengers may use new station if it provides faster routing

**Time Savings**: 
```
Time Savings = Baseline Time - Altered Time
```
- Positive values indicate improvement (passengers benefit)
- Negative values indicate degradation (journey longer with new station)
- Green visualisation for positive, orange/red for negative

**Passenger Count**: Aggregation of station usage
```
Station Passenger Count = Origin Count + Destination Count
```
- Counts passengers boarding (boarding station) at each station
- Counts passengers alighting (destination station) at each station
- Total passenger throughput determines station importance

### Coverage Metrics

**Catchment Area**: 800m walking radius around each station
- Uses Haversine distance formula
- Identifies all locations within walkable range
- Used to determine which passengers can access a station

**Coverage Density**: 
```
Coverage Density = Population in Catchment / Catchment Area
```
- Indicates how many people are served per unit area
- Higher density = more efficient station placement

**Station Proximity**: Distance to nearest existing stations
```
Proximity Impact = Neighbouring Station Count within 1.5km
```
- Measures network redundancy
- More neighbours = less unique contribution
- Fewer neighbours = more novel coverage

### Data Filtering and Display

**Influenced Stations**: 
- Only stations affected by the proposed station are visualised
- Filters out stations with zero passenger impact
- Highlights relevant network effects

**Demand**:

Demand change. coming from switching gets measured based on time savings (m) found for stations that are on altered routes. The probability of a switch can be calculated as follows: $D(m) = \frac{1}{1+e^{-m}}$. This will give a probability of switching between 0 and 1, and bringing different switch probabilities based on affected routes will lead to standard deviation estimates providing demand impact ranges.

**Percentage Change**:
```
Percent Change = (Altered - Baseline) / Baseline * 100%
```
- Shows relative impact of the proposed station
- Used for colour scaling in visualisations
- Helps identify most and least impacted stations

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

