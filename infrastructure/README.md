# Travel Simulator Infrastructure

This directory contains Terraform configurations and deployment scripts for provisioning the complete cloud infrastructure for the Travel Simulator dashboard and simulation pipeline on AWS.

## Overview

The infrastructure creates a fully automated, serverless system for:
- **Data Pipeline**: Automated TFL network data collection and processing via Lambda
- **Simulation Engine**: Discrete event simulation of passenger journeys via Lambda
- **Dashboard**: Streamlit-based interactive dashboard for results visualisation
- **API Layer**: API Gateway for exposing the simulation invocation endpoint

## Files and Their Functions

### Terraform Configuration Files

#### **main.tf**
Terraform backend/provider configuration and shared foundational resources. Defines:
- S3 backend configuration for Terraform state
- AWS provider configuration
- Shared S3 bucket used for reference data and simulation outputs

#### **variables.tf**
Input variables required by the Terraform configuration. Includes:
- AWS region (`aws_region`)
- AWS credentials for the Terraform AWS provider (`aws_access_key_id`, `aws_secret_access_key`)
- Dashboard configuration (`GOOGLE_CLOUD_PROJECT`, `OPENAI_API_KEY`, `S3_BUCKET_NAME`)

#### **terraform.tfvars** (local only)
Local values assigned to the variables defined in `variables.tf`.

> Note: this repository ignores `*.tfvars` files (see `/.gitignore`), so create `terraform.tfvars` locally (or provide values via `TF_VAR_...` environment variables). Do not commit credentials or API keys.

#### **networkx_lambda.tf**
Infrastructure for the TFL network data pipeline Lambda function. Provisions:
- ECR (Elastic Container Registry) repository for Docker images
- Lambda function for network graph creation and processing
- IAM role with S3 and CloudWatch permissions
- EventBridge scheduled trigger for monthly data updates
- CloudWatch log group for Lambda execution logs

#### **simulation_lambda.tf**
Infrastructure for the simulation engine Lambda function. Provisions:
- ECR (Elastic Container Registry) repository for the simulation Docker image
- Lambda function for running simulations (container image)
- IAM role with S3 and CloudWatch Logs permissions
- CloudWatch log group for Lambda execution logs
- `S3_BUCKET_NAME` environment variable for writing results

#### **dashboard.tf**
Infrastructure for the Streamlit dashboard deployment on ECS Fargate. Creates:
- ECR repository for the dashboard image
- ECS task definition and ECS service (Fargate)
- IAM task roles for S3 access and Lambda invocation
- CloudWatch log group for container logs
- Security group/network configuration (port 8501)

> Note: this file references an existing ECS cluster, VPC, and public subnets via Terraform `data` sources.

#### **api_gateway.tf**
API Gateway v2 (HTTP API) configuration for invoking the simulation Lambda. Defines:
- HTTP API (`aws_apigatewayv2_api`)
- `POST /simulate` route
- AWS_PROXY Lambda integration
- Stage with `auto_deploy = true`
- Lambda permission allowing API Gateway invocation

### Deployment Scripts

#### **deploy.sh**
Docker build-and-push script for the NetworkX data pipeline image. It:
- Reads ECR repository outputs from Terraform (`terraform output ...`)
- Logs into ECR
- Builds the Docker image (linux/amd64) from `../tfl_data_and_network`
- Tags and pushes the image to ECR
Usage:
```bash
./deploy_networkx.sh
```

#### **deploy_simulation.sh**
Docker build-and-push script for the simulation image. It:
- Reads the simulation ECR repository outputs from Terraform
- Logs into ECR
- Builds the Docker image (linux/amd64) from `../simulation`
- Tags and pushes the image to ECR

Usage:
```bash
./deploy_simulation.sh
```

#### **dashboard.sh**
Docker build-and-push script for the dashboard image. It:
- Reads the dashboard ECR repository outputs from Terraform
- Logs into ECR
- Builds the Docker image (linux/amd64) from `../dashboard`
- Tags and pushes the image to ECR
- Forces a new deployment of the existing ECS service

