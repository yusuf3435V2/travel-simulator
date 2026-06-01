#!/bin/bash
# Docker build and push script for c23-travel_simulator-dashboard
# Gets values from Terraform outputs and builds from parent directory

set -e

# Get outputs from Terraform (in current directory)
ECR_REPO_URL=$(terraform output -raw ecr_repository_url)
ECR_REPO_NAME=$(terraform output -raw ecr_repository_name)
AWS_REGION="eu-west-2"

# Change to parent directory where Dockerfile is located
cd ../dashboard

echo "=========================================="
echo "Docker Build and Push Script"
echo "=========================================="
echo ""
echo "Using ECR Repository: ${ECR_REPO_URL}"
echo ""

echo "Step 1: Login to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin $(echo ${ECR_REPO_URL} | cut -d'/' -f1)
echo "✓ ECR login successful"
echo ""

echo "Step 2: Building Docker image from $(pwd)..."
docker buildx build -t ${ECR_REPO_NAME} --provenance=false --platform="linux/amd64" .
echo "✓ Docker image built successfully"
echo ""

echo "Step 3: Tagging image..."
docker tag ${ECR_REPO_NAME}:latest ${ECR_REPO_URL}:latest
echo "✓ Image tagged successfully"
echo ""

echo "Step 4: Pushing to ECR..."
docker push ${ECR_REPO_URL}:latest
echo "✓ Image pushed successfully"
echo ""

echo "=========================================="
echo "✓ All steps completed successfully!"
echo "=========================================="
echo ""
echo "ECR Repository URL: ${ECR_REPO_URL}"
