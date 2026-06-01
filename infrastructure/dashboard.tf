resource "aws_ecr_repository" "c23_travel_simulator-dashboard-ecr" {
    name                 = "c23-travel_simulator-dashboard-ecr"
    image_tag_mutability = "MUTABLE"
    force_delete         = true
}

output "ecr_repository_dashboard_url" {
    description = "ECR repository URL for Docker image"
    value       = aws_ecr_repository.c23_travel_simulator-dashboard-ecr.repository_url
}

output "ecr_repository_dashboard_name" {
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

# IAM Role for ECS Task Execution
resource "aws_iam_role" "ecs_task_execution_role" {
    name = "c23-travel_simulator-dashboard-ecs-task-execution-role"

    assume_role_policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
            {
                Action = "sts:AssumeRole"
                Effect = "Allow"
                Principal = {
                    Service = "ecs-tasks.amazonaws.com"
                }
            }
        ]
    })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
    role       = aws_iam_role.ecs_task_execution_role.name
    policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# IAM Role for ECS Task (application permissions)
resource "aws_iam_role" "ecs_task_role" {
    name = "c23-travel_simulator-dashboard-ecs-task-role"

    assume_role_policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
            {
                Action = "sts:AssumeRole"
                Effect = "Allow"
                Principal = {
                    Service = "ecs-tasks.amazonaws.com"
                }
            }
        ]
    })
}

# Policy to allow S3 access for the dashboard
resource "aws_iam_role_policy" "ecs_task_s3_policy" {
    name = "c23-travel_simulator-dashboard-s3-policy"
    role = aws_iam_role.ecs_task_role.id

    policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
            {
                Effect = "Allow"
                Action = [
                    "s3:GetObject",
                    "s3:ListBucket"
                ]
                Resource = [
                    "arn:aws:s3:::c23-travel-simulation-bucket",
                    "arn:aws:s3:::c23-travel-simulation-bucket/*"
                ]
            }
        ]
    })
}

# Security Group for ECS Task
resource "aws_security_group" "dashboard_ecs_sg" {
    name        = "c23-travel_simulator-dashboard-ecs-sg"
    description = "Security group for dashboard ECS task"
    vpc_id      = data.aws_vpc.c23-vpc.id

    ingress {
        from_port   = 8501
        to_port     = 8501
        protocol    = "tcp"
        cidr_blocks = ["0.0.0.0/0"]
    }

    egress {
        from_port   = 0
        to_port     = 0
        protocol    = "-1"
        cidr_blocks = ["0.0.0.0/0"]
    }

    tags = {
        Name = "c23-travel_simulator-dashboard-ecs-sg"
    }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "dashboard" {
    family                   = "c23-travel_simulator-dashboard"
    network_mode             = "awsvpc"
    requires_compatibilities = ["FARGATE"]
    cpu                      = "512"
    memory                   = "1024"
    execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
    task_role_arn            = aws_iam_role.ecs_task_role.arn

    container_definitions = jsonencode([
        {
            name      = "dashboard"
            image     = "${aws_ecr_repository.c23_travel_simulator-dashboard-ecr.repository_url}:latest"
            essential = true
            portMappings = [
                {
                    containerPort = 8501
                    hostPort      = 8501
                    protocol      = "tcp"
                }
            ]
            environment = [
                {
                    name  = "GOOGLE_CLOUD_PROJECT"
                    value = var.GOOGLE_CLOUD_PROJECT
                }
            ]
            logConfiguration = {
                logDriver = "awslogs"
                options = {
                    "awslogs-group"         = aws_cloudwatch_log_group.ecs_log_group.name
                    "awslogs-region"        = var.aws_region
                    "awslogs-stream-prefix" = "ecs"
                }
            }
        }
    ])

    tags = {
        Name = "c23-travel_simulator-dashboard"
    }
}

# ECS Service
resource "aws_ecs_service" "dashboard" {
    name            = "c23-travel_simulator-dashboard-service"
    cluster         = data.aws_ecs_cluster.c23-ecs-cluster.id
    task_definition = aws_ecs_task_definition.dashboard.arn
    desired_count   = 1
    launch_type     = "FARGATE"

    network_configuration {
        subnets          = data.aws_subnets.c23-public-subnets.ids
        security_groups  = [aws_security_group.dashboard_ecs_sg.id]
        assign_public_ip = true
    }

    tags = {
        Name = "c23-travel_simulator-dashboard-service"
    }

    depends_on = [
        aws_ecs_task_definition.dashboard
    ]
}

