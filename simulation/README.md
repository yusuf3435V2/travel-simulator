# Passenger Collection & Travel Simulation

## Overview

This folder contains a Mesa-based agent simulation module that models passenger journeys through a transport network. The module simulates how passengers travel from origin to destination using the station network, with intelligent pathfinding that accounts for line transfers and mode choices.

## Core Functionality

### Simulation Components

#### **PassengerAgent**
Represents individual passengers who travel through the transit network. Each agent:
- Starts at an origin location and aims to reach a destination (both latitude/longitude)
- Finds the nearest station to their origin and their destination
- Works out optimal route to get between these stations via public transport

#### **TravelModel**
The Mesa model container that:
- Manages all passenger agents
- Maintains the transport network graph
- Stores station metadata
- Supports adding new stations dynamically
- Runs simulation steps

### Key Features

1. **Intelligent Route Planning**
   - Uses modified Dijkstra's algorithm
   - Considers line changes as a cost (penalises transfers)
   - Calculates shortest paths by time, not distance

2. **Dynamic Station Addition**
   - Add new stations to the existing network
   - Automatically connects new stations to closest consecutive stations
   - Updates network structure based on new calculated station distances, assuming a train speed of 45km/h

3. **Multi-Mode Transportation**
   - Walking: For short distances (=< 1.6 km)
   - Bus/Public Transit: For long distances (> 1.6 km)

4. **Travel Time Tracking**
   - Total journey time
   - Transit time (time getting from origin to station, and station to destination)
   - Line change penalties

## Travel Assumptions

### Transportation Speeds
Speeds are fixed and mode-dependent:
- **Walking Speed**: 5 km/h (0.0833 km/min)
- **Public Transit Speed**: 30 km/h (0.5 km/min)

### Travel Process
For each passenger:
1. **Origin to Nearest Station**: Mode chosen based on distance
2. **Transit Journey**: Along graph edges with line change penalties
3. **Station to Destination**: Mode chosen based on distance

### Line Change Costs
- Each line change adds 5 minutes to travel time
- Line changes are detected when consecutive edges belong to different lines
- Algorithm actively minimises line changes in route planning

### Distance Calculations
- Uses Haversine distance for geographic calculations
- Automatically finds nearest stations using lat/long coordinates

## Files

### **collect_passengers.py**
Core module for passenger data collection and simulation setup. Contains the `TravelModel` class (Mesa simulation container) and utilities for:
- Loading passenger data from CSV files
- Creating passenger agents with origin/destination coordinates
- Assigning unique IDs to passenger routes
- Extracting agent trajectory data after simulation completes
- Converting simulation results to DataFrames for analysis

### **distance_maths.py**
Mathematical utilities for calculating distances and finding nearest stations. Includes:
- Haversine formula implementation for geographic distance calculation

### **result_analysis.py**
Post-simulation analysis and statistical utilities. Provides functions to:
- Calculate aggregate journey statistics (mean, median, percentile travel times)
- Analyse route characteristics and passenger flows
- Generate summary reports of simulation results
- Compare simulation outcomes across different network configurations

### **run_sim_and_save.py**
Orchestration script for executing complete simulation workflows. Handles:
- Loading all required input data (passengers, stations, network graph)
- Initialising and running the simulation model
- Extracting results and performing post-simulation analysis
- Saving outputs to local storage and AWS S3

### **s3_utils_sim.py**
AWS S3 integration utilities for cloud storage operations. Enables:
- Uploading simulation results to S3 buckets
- Downloading reference data from S3
- Managing S3 file paths and naming conventions

## Input Format

### 1. Passenger Data CSV
**File**: `passengers.csv` (or similar)

**Required Columns**:
| Column | Type | Description |
|--------|------|-------------|
| `origin_lat` | float | Latitude of starting location |
| `origin_lng` | float | Longitude of starting location |
| `destination_lat` | float | Latitude of ending location |
| `destination_lng` | float | Longitude of ending location |

**Example**:
```csv
passenger_id,origin_lat,origin_lng,destination_lat,destination_lng
51.5074,-0.1278,51.5165,-0.1019
51.4883,-0.3426,51.5175,-0.0532
```

### 2. Station Data CSV
**File**: `stations/Stations.csv`

**Required Columns**:
| Column | Type | Description |
|--------|------|-------------|
| `UniqueId` | string | Station NaPTAN ID |
| `Name` | string | Human-readable station name |
| `Latitude` | float | Station latitude |
| `Longitude` | float | Station longitude |
| `Line_id` | string | Primary line identifier |

**Example**:
```csv
UniqueId,Name,Latitude,Longitude,Line_id
940GZZLUBNK,Bank,51.513356,-0.088899,northern
940GZZLUSST,South Kensington,51.493541,-0.174961,circle
```