Usage:
```bash
./dashboard.sh
```

## Architecture Flow

```
┌─────────────────────────────────────────────────────────┐
│  AWS Infrastructure Overview                             │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────────────┐   ┌──────────────────────┐   │
│  │ TFL Data Pipeline    │   │ Simulation Engine    │   │
│  │ (networkx_lambda)    │   │ (simulation_lambda)  │   │
│  │                      │   │                      │   │
│  │ - ECR Repository     │   │ - ECR Repository     │   │
│  │ - Lambda Function    │   │ - Lambda Function    │   │
│  │ - EventBridge        │   │                      │   │
│  │   (monthly schedule) │   │                      │   │
│  └──────────┬───────────┘   └──────────┬───────────┘   │
│             │                          │                 │
│             └──────────┬───────────────┘                 │
│                        ▼                                  │
│              ┌──────────────────┐                        │
│              │  S3 Storage      │                        │
│              │  (Results & Data)│                        │
│              └────────┬─────────┘                        │
│                       ▼                                   │
│  ┌────────────────────────────────────────────┐         │
│  │  API Gateway                               │         │
│  │  (REST API Endpoints)                      │         │
│  │  - /simulate                               │         │
│  │  - /results                                │         │
│  │  - /analysis                               │         │
│  └──────────────────────┬─────────────────────┘         │
│                         ▼                                 │
│  ┌────────────────────────────────────────────┐         │
│  │  Dashboard (Streamlit on EC2/ECS)          │         │
│  │  - Interactive Results Visualisation       │         │
│  │  - Simulation History                      │         │
│  │  - Coverage Analysis                       │         │
│  └────────────────────────────────────────────┘         │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## Deployment Prerequisites

1. **Terraform** installed (v1.0+)
2. **AWS CLI** configured with appropriate credentials
3. **Docker** installed locally for building container images
4. **AWS Account** with permissions to create Lambda, ECS, S3, ECR, API Gateway, IAM, and CloudWatch resources
5. **S3 Bucket** for storing reference data and simulation results (created automatically)

## Deployment Steps

### Initial Setup

1. **Initialise Terraform:**
   ```bash
   cd infrastructure
   terraform init
   ```

2. **Review planned infrastructure:**
   ```bash
   terraform plan
   ```

### Full Deployment

Deploy all infrastructure components:
```bash
./deploy.sh
```

This creates:
- S3 buckets for results and data storage
- ECR repositories for Docker images
- Network pipeline Lambda function with monthly schedule
- Simulation engine Lambda with S3 triggers
- Dashboard infrastructure (EC2/ECS)
- API Gateway with endpoints
- IAM roles and security groups
- CloudWatch logging and monitoring

### Selective Deployment

Deploy only specific components:

**Network Pipeline Only:**
```bash
terraform apply -target=module.networkx_lambda
```

**Simulation Engine Only:**
terraform apply -target=aws_lambda_function.c23_travel_simulator_simulation
./deploy_simulation.sh

**Dashboard Only:**
terraform apply -target=aws_ecs_service.dashboard
./dashboard.sh

## Outputs

After deployment, Terraform outputs the following endpoints:

- **API Gateway Base URL**: For API integration
- **Dashboard URL**: For accessing the interactive dashboard
- **S3 Bucket Name**: For results storage and retrieval
- **CloudWatch Log Groups**: For monitoring and debugging

Access these values with:
```bash
terraform output
```

## Monitoring and Debugging

### View Lambda Logs

# Network pipeline logs
aws logs tail /aws/lambda/c23-travel-simulator-networkx-pipeline --follow

# Simulation engine logs
aws logs tail /aws/lambda/c23-travel-simulator-simulation --follow

### Check Lambda Executions

```bash
aws lambda list-functions
aws lambda get-function-concurrency --function-name <function-name>
```

### Monitor S3 Activity

```bash
aws s3 ls s3://c23-travel-simulation-bucket --recursive
```

## Destroying Infrastructure

To tear down all provisioned resources:

```bash
terraform destroy
```

**Warning**: `terraform destroy` may fail if the S3 bucket is not empty (and this project also uses that bucket as the Terraform backend). Empty the bucket and migrate state to a different backend before attempting to delete the bucket, and back up any required data first.

## Simulation Lambda

Runs passenger flow simulations. ECR-backed Lambda with 15-minute timeout and 3GB memory.

### Deployment

```bash
# Step 1: Create ECR repository
terraform apply -target aws_ecr_repository.c23_travel_simulator_simulation

