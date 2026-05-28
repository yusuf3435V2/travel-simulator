terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "eu-west-2"
}

resource "aws_s3_bucket" "travel_simulation_bucket" {
  bucket = "c23-travel-simulation-bucket"

  tags = {
    Project = "Travel Simulation"
    Purpose = "Shared project data and outputs"
  }
}

resource "aws_s3_bucket_versioning" "versioning" {
  bucket = aws_s3_bucket.travel_simulation_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "public_access" {
  bucket = aws_s3_bucket.travel_simulation_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "raw_folder" {
  bucket  = aws_s3_bucket.travel_simulation_bucket.id
  key     = "raw/"
  content = ""
}

resource "aws_s3_object" "processed_folder" {
  bucket  = aws_s3_bucket.travel_simulation_bucket.id
  key     = "processed/"
  content = ""
}

resource "aws_s3_object" "outputs_folder" {
  bucket  = aws_s3_bucket.travel_simulation_bucket.id
  key     = "outputs/"
  content = ""
}