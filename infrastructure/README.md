# Networkx Lambda Terraform Configuration

This Terraform configuration creates an AWS Lambda function that runs your Docker container for the travel simulator network pipeline.

## Prerequisites

1. **Terraform** installed (v1.0+)
2. **AWS CLI** configured with credentials
3. **Docker** image built locally
4. **S3 bucket** created: `c23-travel-simulation-bucket`

## What Gets Created

- **ECR Repository**: Docker image registry
- **Lambda Function**: Runs your pipeline with 15-minute timeout and 3GB memory
- **IAM Role**: Permissions for Lambda to write logs and S3
- **EventBridge Rule**: Optional daily schedule trigger (2 AM UTC)
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