# Step 2: Build and push Docker image
./deploy_simulation.sh

# Step 3: Deploy Lambda function
terraform apply
```

The `deploy_simulation.sh` script:
- Logs into ECR
- Builds Docker image from `simulation/` with platform=linux/amd64
- Tags and pushes image to ECR

### Invoke Lambda

```bash
aws lambda invoke --function-name c23-travel-simulator-simulation response.json
aws logs tail /aws/lambda/c23-travel-simulator-simulation --follow
```

---

## Choropleth Pipeline Lambda

Generates choropleth maps showing station density by borough. ECR-backed Lambda with 15-minute timeout and 3GB memory.

### Deployment

```bash
# Step 1: Create ECR repository
terraform apply -target aws_ecr_repository.c23_travel_simulator_choropleth_pipeline

# Step 2: Build and push Docker image
./deploy_choropleth.sh

# Step 3: Deploy Lambda function
terraform apply
```

The `deploy_choropleth.sh` script:
- Logs into ECR
- Builds Docker image from `choropleth/` with platform=linux/amd64
- Tags and pushes image to ECR

### Invoke Lambda

```bash
aws lambda invoke --function-name c23-travel-simulator-choropleth-pipeline response.json
aws logs tail /aws/lambda/c23-travel-simulator-choropleth-pipeline --follow
```

---

## Dashboard ECS Deployment

Streamlit dashboard running on ECS Fargate. Accessible on port 8501.

## Dashboard ECS Deployment

Streamlit dashboard running on ECS Fargate. Accessible on port 8501.

### Deployment

```bash
# Step 1: Create ECR repository and ECS infrastructure
terraform apply -target aws_ecr_repository.c23_travel_simulator_dashboard_ecr

# Step 2: Build and push Docker image
./dashboard.sh

# Step 3: Deploy ECS task definition and service
terraform apply
```

The `dashboard.sh` script:
- Logs into ECR
- Builds Docker image from `dashboard/` with platform=linux/amd64
- Tags and pushes image to ECR
- Triggers ECS service redeployment to pull the new image

### Access Dashboard

Once deployed, find the running service in the AWS ECS console:
- Go to `Clusters > c23-ecs-cluster > Services > c23_travel_simulator_dashboard_service`
- Click the service and find its public IP address
- Access dashboard at `http://<public-ip>:8501`

### Environment Variables

Configure in ECS task definition:
- `GOOGLE_CLOUD_PROJECT`: Google Cloud project ID for Earth Engine
- `GOOGLE_APPLICATION_CREDENTIALS_JSON`: Service account JSON (if using Earth Engine)
- `OPENAI_API_KEY`: OpenAI API key for analysis features (optional)

AWS S3 access is provided via the ECS task role (no explicit AWS credentials needed).

---

## Cleanup

```bash
# Destroy all AWS resources
terraform destroy

# Remove local Docker images
docker rmi c23-travel_simulator_networkx_pipeline
docker rmi c23-travel_simulator_simulation
docker rmi c23-travel_simulator_choropleth_pipeline
docker rmi c23_travel_simulator_dashboard_ecr
```

---

## Troubleshooting

**Lambda not starting after Docker push:**
- Update Lambda configuration: `aws lambda update-function-code --function-name <name> --image-uri <ecr-url>:latest`

**ECS service not updating after Docker push:**
- `dashboard.sh` should trigger this automatically, or manually: `aws ecs update-service --cluster c23-ecs-cluster --service c23_travel_simulator_dashboard_service --force-new-deployment --region eu-west-2`

**ECR login fails:**
- Verify AWS credentials: `aws sts get-caller-identity`
- Check IAM permissions for ECR push/pull
