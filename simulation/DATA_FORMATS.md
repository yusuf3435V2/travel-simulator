# Data Formats & File Specifications

## Input Formats

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
| `day_type` | string | Type of day (e.g. `weekday`, `weekend`) |

**Example**:
```csv
passenger_id,origin_lat,origin_lng,destination_lat,destination_lng,day_type
P001,51.5074,-0.1278,51.5165,-0.1019,weekday
P002,51.4883,-0.3426,51.5175,-0.0532,weekend
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

### 4. Proposed Station (New Station Format)

**Format**: Dictionary with keys `["UniqueId", "Name", "Latitude", "Longitude", "Line_id"]`

**Example** (JSON):
```json
{
  "UniqueId": "user_station_1",
  "Name": "User Station",
  "Latitude": 51.519425328081894,
  "Longitude": -0.09887695312500001,
  "Line_id": "bakerloo"
}
```

## Output Formats

### Extracted Agent Data DataFrame

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
| `walk_time` | float | Time spent travelling between origin/destination and their nearest stations (minutes) |

### Lambda Output to S3

The Lambda function saves the following to S3:

- **Baseline results**: `raw/BASELINE.csv` (created on first run)
- **Altered simulation results**: `raw/{station_id}/simulation_results_with_user_station.csv`
- **Comparison results**: `raw/{station_id}/simulation_comparison.csv`
- **Metadata**: `raw/{station_id}/user_station.json` (the proposed station details)

## Key Functions Reference

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
| `run_simulation_baseline()` | Execute baseline simulation (no new station) |
| `run_simulation_with_user_station()` | Execute simulation with proposed station |
| `compare_simulations()` | Compare baseline and altered results |
