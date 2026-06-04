# ECR Repository for the Docker image
resource "aws_ecr_repository" "c23_travel_simulator_choropleth_pipeline" {
  name                 = "c23-travel-simulator-choropleth-pipeline"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

# IAM Role for Lambda execution
resource "aws_iam_role" "c23_travel_simulator_choropleth_lambda_role" {
  name = "c23-travel-simulator-choropleth-lambda-role"

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
resource "aws_iam_policy" "c23_travel_simulator_choropleth_s3_policy" {
  name = "c23-travel-simulator-choropleth-s3-policy"

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
resource "aws_iam_policy" "c23_travel_simulator_choropleth_logs_policy" {
  name = "c23-travel-simulator-choropleth-logs-policy"

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
resource "aws_iam_role_policy_attachment" "c23_travel_simulator_choropleth_attach_s3_policy" {
  role       = aws_iam_role.c23_travel_simulator_choropleth_lambda_role.name
  policy_arn = aws_iam_policy.c23_travel_simulator_choropleth_s3_policy.arn
}

# Attach logs policy to Lambda role
resource "aws_iam_role_policy_attachment" "c23_travel_simulator_choropleth_attach_logs_policy" {
  role       = aws_iam_role.c23_travel_simulator_choropleth_lambda_role.name
  policy_arn = aws_iam_policy.c23_travel_simulator_choropleth_logs_policy.arn
}

# Lambda Function using Docker image from ECR
resource "aws_lambda_function" "c23_travel_simulator_choropleth_pipeline" {
  function_name = "c23-travel-simulator-choropleth-pipeline"
  role          = aws_iam_role.c23_travel_simulator_choropleth_lambda_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.c23_travel_simulator_choropleth_pipeline.repository_url}:latest"

  image_config {
    entry_point = ["/lambda-entrypoint.sh"]
    command     = ["choropleth_pipline.lambda_handler"]
  }

  memory_size = 3008 # Maximum memory for geospatial processing
  timeout     = 900  # 15 minutes for choropleth generation

  architectures = ["x86_64"]

  depends_on = [
    aws_iam_role_policy_attachment.c23_travel_simulator_choropleth_attach_s3_policy,
    aws_iam_role_policy_attachment.c23_travel_simulator_choropleth_attach_logs_policy
  ]
}
