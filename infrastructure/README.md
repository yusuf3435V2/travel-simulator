# Travel Simulator Infrastructure

This directory contains Terraform configurations and deployment scripts for provisioning the complete cloud infrastructure for the Travel Simulator dashboard and simulation pipeline on AWS.

## Overview

The infrastructure creates a fully automated, serverless system for:
- **Data Pipeline**: Automated TFL network data collection and processing via Lambda
- **Simulation Engine**: Discrete event simulation of passenger journeys via Lambda
- **Dashboard**: Streamlit-based interactive dashboard for results visualisation
- **Storage**: S3 buckets for persisting simulation results and reference data
- **API Layer**: API Gateway for exposing simulation and analysis endpoints

## Files and Their Functions

### Terraform Configuration Files

#### **main.tf**
Primary Terraform entry point and orchestration file. Defines:
- AWS provider configuration
- Root module structure and resource composition
- Output values for deployed infrastructure endpoints
- Integration points between all infrastructure components

#### **variables.tf**
Input variables required by the Terraform configuration. Includes:
- AWS region (`aws_region`)
- AWS credentials for the Terraform AWS provider (`aws_access_key_id`, `aws_secret_access_key`)
- Dashboard configuration (`GOOGLE_CLOUD_PROJECT`, `OPENAI_API_KEY`, `S3_BUCKET_NAME`)

#### **terraform.tfvars** (local only)
Local values assigned to the variables defined in `variables.tf`.

> Note: this repository ignores `*.tfvars` files (see `/.gitignore`), so create `terraform.tfvars` locally (or provide values via `TF_VAR_...` environment variables). Do not commit credentials or API keys.

#### **networkx_lambda.tf**
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
Main deployment orchestration script. Handles:
- Terraform initialisation (`terraform init`)
- Infrastructure planning review (`terraform plan`)
- Full infrastructure provisioning (`terraform apply`)
- Post-deployment configuration and validation
- Error handling and rollback support

Usage:
```bash
./deploy.sh
```

#### **deploy_simulation.sh**
Focused deployment script for the simulation Lambda infrastructure only. Performs:
- Builds and pushes simulation Docker image to ECR
- Deploys or updates the simulation Lambda function
- Configures S3 triggers and IAM permissions
- Updates Lambda environment variables
- Validates Lambda function configuration

Usage:
```bash
./deploy_simulation.sh
```

#### **dashboard.sh**
Deployment script specifically for the dashboard infrastructure. Handles:
- Dashboard application containerisation
- EC2 or ECS cluster setup
- Streamlit application deployment
- Load balancer configuration
- SSL/TLS certificate provisioning
- Dashboard service healthchecks

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
4. **AWS Account** with permissions to create Lambda, EC2, S3, ECR, and API Gateway resources
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
```bash
./deploy_simulation.sh
```

**Dashboard Only:**
```bash
./dashboard.sh
```

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

```bash
# Network pipeline logs
aws logs tail /aws/lambda/travel-simulator-networkx --follow

# Simulation engine logs
aws logs tail /aws/lambda/travel-simulator-simulation --follow
```

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

**Warning**: This will delete all infrastructure including S3 buckets and Lambda functions. Ensure data is backed up before destruction.

## Configuration

Edit `terraform.tfvars` to customize:
- `aws_region`: AWS region (default: eu-west-2)
- `aws_access_key_id`: AWS access key ID for Terraform authentication
- `aws_secret_access_key`: AWS secret access key for Terraform authentication

## Cleanup

```bash
# Destroy all AWS resources
terraform destroy

# Remove local Docker image
docker rmi c23-travel_simulation_networkx_pipeline
```

## Outputs

After deployment, Terraform will display:
- ECR repository URL
- Lambda function name and ARN

Use these to:
- Push new Docker images: `docker push <ECR_URL>:latest`
- Invoke Lambda: `aws lambda invoke --function-name <LAMBDA_NAME>`

## Notes

- Lambda timeout set to 15 minutes (max for API rate limits)
- Memory set to 3GB for better performance
- S3 access required to upload processed data

---

# Dashboard ECS Deployment

This configuration also deploys a Streamlit dashboard to AWS ECS Fargate.

## Deployment Steps

### 1. Create Dashboard ECR Repository and Infrastructure

```bash
cd infrastructure
terraform init # if not already done
terraform apply -target=aws_ecr_repository.c23_travel_simulator_dashboard_ecr
```

This creates the ECR repository for the dashboard Docker image.

### 2. Build and Push Dashboard Docker Image

```bash
./dashboard.sh
```

This script handles:
- ECR login
- Docker build from dashboard directory
- Image tagging
- Push to ECR

### 3. Deploy ECS Task and Service

```bash
terraform apply
```

This creates the ECS task definition, service, security groups, IAM roles, and CloudWatch logs for the dashboard.

## Dashboard Access

Once deployed, the Streamlit dashboard will be accessible on port 8501 from the ECS service public IP. Check the AWS ECS console to find the running service and its public IP address.

## Environment Variables

The dashboard requires these environment variables:
- `GOOGLE_CLOUD_PROJECT`: Google Cloud project ID for Earth Engine

AWS access to S3 should be provided via the ECS task role (no `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` env vars needed).
