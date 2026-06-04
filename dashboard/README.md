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
docker run -p 8501:8501 travel-simulator-dashboard
```

### Command-Line Options

Common Streamlit options:
```bash
# Run on specific port
streamlit run dashboard/dashboard.py --server.port 8000

## Dashboard Scripts

### **dashboard.py**
Main dashboard application and entry point. Provides:
- Multi-page interface using Streamlit pages
- User input for proposed station locations (latitude, longitude, name)
- Selection of baseline and altered simulation results for comparison
- Main visualisation container and layout orchestration
- Navigation between different analysis views

### **analysis.py**
Advanced analysis and report generation utilities. Includes:
- Google Earth Engine integration for environmental context analysis
- OpenAI integration for generating analysis summaries and insights
- PDF report generation using ReportLab
- Coverage context analysis with GIS data
- AI-powered interpretation of simulation results

### **coverage_context.py**
Station coverage and accessibility analysis. Provides:
- Calculates coverage areas around stations using 800m walking radius
- Loads station data from S3
- Performs spatial analysis using GeoPandas
- Identifies stations within catchment areas
- Generates coverage statistics and metrics

### **df_analysis.py**
DataFrame manipulation and comparison utilities. Handles:
- Passenger impact analysis comparing baseline vs. altered simulations
- Statistical calculations on journey times and passenger flows
- Color-coding logic for visualising time savings (green) vs. increases (orange/red)
- Station demand calculation by aggregating origin and destination flows
- Filtering and transformation of comparison data

### **folium_functions.py**
Interactive map visualisation utilities. Creates:
- Folium-based interactive maps of the transport network
- Proposed station markers and 800m catchment circles
- Station markers colour-coded by passenger impact
- Line network visualization
- Click-enabled popups with station details and statistics

### **kml_export.py**
KML file generation for external GIS applications. Provides:
- Export of proposed station locations to KML format
- Export of affected stations and coverage areas to KML
- Support for custom styling and icons in KML output
- Integration with external mapping tools (Google Earth, ArcGIS, etc.)

### **s3_utils.py**
AWS S3 integration for data access. Handles:
- Loading simulation results from S3 buckets
- Retrieving station reference data from cloud storage
- Caching downloaded data for performance
- Managing S3 authentication and error handling

### **stations_choropleth.py**
Choropleth map generation for geographic visualisation. Creates:
- Heatmaps showing passenger density by station
- Colour-scaled visualisations of impact metrics
- Geographic boundary layers with station overlays
- Interactive choropleth legends and controls

### **pages/2_previous_simulations.py**
Multi-page dashboard section for historical analysis. Displays:
- List of previous simulation runs with metadata
- Comparison of results across different proposed stations
- Historical trends in network impact
- Archive of past analysis and reports

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

