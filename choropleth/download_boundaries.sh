#!/bin/bash

# Download boundaryData.geojson from ArcGIS Hub
curl -o boundaryData.geojson "https://hub.arcgis.com/api/v3/datasets/0a92a355a8094e0eb20a7a66cf4ca7cf_10/downloads/data?format=geojson&spatialRefId=4326&where=1%3D1"

if [ $? -eq 0 ]; then
    echo "Download successful: boundaryData.geojson"
else
    echo "Download failed"
    exit 1
fi