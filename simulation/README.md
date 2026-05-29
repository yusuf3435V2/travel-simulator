# Passenger Collection & Travel Simulation

## Overview

`collect_passengers.py` is a Mesa-based agent simulation module that models passenger journeys through a transport network. The module simulates how passengers travel from origin to destination using public transit, with intelligent pathfinding that accounts for line transfers and mode choices.

## Core Functionality

### Simulation Components

#### **PassengerAgent**
Represents individual passengers who travel through the transit network. Each agent:
- Starts at an origin location (latitude/longitude)
- Finds the nearest transit station
- Plans an optimal route to their destination
- Travels via public transit
- Walks from the destination station to their final location

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
   - Considers line changes as a cost (penalizes transfers)
   - Calculates shortest paths by time, not distance

2. **Dynamic Station Addition**
   - Add new stations to the existing network
   - Automatically connects new stations to closest consecutive stations
   - Updates network structure intelligently

3. **Multi-Mode Transportation**
   - Walking: For short distances (< 1.6 km)
   - Cycling: For medium distances (1.6 - 5 km)
   - Bus/Public Transit: For long distances (> 5 km)

4. **Travel Time Tracking**
   - Total journey time
   - Transit time (time on public transport)
   - Line change penalties
   - Walking time

## Travel Assumptions

### Transportation Speeds
Speeds are fixed and mode-dependent:
- **Walking Speed**: 5 km/h (0.0833 km/min)
- **Cycling Speed**: 20 km/h (0.333 km/min)
- **Public Transit Speed**: 30 km/h (0.5 km/min)

### Distance-Based Mode Selection
```
Distance < 1.6 km  → Walk
1.6 km ≤ Distance < 5 km  → Bike
Distance ≥ 5 km  → Public Transit
```

### Travel Process
For each passenger:
1. **Origin to Nearest Station**: Mode chosen based on distance
2. **Wait for Transit**: (Currently not simulated)
3. **Transit Journey**: Along graph edges with line change penalties
4. **Station to Destination**: Mode chosen based on distance

### Line Change Costs
- Each line change adds 5 minutes to travel time
- Line changes are detected when consecutive edges belong to different lines
- Algorithm actively minimizes line changes in route planning

### Distance Calculations
- Uses Haversine distance for geographic calculations
- Automatically finds nearest stations using lat/long coordinates
- Accurate for the London transit system scale

## Input Format

### 1. Passenger Data CSV
**File**: `passengers.csv` (or similar)

**Required Columns**:
| Column | Type | Description |
|--------|------|-------------|
| `passenger_id` | string | Unique identifier for the passenger |
| `origin_lat` | float | Latitude of starting location |
| `origin_lng` | float | Longitude of starting location |
| `destination_lat` | float | Latitude of ending location |
| `destination_lng` | float | Longitude of ending location |
| `day_type` | string | Type of day (e.g., "weekday", "weekend") |

**Example**:
```csv
passenger_id,origin_lat,origin_lng,destination_lat,destination_lng,day_type
P001,51.5074,-0.1278,51.5165,-0.1019,weekday
P002,51.4883,-0.3426,51.5175,-0.0532,weekday
```

### 2. Station Data CSV
**File**: `stations/Stations.csv`

**Required Columns**:
| Column | Type | Description |
|--------|------|-------------|
| `UniqueId` | string | Unique station identifier |
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
| `line` or `line_id` | string | Transit line identifier |

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

## Usage Example

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
graph = load_graphml("stations/tube_network.graphml")
station_data = pd.read_csv("stations/Stations.csv")
passenger_data = load_user_information("passengers.csv")

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

## Advanced: Adding New Stations

You can dynamically add new stations to the network:

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
