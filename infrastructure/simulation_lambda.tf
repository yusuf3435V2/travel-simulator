# ECR Repository for the Docker image
resource "aws_ecr_repository" "c23_travel_simulator_simulation" {
  name                 = "c23-travel-simulator-simulation"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

# IAM Role for Lambda execution
resource "aws_iam_role" "c23_travel_simulator_simulation_lambda_role" {
  name = "c23-travel-simulator-simulation-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "lambda.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

# IAM Policy for Lambda to access S3
resource "aws_iam_policy" "c23_travel_simulator_simulation_s3_policy" {
  name = "c23-travel-simulator-simulation-s3-policy"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ],
        Resource = [
          aws_s3_bucket.travel_simulation_bucket.arn,
          "${aws_s3_bucket.travel_simulation_bucket.arn}/*"
        ]
      }
    ]
  })
}

# IAM Policy for Lambda to write logs
resource "aws_iam_policy" "c23_travel_simulator_simulation_logs_policy" {
  name = "c23-travel-simulator-simulation-logs-policy"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "*"
      }
    ]
  })
}

# Attach S3 policy to Lambda role
resource "aws_iam_role_policy_attachment" "c23_travel_simulator_simulation_attach_s3_policy" {
  role       = aws_iam_role.c23_travel_simulator_simulation_lambda_role.name
  policy_arn = aws_iam_policy.c23_travel_simulator_simulation_s3_policy.arn
}

# Attach logs policy to Lambda role
resource "aws_iam_role_policy_attachment" "c23_travel_simulator_simulation_attach_logs_policy" {
  role       = aws_iam_role.c23_travel_simulator_simulation_lambda_role.name
  policy_arn = aws_iam_policy.c23_travel_simulator_simulation_logs_policy.arn
}

# Lambda Function using Docker image from ECR
resource "aws_lambda_function" "c23_travel_simulator_simulation" {
  function_name = "c23-travel-simulator-simulation"
  role          = aws_iam_role.c23_travel_simulator_simulation_lambda_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.c23_travel_simulator_simulation.repository_url}:latest"
  
  image_config {
    entry_point = ["/lambda-entrypoint.sh"]
    command     = ["run_sim_and_save.lambda_handler"]
  }

  memory_size = 3008  # Maximum memory for better performance
  timeout     = 900   # 15 minutes for simulation

  architectures = ["x86_64"]
  environment {
    variables = {
      S3_BUCKET_NAME = aws_s3_bucket.travel_simulation_bucket.bucket
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.c23_travel_simulator_attach_s3_policy,
    aws_iam_role_policy_attachment.c23_travel_simulator_attach_logs_policy
  ]
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "c23_travel_simulator_simulation_logs" {
  name              = "/aws/lambda/${aws_lambda_function.c23_travel_simulator_simulation.function_name}"
  retention_in_days = 7
}

# Outputs
output "ecr_repository_url_simulation" {
  description = "ECR repository URL for pushing Docker images"
  value       = aws_ecr_repository.c23_travel_simulator_simulation.repository_url
}

output "lambda_function_name_simulation" {
  description = "Lambda function name"
  value       = aws_lambda_function.c23_travel_simulator_simulation.function_name
}

output "lambda_function_arn_simulation" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.c23_travel_simulator_simulation.arn
}

output "ecr_repository_name_simulation" {
  description = "ECR repository name"
  value       = aws_ecr_repository.c23_travel_simulator_simulation.name
}
