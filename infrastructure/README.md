# Networkx Lambda Terraform Configuration

This Terraform configuration creates an AWS Lambda function that runs your Docker container for the travel simulator network pipeline.

## Prerequisites

1. **Terraform** installed (v1.0+)
1. **Terraform** installed (v1.0+)
2. **AWS CLI** configured with credentials
3. **Docker** image built locally
4. **S3 bucket** will be created by Terraform: `c23-travel-simulation-bucket`
## What Gets Created

- **ECR Repository**: Docker image registry
- **Lambda Function**: Runs your pipeline with 15-minute timeout and 3GB memory
- **IAM Role**: Permissions for Lambda to write logs and S3
- **EventBridge Rule**: Optional monthly schedule trigger (2 AM UTC on the 1st)
- **CloudWatch Log Group**: 7-day retention logs

## Deployment Steps

### 1. Create ECR Repository First

```bash
cd infrastructure
terraform init
terraform apply -target aws_ecr_repository.c23_travel_simulator_networkx_pipeline
```

This creates the ECR repository where the Docker image will be stored.

### 2. Build and Push Docker Image

```bash
./deploy.sh
```

This script handles:
- ECR login
- Docker build with platform=linux/amd64
- Image tagging
- Push to ECR

### 3. Deploy Remaining Infrastructure

```bash
terraform apply
```

This creates the Lambda function, IAM roles, EventBridge schedule, and CloudWatch logs.

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
terraform init (if not already done)
terraform apply -target aws_ecr_repository.c23_travel_simulator-dashboard-ecr
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

The dashboard requires these environment variables (can be added to the ECS task definition):
- `GOOGLE_CLOUD_PROJECT`: Google Cloud project ID for Earth Engine
- `AWS_ACCESS_KEY_ID`: AWS credentials for S3 access
- `AWS_SECRET_ACCESS_KEY`: AWS credentials for S3 access
