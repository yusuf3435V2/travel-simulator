# Passenger Collection & Travel Simulation

Mesa-based agent simulation for modeling passenger journeys through a transport network. Simulates how passengers travel from origin to destination using intelligent pathfinding that accounts for line transfers, walking distances, and travel modes.

**Primary deployment**: AWS Lambda with ECR (see [infrastructure README](../infrastructure/README.md))

**Local usage**: Direct Python execution for development and testing

See [DATA_FORMATS.md](DATA_FORMATS.md) for detailed input/output specifications.

## Quick Start

### Lambda Deployment

See the [infrastructure README](../infrastructure/README.md#simulation-lambda) for deployment steps.

**Lambda invocation**:
```bash
aws lambda invoke --function-name c23-travel-simulator-simulation --cli-binary-format raw-in-base64-out --payload '{"UniqueId": "test_station", "Name": "Test", "Latitude": 51.5, "Longitude": -0.1, "Line_id": "bakerloo"}' response.json
aws logs tail /aws/lambda/c23-travel-simulator-simulation --follow
```

**What the Lambda expects** (JSON input):
```json
{
  "UniqueId": "user_station_1",
  "Name": "My Station",
  "Latitude": 51.5175,
  "Longitude": -0.0532,
  "Line_id": "bakerloo"
}
```

**What it produces** (saved to S3):
- `raw/{UniqueId}/simulation_results_with_user_station.csv` - Passenger journey data with the proposed station added
- `raw/{UniqueId}/simulation_comparison.csv` - Passenger journey comparison vs. baseline
- `raw/{UniqueId}/user_station.json` - The proposed station metadata

### Local Usage

For development and testing, import from `collect_passengers.py`, `result_analysis.py`, and `distance_maths.py`. See [DATA_FORMATS.md](DATA_FORMATS.md) for module functions and data specifications.

## Simulation Workflow

The simulation follows a baseline + comparison approach:

1. **Baseline Simulation** (Lambda): First run calculates journey times with existing network
   - Saved to S3 as `raw/BASELINE.csv`
   - Reused for all subsequent comparisons

2. **Comparison Simulation** (Lambda): When new station proposed
   - Runs simulation with proposed station added to network
   - Compares against baseline to calculate time savings/losses
   - Saves detailed passenger-level comparison data to S3

3. **Analysis**: Post-simulation analytics
   - Calculates aggregate impacts (total time savings, affected routes, demand changes)
   - Generates summary statistics
   - Used by dashboard for visualization

## Core Concepts

### Route Calculation
- **Algorithm**: Modified Dijkstra's with line change penalties
- **Distance metric**: Geographic (Haversine) with travel time as cost
- **Line changes**: Each transfer adds 5 minutes to journey time
- **Objective**: Minimize total travel time, not distance

### Transportation Modes
- **Walking** (<1.6 km): 5 km/h
- **Public Transit** (≥1.6 km): 30 km/h
- Mode choice based on distance from origin to nearest station and destination station to destination

### Station Connection
When adding a new station, it automatically connects to:
- The geographically closest existing station and one of that station’s current neighbors (the original edge between them is removed)
- Connections assume train speed of 45 km/h for distance-to-time conversion

### Travel Time Components
```
Total Time = Walk Time (origin→station) + Transit Time (station→station) + Walk Time (station→destination)
```

## Module Overview

**collect_passengers.py**
Core simulation engine. Contains `TravelModel` (Mesa container), agent creation, passenger loading, and result extraction.

**distance_maths.py**
Haversine distance calculations and nearest station lookup.

**result_analysis.py**
Post-simulation analytics: aggregation, statistics, and comparison between simulations.

**run_sim_and_save.py**
Lambda handler and orchestration. Loads data from S3, runs simulations, saves results to S3.

**s3_utils_sim.py**
AWS S3 utilities for data loading and result storage.

## Development & Testing

Testing should be done before deploying to Lambda. Comprehensive tests are provided in `test_collect_passengers.py`:

```bash
# Run all tests
pytest test_collect_passengers.py -v

# Run specific test
pytest test_collect_passengers.py::test_station_lookup -v

# Run with coverage
pytest test_collect_passengers.py --cov=. --cov-report=html
```

Tests cover:
- Station lookup and nearest station functions
- Path calculation with line penalties
- Distance calculations (Haversine)
- Travel time determination
- Agent creation and simulation
- Data extraction and result formats

## Notes & Limitations

- **Waiting times**: Not fully simulated (instantaneous transfers assumed)
- **Capacity**: No congestion or capacity limits modeled
- **Frequency**: Line frequency not considered
- **Time variation**: No time-of-day variations (static network)
- **Walking paths**: Assume straight-line Euclidean paths
- **Simulation step**: Single time unit step (not calendar-based)