### 3. Transport Network GraphML
**File**: `stations/tube_network.graphml`

**Edge Attributes**:
| Attribute | Type | Description |
|-----------|------|-------------|
| `duration` | float | Travel time in minutes between stations |
| `line_id` | string | Transit line identifier |

**GraphML Structure Example**:
```xml
<graph>
  <node id="940GZZLUBNK">
    <data key="name">Bank</data>
  </node>
  <edge source="940GZZLUBNK" target="940GZZLUSST">
    <data key="duration">2.5</data>
    <data key="line">northern</data>
  </edge>
</graph>
```

### 4. New Proposed Station

**Format**
A dictionary with keys `["UniqueId", "Name", "Latitude", "Longitude", "Line_id"]` 

**Example** (JSON)

    {
      "UniqueId": "user_station_1",
      "Name": "User Station",
      "Latitude": 51.519425328081894,
      "Longitude": -0.09887695312500001,
      "Line_id": "bakerloo"
    }

## Output Format

### Extracted Agent Data
After simulation, `extract_agent_data()` returns a DataFrame with:

| Column | Type | Description |
|--------|------|-------------|
| `route_id` | int | Unique route identifier |
| `passenger_id` | string | Passenger identifier |
| `origin_lat` | float | Origin latitude |
| `origin_lng` | float | Origin longitude |
| `destination_lat` | float | Destination latitude |
| `destination_lng` | float | Destination longitude |
| `day_type` | string | Day type |
| `nearest_station` | string | Name of boarding station |
| `alighting_station` | string | Name of exit station |
| `time_spent` | float | Total journey time in minutes |
| `transit_time` | float | Time spent walking and waiting in minutes |

## Usage Example: Unmodified Network

```python
from collect_passengers import (
    load_graphml,
    load_user_information,
    assign_unique_id_to_routes,
    create_agents_from_passenger_data,
    extract_agent_data,
    TravelModel
)
import pandas as pd

# Load data
graph = load_graphml("test_data/tube_network.graphml")
station_data = pd.read_csv("test_data/Stations.csv")
passenger_data = load_user_information("test_data/passengers.csv")

# Prepare passenger data
passenger_data = assign_unique_id_to_routes(passenger_data)

# Create and run model
model = TravelModel(graph, station_data)
create_agents_from_passenger_data(passenger_data, model)
model.step()

# Extract and save results
results = extract_agent_data(model)
results.to_csv("results.csv", index=False)
```

## Usage Example: Adding A New Station

You can dynamically add a new station to the network:

```python
from collect_passengers import add_station_to_stations_data, add_station_to_network

# Define new station
new_station = {
    "UniqueId": "user_station_1",
    "Name": "My Custom Station",
    "Latitude": 51.5175,
    "Longitude": -0.0532,
    "Line_id": "district"
}

# Add to stations data
station_data = add_station_to_stations_data(
    station_data,
    new_station["UniqueId"],
    new_station["Latitude"],
    new_station["Longitude"],
    new_station["Line_id"],
    new_station["Name"]
)

# Add to network graph
add_station_to_network(
    graph,
    new_station["UniqueId"],
    new_station["Latitude"],
    new_station["Longitude"],
    new_station["Line_id"],
    station_data,
    new_station["Name"]
)

# Create model with new stations
model = TravelModel(graph, station_data, new_stations=[new_station])
```

## Key Functions

| Function | Purpose |
|----------|---------|
| `load_graphml()` | Load transport network from GraphML file |
| `load_user_information()` | Load passenger data from CSV |
| `assign_unique_id_to_routes()` | Add route_id column to passenger data |
| `get_nearest_station()` | Find closest station to coordinates |
| `shortest_path_between_stations()` | Calculate optimal route with line penalty |
| `choose_transport_speed()` | Select mode based on distance |
| `determine_travel_time()` | Calculate travel time for distance |
| `create_agents_from_passenger_data()` | Initialize agents in model |
| `extract_agent_data()` | Export agent results to DataFrame |

## Dependencies

- `networkx`: Graph operations and pathfinding
- `mesa`: Agent-based simulation framework
- `pandas`: Data manipulation
- `distance_maths`: Haversine distance calculations

## Testing

Comprehensive tests are provided in `test_collect_passengers.py`, including:
- Station lookup functions
- Path calculation with line penalties
- Distance calculations
- Travel time determination
- Agent creation and data extraction

Run tests with:
```bash
pytest simulation/test_collect_passengers.py -v
```

## Limitations & Future Work

- Waiting time at stations not fully simulated
- No congestion or capacity limits
- Line frequency not considered
- No time-of-day variations
- Walking times assume straight-line paths
- Single time unit step (not calendar-based)
