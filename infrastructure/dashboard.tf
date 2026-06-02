resource "aws_ecr_repository" "c23_travel_simulator_dashboard_ecr" {
  name                 = "c23_travel_simulator_dashboard_ecr"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

output "ecr_repository_dashboard_url" {
  description = "ECR repository URL for Docker image"
  value       = aws_ecr_repository.c23_travel_simulator_dashboard_ecr.repository_url
}

output "ecr_repository_dashboard_name" {
  description = "ECR repository name"
  value       = aws_ecr_repository.c23_travel_simulator_dashboard_ecr.name
}

data "aws_ecs_cluster" "c23_ecs_cluster" {
  cluster_name = "c23-ecs-cluster"
}

data "aws_vpc" "c23_vpc" {
  filter {
    name   = "tag:Name"
    values = ["c23-VPC"]
  }
}

data "aws_subnets" "c23_public_subnets" {
  filter {
    name   = "tag:Name"
    values = ["c23-public-subnet-*"]
  }
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.c23_vpc.id]
  }
}

resource "aws_cloudwatch_log_group" "ecs_log_group" {
  name              = "/ecs/c23_travel_simulator_dashboard"
  retention_in_days = 7
}

# IAM Role for ECS Task Execution
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "c23_travel_simulator_dashboard_ecs_task_execution_role"

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
  name = "c23_travel_simulator_dashboard_ecs_task_role"

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
  name = "c23_travel_simulator_dashboard_s3_policy"
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
  name        = "c23_travel_simulator_dashboard_ecs_sg"
  description = "Security group for dashboard ECS task"
  vpc_id      = data.aws_vpc.c23_vpc.id
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
    Name = "c23_travel_simulator_dashboard_ecs_sg"
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "dashboard" {
  family                   = "c23_travel_simulator_dashboard"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "dashboard"
      image     = "${aws_ecr_repository.c23_travel_simulator_dashboard_ecr.repository_url}:latest"
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
        },
        {
          name  = "S3_BUCKET_NAME"
          value = var.S3_BUCKET_NAME

        },
        {
          name  = "OPENAI_API_KEY"
          value = var.OPENAI_API_KEY
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
    Name = "c23_travel_simulator_dashboard"
  }
}

resource "aws_iam_role_policy" "ecs_task_lambda_invoke_policy" {
  name = "c23_travel_simulator_dashboard_lambda_invoke_policy"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = aws_lambda_function.c23_travel_simulator_simulation.arn
      }
    ]
  })
}

# ECS Service
resource "aws_ecs_service" "dashboard" {
  name            = "c23_travel_simulator_dashboard_service"
  cluster         = data.aws_ecs_cluster.c23_ecs_cluster.id
  task_definition = aws_ecs_task_definition.dashboard.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.c23_public_subnets.ids
    security_groups  = [aws_security_group.dashboard_ecs_sg.id]
    assign_public_ip = true
  }

  tags = {
    Name = "c23_travel_simulator_dashboard_service"
  }

  depends_on = [
    aws_cloudwatch_log_group.ecs_log_group,
    aws_iam_role_policy_attachment.ecs_task_execution_role_policy,
    aws_iam_role_policy.ecs_task_s3_policy,
    aws_iam_role_policy.ecs_task_lambda_invoke_policy,
    aws_ecs_task_definition.dashboard
  ]
}

