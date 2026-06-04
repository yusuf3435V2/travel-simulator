# Infrastructure & Deployment Configuration

Terraform configuration for deploying containerized travel simulator components to AWS:
- **3 Lambda functions** running Docker containers (networkx, simulation, choropleth)
- **1 ECS Fargate service** running the Streamlit dashboard
- **S3 bucket** for shared data storage
- **IAM roles, ECR repositories, EventBridge schedules, CloudWatch logs**

## Prerequisites

- **Terraform** installed (v1.0+)
- **AWS CLI** configured with credentials
- **Docker** installed for building images
- **Terraform state bucket** exists: `c23-travel-simulation-bucket` (created by Terraform)

## General Setup

```bash
cd infrastructure
terraform init
terraform fmt  # Format all .tf files
terraform validate  # Validate configuration
```

Edit `terraform.tfvars` to customize:
- `aws_region`: AWS region (default: eu-west-2)
- `aws_access_key_id`: AWS access key ID for Terraform authentication
- `aws_secret_access_key`: AWS secret access key for Terraform authentication

---

## NetworkX Pipeline Lambda

Processes TFL API data and creates the station network graph. Runs as ECR-backed Lambda with 15-minute timeout and 3GB memory.

### Deployment

```bash
# Step 1: Create ECR repository
terraform apply -target aws_ecr_repository.c23_travel_simulator_networkx_pipeline

# Step 2: Build and push Docker image
./deploy.sh

# Step 3: Deploy Lambda function
terraform apply
```

The `deploy.sh` script:
- Logs into ECR
- Builds Docker image from `tfl_data_and_network/` with platform=linux/amd64
- Tags and pushes image to ECR

### Invoke Lambda

```bash
# Manual invocation
aws lambda invoke --function-name c23-travel-simulator-networkx-pipeline response.json
aws logs tail /aws/lambda/c23-travel-simulator-networkx-pipeline --follow
```

---

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
- Dashboard.sh should trigger this automatically, or manually: `aws ecs update-service --cluster c23-ecs-cluster --service c23_travel_simulator_dashboard_service --force-new-deployment --region eu-west-2`

**ECR login fails:**
- Verify AWS credentials: `aws sts get-caller-identity`
- Check IAM permissions for ECR push/pull
