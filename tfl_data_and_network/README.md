# TFL Data & Network Pipeline

Fetches London transport network data from the TFL API and constructs a NetworkX graph representation of stations, lines, and routes. Outputs station metadata and network topology to S3 for use by simulation modules.

**Primary deployment**: AWS Lambda with ECR (see [infrastructure README](../infrastructure/README.md))

**Local usage**: Direct Python execution for development and testing

## Quick Start

### Lambda Deployment

See the [infrastructure README](../infrastructure/README.md#networkx-pipeline-lambda) for deployment steps.

**Lambda invocation** (no parameters required):
```bash
aws lambda invoke --function-name c23-travel-simulator-networkx-pipeline response.json
aws logs tail /aws/lambda/c23-travel-simulator-networkx-pipeline --follow
```

**What it produces** (saved to S3):
- `processed/stations_network.graphml` - NetworkX MultiGraph of the transport network (nodes=stations, edges=routes with travel times)
- `processed/stations.csv` - Station metadata (UniqueId, Name, Latitude, Longitude, Line_id)

### Local Usage

Import from `create_stations_network.py`, `get_lines.py`, `get_sequenced_stops.py`, `get_travel_times.py`, and `api_utils.py`. Requires TFL API access (no key needed for public endpoints).

## Data Pipeline

The Lambda executes this workflow:

1. **Fetch Lines**: Queries TFL API for all tube/DLR/Elizabeth-line routes
2. **Get Sequenced Stops**: For each line, fetches ordered station sequences
3. **Calculate Travel Times**: Retrieves duration between consecutive stations
4. **Connect Nearby Stations**: Links nearby station entrances that serve multiple lines
5. **Build Network Graph**: Creates NetworkX MultiGraph with stations as nodes, routes as edges
6. **Save to S3**: Outputs GraphML file and station CSV for downstream simulations

## Network Structure

**Nodes**: Station entries (can have duplicates for different line interchanges)
- Attributes: station name, coordinates (lat/lon)

**Edges**: Transit connections between stations
- Attributes: `line_id` (route identifier), `duration` (travel time in minutes)

**Graph Type**: MultiGraph (multiple edges between same node pairs for different lines)

## Module Overview

**create_stations_network.py**
Main orchestrator. Calls all sub-modules to fetch API data, construct the graph, and upload to S3. Lambda entry point: `lambda_handler()`.

**get_lines.py**
Fetches available transport lines from TFL API. Supports filtering by mode (tube, dlr, elizabeth-line, etc).

**get_sequenced_stops.py**
Retrieves ordered station sequences for a given line and direction. Parses route topology from API.

**get_travel_times.py**
Calculates travel duration between consecutive stations on each route. Uses TFL timetable data.

**connect_nearby_stations.py**
Identifies and links station entrances that represent the same physical location (e.g., Circle Line vs. District Line entrances). Matches stations by name after removing mode-specific suffixes, enabling multi-line interchange modeling.

**api_utils.py**
Shared utilities for TFL API calls: retry logic for rate limits, error handling, logging setup.

## Development & Testing

Run tests before deploying to Lambda:

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

Tests cover:
- API call retry logic and error handling
- Line and stop data parsing
- Travel time calculations
- Station connection logic
- Graph construction and validation

## Notes & Limitations

- **API Rate Limits**: TFL API enforces rate limits; `api_utils.py` includes retry logic
- **Real-time Data**: Uses live TFL API; network changes reflect current state
- **Station Linking**: Connects stations by matching names (after removing mode suffixes) rather than geographic proximity
- **Mode Coverage**: Currently fetches tube, DLR, and Elizabeth-line; other modes can be added via TFL API
- **No Frequency Data**: Travel times included but service frequency not modeled
