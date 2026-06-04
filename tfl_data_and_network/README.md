# TFL Data and Network Module

This module is responsible for fetching real-time data from the Transport for London (TFL) API and constructing a comprehensive transportation network graph. It downloads station information, line data, stop sequences, and travel times to build a complete representation of the London transport network for use in simulations.

## Overview

The module orchestrates a multi-step pipeline:

1. **Fetch tube line identifiers** from TFL API
2. **Retrieve station and stop sequences** for each line
3. **Extract travel times** between consecutive stations
4. **Build a NetworkX graph** with stations as nodes and routes as edges
5. **Connect inter-line transfers** by matching station names across lines
6. **Export the network** to GraphML format for downstream use

## Flow

```
┌──────────────────────────────────────────────────────────┐
│  TFL API Data Pipeline                                   │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  ┌─────────────────┐                                      │
│  │  get_lines.py   │ ──→ Get all tube line IDs           │
│  └────────┬────────┘                                      │
│           ▼                                                │
│  ┌──────────────────────────┐                            │
│  │ get_sequenced_stops.py   │ ──→ Get stations per line  │
│  └────────┬─────────────────┘                            │
│           ▼                                                │
│  ┌──────────────────────┐                                │
│  │ get_travel_times.py  │ ──→ Fetch travel durations    │
│  └────────┬─────────────┘                                │
│           ▼                                                │
│  ┌─────────────────────────────┐                         │
│  │ create_stations_network.py  │ ──→ Build graph        │
│  └────────┬────────────────────┘                         │
│           ▼                                                │
│  ┌─────────────────────────────┐                         │
│  │ connect_nearby_stations.py  │ ──→ Add transfers      │
│  └────────┬────────────────────┘                         │
│           ▼                                                │
│  ┌───────────────────────┐                               │
│  │ Output: GraphML file  │                               │
│  │ + Stations CSV        │                               │
│  └───────────────────────┘                               │
│                                                            │
└──────────────────────────────────────────────────────────┘
```

## Files

### **api_utils.py**

Provides robust HTTP communication utilities with built-in error handling and rate-limiting support. Used throughout the module for all TFL API interactions.

**Key Functions:**
- `setup_logger(log_level)`: Configure logging with specified verbosity level
- `make_api_call_with_retry(url, max_retries=7)`: Fetch data from URL with exponential backoff retry logic
  - Handles HTTP 429 (rate limit) responses automatically
  - Implements exponential backoff (2^attempt, capped at 64 seconds)
  - Retries up to 7 times before giving up
  - Returns empty dict on failure for graceful degradation

**Features:**
- Timeout protection (10 seconds per request)
- Comprehensive error logging
- Rate limit detection and automatic backoff

### **get_lines.py**

Fetches the complete list of tube line identifiers from the TFL API. Serves as the entry point for the data collection pipeline.

**Key Functions:**
- `get_lines(mode="tube")`: Retrieve all tube line IDs
  - Supports multiple modes: "tube", "elizabeth-line", "dlr"
  - Returns list of line IDs (e.g., ["central", "northern", "victoria"])
  - Used to iterate through all lines for subsequent data collection

**Output:**
- List of line identifiers for downstream processing

### **get_sequenced_stops.py**

Retrieves the ordered sequence of stops (stations) for each tube line and direction. Provides the station ordering information needed to construct graph edges.

**Key Functions:**
- `get_line_stops_data(line_id, direction)`: Fetch raw API data for a line and direction
- `get_sequenced_stops(data)`: Parse API response to extract ordered station sequences
  - Extracts NAPTAN IDs (station identifiers)
  - Returns nested lists: [[station1, station2, ...], [alt_route_stations]]
  - Multiple routes per line for branches and variations

**Data Structure:**
- Input: Raw API JSON response
- Output: List of station sequences ordered by travel direction

### **get_travel_times.py**

Queries the TFL Journey API to obtain actual travel time durations between pairs of stations. Critical for accurate graph edge weights.

**Key Functions:**
- `extract_travel_time_data(start_station_id, end_station_id)`: Query journey API
- `get_duration_data_from_api_data(travel_time_data)`: Parse response and extract duration
  - Returns duration in minutes
  - Falls back to 2-minute default if no journey data found
  - Logs warnings for unusually long durations (≥10 minutes for adjacent stops)
- `get_duration_data(start_id, end_id)`: Combined function for direct queries

**Features:**
- Handles missing journey data gracefully with sensible defaults
- Logs anomalies for manual verification
- Supports arbitrary station pairs, not just consecutive stations

### **create_stations_network.py**

Main orchestration module that assembles all collected data into a NetworkX graph. Builds the complete transport network topology.

**Key Functions:**
- `get_lines()`: Wrapper to fetch all line IDs
- `get_line_stops_data(line_id, direction)`: Fetch stops for a line
- `get_stops_from_line(line_data, line_id)`: Extract station metadata from API response
- `add_edge_between_stations(graph, station1, station2, line_id, duration)`: Add edge to graph
- `create_network()`: Main orchestration function that:
  - Iterates through all tube lines
  - Fetches stops for each line
  - Queries travel times between consecutive stops
  - Builds NetworkX MultiGraph with station nodes
  - Saves graph to GraphML format
  - Exports station metadata to CSV

