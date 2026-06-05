# Travel Simulator

## Introduction

Travel Simulator is a comprehensive system for simulating passenger movement and analyzing coverage across the London Underground network with the insertion of proposed stations. The project combines real TFL data with discrete event simulation to model passenger flows, visualize network coverage, and provide actionable insights through interactive dashboards and analysis tools.

This system is designed to help transport planners and analysts understand network utilisation patterns, identify coverage gaps, and optimise service delivery across the tube network.

## Quick Start - Running the Dashboard

The fastest way to explore simulations is via the interactive dashboard:

```bash
# From repository root
streamlit run dashboard/Run_Simulations.py
```

The dashboard will launch at `http://localhost:8501` and provides:
- **Interactive Map**: Click on the borough-based station density map to select proposed station locations
- **Simulation Execution**: Run simulations via AWS Lambda with real-time elapsed time display
- **Results Visualization**: View impact charts, affected routes, and metrics
- **Historical Archive**: Browse previous simulations in the "Previous Simulations" page

### Requirements
- Python 3.8+
- Installed dependencies: `pip install -r dashboard/requirements.txt`
- AWS credentials configured locally
- Environment variables: `S3_BUCKET_NAME`, `SIMULATION_LAMBDA_ARN`

## Folder Descriptions

### `/choropleth`
Contains data visualisation functionality for generating choropleth maps and heatmaps. Includes utilities for processing geographic data and creating visual representations of coverage areas and station metrics.

**Key Files:**
- `data_functions.py`: Data processing utilities
- `endmap.py`: Final map generation
- `requirements.txt`: Python dependencies

### `/dashboard`
Streamlit-based interactive multi-page dashboard for simulation execution, visualization, and analysis. Provides real-time interaction with the simulation engine via AWS Lambda, interactive mapping interfaces, and comprehensive results visualization.

**Key Files:**
- `Run_Simulations.py`: Main dashboard entry point - interactive station selection and simulation execution
- `pages/2_previous_simulations.py`: Historical simulation archive and comparison view
- `df_analysis.py`: Chart generation and metric calculations
- `folium_functions.py`: Interactive map utilities
- `stations_choropleth.py`: Borough-based station density maps
- `s3_utils.py`: AWS S3 integration for results and data access

**Running the Dashboard:**
```bash
streamlit run dashboard/Run_Simulations.py
```

### `/infrastructure`
Terraform configuration for AWS infrastructure deployment, including an ECS Service for the dashboard, Lambda functions for simulation and S3 for centralised station and simulation result storage.

This also contains shell scripts for deploying Docker images to the ECR in the infrastructure.

### `/simulation`
Core simulation engine that executes discrete event simulation of passenger movement through the network. Handles passenger collection, distance calculations, and result aggregation.

**Key Files:**
- `run_sim_and_save.py`: Main simulation runner
- `collect_passengers.py`: Passenger data collection
- `distance_maths.py`: Distance and routing calculations
- `result_analysis.py`: Post-simulation analysis
- `s3_utils_sim.py`: AWS S3 utilities for simulation
- `test_collect_passengers.py`: Simulation tests
- `requirements.txt`: Python dependencies

### `/tfl_data_and_network`
Utilities for fetching real TFL API data, constructing the network graph, and managing station sequences. Handles API communication, data transformation, and network topology creation.

**Key Files:**
- `api_utils.py`: TFL API communication
- `get_lines.py`: Retrieve tube line data
- `get_sequenced_stops.py`: Get ordered station sequences
- `get_travel_times.py`: Fetch travel times from API
- `create_stations_network.py`: Build network graph
- `connect_nearby_stations.py`: Add cross-network connections
- `plot_networkx.py`: Network visualization
- `tests/`: Comprehensive test suite for network operations

## Deploying

### Prerequisites

1. **Terraform** installed (v1.0+)
2. **AWS CLI** configured with credentials
3. **Docker** image built locally
4. **S3 bucket** will be created by Terraform: `c23-travel-simulation-bucket`
### What Gets Created

- **ECR Repository**: Docker image registry
- **Lambda Function**: Runs your pipeline with 15-minute timeout and 3GB memory
- **IAM Role**: Permissions for Lambda to write logs and S3
- **EventBridge Rule**: Optional monthly schedule trigger (2 AM UTC on the 1st)
- **CloudWatch Log Group**: 7-day retention logs

### Deployment Steps

#### 1. Create ECR Repository First

```bash
cd infrastructure
terraform init
terraform apply -target aws_ecr_repository.c23_travel_simulator_networkx_pipeline
```

This creates the ECR repository where the Docker image will be stored.

#### 2. Build and Push Docker Image

```bash
./deploy_networkx.sh
```

This script handles:
- ECR login
- Docker build with platform=linux/amd64
- Image tagging
- Push to ECR

#### 3. Deploy Remaining Infrastructure

```bash
terraform apply
```

This creates the Lambda function, IAM roles, EventBridge schedule, and CloudWatch logs.

### Configuration

Edit `terraform.tfvars` to customize:
- `aws_region`: AWS region (default: eu-west-2)
- `aws_access_key_id`: AWS access key ID for Terraform authentication
- `aws_secret_access_key`: AWS secret access key for Terraform authentication

### Cleanup

```bash
# Destroy all AWS resources
terraform destroy

# Remove local Docker image
docker rmi c23-travel-simulator-networkx-pipeline
```

### Outputs

After deployment, Terraform will display:
- ECR repository URL
- Lambda function name and ARN

Use these to:
- Push new Docker images: `docker push <ECR_URL>:latest`
- Invoke Lambda: `aws lambda invoke --function-name <LAMBDA_NAME>`

### Dashboard Access

Once deployed, the Streamlit dashboard will be accessible on port 8501 from the ECS service public IP. Check the AWS ECS console to find the running service and its public IP address.

### Environment Variables

The dashboard requires these environment variables:
- `GOOGLE_CLOUD_PROJECT`: Google Cloud project ID for Earth Engine
- `OPENAI_API_KEY`: OpenAI API key (used for report generation)
AWS access to S3 should be provided via the ECS task role (no `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` env vars needed).


## Testing

### Running Tests

Tests are organized by module. Run all tests from the project root:

```bash
# Run all tests
pytest

# Run specific module tests
pytest tfl_data_and_network/tests/
pytest dashboard/tests/
pytest simulation/test_collect_passengers.py

# Run with coverage
pytest --cov
```

### Test Structure

- **`tfl_data_and_network/tests/`**: Tests for API utilities, network creation, and data fetching
- **`dashboard/tests/`**: Tests for dashboard analysis and coverage functions
- **`simulation/`**: Simulation-specific test files

### Key Test Files

- `tfl_data_and_network/tests/test_api_utils.py`: API communication tests
- `tfl_data_and_network/tests/test_create_stations_network.py`: Network graph creation tests
- `dashboard/tests/test_coverage_context.py`: Coverage analysis tests
- `dashboard/tests/test_analysis.py`: Analysis function tests
- `simulation/test_collect_passengers.py`: Passenger collection tests

### Writing Tests

When adding new functionality, ensure:
- Each module has corresponding tests
- Tests include both unit and integration scenarios
- Test files follow naming convention: `test_*.py`
- Functions include docstrings describing test purpose
