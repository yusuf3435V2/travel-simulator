resource "aws_ecr_repository" "c23_travel_simulator-dashboard-ecr" {
    name                 = "c23-travel_simulator-dashboard-ecr"
    image_tag_mutability = "MUTABLE"
    force_delete         = true
}

output "ecr_repository_url" {
    description = "ECR repository URL for Docker image"
    value       = aws_ecr_repository.c23_travel_simulator-dashboard-ecr.repository_url
}

output "ecr_repository_name" {
    description = "ECR repository name"
    value       = aws_ecr_repository.c23_travel_simulator-dashboard-ecr.name
}

data "aws_ecs_cluster" "c23-ecs-cluster" {
    cluster_name = "c23-ecs-cluster"
}

data "aws_vpc" "c23-vpc" {
    filter {
        name   = "tag:Name"
        values = ["c23-VPC"]
    }
}

data "aws_subnets" "c23-public-subnets" {
    filter {
        name   = "tag:Name"
        values = ["c23-public-subnet-*"]
    }
    filter {
        name   = "vpc-id"
        values = [data.aws_vpc.c23-vpc.id]
    }
}

resource "aws_cloudwatch_log_group" "ecs_log_group" {
    name              = "/ecs/c23-travel_simulator-dashboard"
    retention_in_days = 7
}

