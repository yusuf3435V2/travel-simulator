# Metrics Calculation

## Journey Time Metrics

**Total Travel Time**: 
```
Total Time = Walking Time (Origin→Station) + Transit Time (Station→Station) + Walking Time (Station→Destination)
```

**Walking Time**: Calculated based on distance and fixed walking speed (5 km/h)
```
Walking Time (minutes) = Distance (km) / 5 * 60
```

**Transit Time**: Sum of edge durations along the path plus 5-minute penalty per line change, using modified Dijkstra's algorithm.

**Time Savings**: 
```
Time Savings = Baseline Time - Altered Time
```
Positive values indicate improvement (green), negative values indicate degradation (orange/red).

**Passenger Count**: 
```
Station Passenger Count = Origin Count + Destination Count
```
Aggregates passengers boarding and alighting at each station.

## Coverage Metrics

**Catchment Area**: 800m walking radius around each station using Haversine distance formula.

**Coverage Density**: 
```
Coverage Density = Population in Catchment / Catchment Area
```
Indicates how many people are served per unit area.

**Station Proximity**: 
```
Proximity Impact = Neighbouring Station Count within 1.5km
```
Measures network redundancy and unique contribution of new station.

## Data Filtering and Display

**Influenced Stations**: Only stations affected by the proposed station are visualised, filtering out stations with zero passenger impact.

**Demand**: Measured based on time savings. Probability of switching calculated as:
$$D(m) = \frac{1}{1+e^{-m}}$$

This gives switching probability between 0 and 1, with standard deviation estimates providing demand impact ranges.

**Percentage Change**: 
```
Percent Change = (Altered - Baseline) / Baseline * 100%
```
Used for colour scaling and identifying most/least impacted stations.
