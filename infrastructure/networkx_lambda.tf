# ECR Repository for the Docker image
resource "aws_ecr_repository" "networkx_pipeline" {
  name                 = "c23-travel-simulation-networkx-pipeline"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

# IAM Role for Lambda execution
resource "aws_iam_role" "c23_networkx_lambda_role" {
  name = "c23-networkx-pipeline-lambda-role"

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
resource "aws_iam_policy" "s3_policy" {
  name = "c23-networkx-s3-policy"

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
          "arn:aws:s3:::c23-travel-simulation-bucket",
          "arn:aws:s3:::c23-travel-simulation-bucket/*"
        ]
      }
    ]
  })
}

# IAM Policy for Lambda to write logs
resource "aws_iam_policy" "lambda_logs_policy" {
  name = "c23-networkx-logs-policy"

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
resource "aws_iam_role_policy_attachment" "attach_s3_policy" {
  role       = aws_iam_role.c23_networkx_lambda_role.name
  policy_arn = aws_iam_policy.s3_policy.arn
}

# Attach logs policy to Lambda role
resource "aws_iam_role_policy_attachment" "attach_logs_policy" {
  role       = aws_iam_role.c23_networkx_lambda_role.name
  policy_arn = aws_iam_policy.lambda_logs_policy.arn
}

# Lambda Function using Docker image from ECR
resource "aws_lambda_function" "networkx_pipeline" {
  function_name = "c23-networkx-pipeline"
  role          = aws_iam_role.c23_networkx_lambda_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.networkx_pipeline.repository_url}:latest"
  
  image_config {
    entry_point = ["/lambda-entrypoint.sh"]
    command     = ["create_stations_network.lambda_handler"]
  }

  memory_size = 3008  # Maximum memory for better performance
  timeout     = 900   # 15 minutes for network creation

  architectures = ["x86_64"]

  depends_on = [
    aws_iam_role_policy_attachment.attach_s3_policy,
    aws_iam_role_policy_attachment.attach_logs_policy
  ]
}

# EventBridge Rule to trigger Lambda on schedule
resource "aws_cloudwatch_event_rule" "networkx_schedule" {
  name                = "c23-networkx-pipeline-schedule"
  description         = "Trigger networkx pipeline daily"
  schedule_expression = "cron(0 2 * * ? *)"  # Daily at 2 AM UTC
}

resource "aws_cloudwatch_event_target" "networkx_lambda" {
  rule      = aws_cloudwatch_event_rule.networkx_schedule.name
  target_id = "c23NetworkxLambda"
  arn       = aws_lambda_function.networkx_pipeline.arn

  depends_on = [aws_lambda_permission.allow_eventbridge]
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.networkx_pipeline.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.networkx_schedule.arn
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "networkx_logs" {
  name              = "/aws/lambda/${aws_lambda_function.networkx_pipeline.function_name}"
  retention_in_days = 7
}

# Outputs
output "ecr_repository_url" {
  description = "ECR repository URL for pushing Docker images"
  value       = aws_ecr_repository.networkx_pipeline.repository_url
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.networkx_pipeline.function_name
}

output "lambda_function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.networkx_pipeline.arn
}

output "ecr_repository_name" {
  description = "ECR repository name"
  value       = aws_ecr_repository.networkx_pipeline.name
}