**Graph Structure:**
- **Nodes**: Station IDs (NAPTAN IDs)
- **Edges**: Transit routes between consecutive stations
- **Edge Attributes**:
  - `line_id`: Tube line identifier
  - `duration`: Travel time in minutes
- **Graph Type**: MultiGraph (supports multiple edges between nodes for different lines)

**Outputs:**
- `tube_network.graphml`: Complete network graph in GraphML format
- `Stations.csv`: Station metadata (ID, name, latitude, longitude, line)

### **connect_nearby_stations.py**

Identifies and creates cross-line transfer connections by matching station names. Enables passengers to change between lines at interchange stations.

**Key Functions:**
- `unsuffix_name(station_name)`: Normalize station names
  - Removes suffixes: " Underground Station", " DLR Station", " Elizabeth Line Station", etc.
  - Strips parenthetical notes (e.g., "King's Cross (Circle)" → "King's Cross")
  - Allows matching of same station across different line datasets
- `connect_nearby_stations(graph, station_data)`: Add transfer edges
  - Groups stations by normalized name
  - For each group with multiple stations, adds edges between all pairs
  - Edges have zero-duration attribute for instant transfers
  - Preserves existing edges without duplication

**Features:**
- Enables network-wide passenger transfers
- Zero-cost edges for interchanges
- Handles station name variations across different TFL data sources

## Usage

### Running the Complete Pipeline

```bash
python create_stations_network.py
```

This executes the full workflow:
1. Fetches all tube lines
2. Iterates through each line
3. Downloads station sequences
4. Retrieves travel times
5. Builds the graph
6. Adds cross-line transfers
7. Exports to files

### Individual Module Usage

**Get all tube lines:**
```python
from get_lines import get_lines

lines = get_lines()
print(lines)  # ['central', 'northern', 'victoria', ...]
```

**Fetch stops for a specific line:**
```python
from get_sequenced_stops import get_line_stops_data, get_sequenced_stops

data = get_line_stops_data("central", "inbound")
stops = get_sequenced_stops(data)
print(stops)  # [['station1', 'station2', ...], ...]
```

**Get travel time between stations:**
```python
from get_travel_times import get_duration_data

duration = get_duration_data("940GZZLUBNK", "940GZZLUSST")
print(f"Travel time: {duration} minutes")
```

### Debugging and Logging

Enable debug logging to see detailed API calls and processing:

```bash
python -c "from api_utils import setup_logger; setup_logger('DEBUG'); import create_stations_network"
```

Or run from Python:
```python
from api_utils import setup_logger
setup_logger('DEBUG')
from create_stations_network import create_network
create_network()
```

## Output Files

### **tube_network.graphml**
Complete transport network in GraphML format. Contains:
- All stations as nodes
- Transit routes as edges (with line_id and duration)
- Transfer connections between interchange stations

### **Stations.csv**
Station reference data in CSV format:
- `UniqueId`: NAPTAN station identifier
- `Name`: Human-readable station name
- `Latitude`: Geographic latitude
- `Longitude`: Geographic longitude
- `Line_id`: Primary/first line for the station

## Testing

Comprehensive test suite in `/tests/` directory:

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_get_lines.py

# Run with coverage
pytest --cov tests/
```

**Key Test Files:**
- `test_api_utils.py`: API communication and retry logic
- `test_get_lines.py`: Line fetching functionality
- `test_get_sequenced_stops.py`: Stop sequence parsing
- `test_get_travel_times.py`: Travel time extraction
- `test_create_stations_network.py`: Graph construction
- `test_connect_nearby_stations.py`: Transfer connection logic

## Dependencies

Core dependencies (see `requirements.txt`):
- `requests`: HTTP library for API calls
- `networkx`: Graph data structures and algorithms
- `pandas`: Data manipulation and CSV handling
- `boto3`: AWS S3 integration for cloud storage
- `pytest`: Testing framework

## Performance Considerations

### API Rate Limiting

The TFL API has rate limits:
- Exponential backoff automatically handles 429 responses
- Default 7 retries with maximum 64-second wait
- Initial calls have shorter backoff times

### Network Size

The complete London Underground network contains:
- ~270 stations
- ~400 edges per line (with ~11 lines)
- ~1000 total edges including transfers

### Execution Time

Full network creation typically takes:
- 10 minutes (based on current lines)
- Network traversal for travel time queries dominates execution

## Error Handling

The module implements graceful error handling:
- Missing API data results in default values
- Failed API calls don't halt the pipeline
- Incomplete networks are still usable (missing edges skipped)
- Comprehensive logging for debugging failures

## Docker Deployment

Build and run in Docker:

```bash
docker build -t tfl-data-pipeline .
docker run tfl-data-pipeline python create_stations_network.py
```

The module is containerized for Lambda deployment and cloud execution.

## Future Enhancements

Potential improvements:
- Parallel lambda invocation for different lines, improving network generation speed
- Support for additional transport modes (DLR, Elizabeth Line)
- Real-time network updates via scheduled Lambda functions
