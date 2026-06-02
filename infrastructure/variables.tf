variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "eu-west-2"
}
variable "aws_access_key_id" {
  type      = string
  sensitive = true
}

variable "aws_secret_access_key" {
  type      = string
  sensitive = true
}

variable "GOOGLE_CLOUD_PROJECT" {
  description = "Google Cloud project ID for the dashboard"
  type        = string
}

variable "OPENAI_API_KEY" {
  description = "OpenAI API key for the dashboard"
  type        = string
  sensitive   = true
}

variable "S3_BUCKET_NAME" {
  description = "Name of the S3 bucket for the dashboard"
  type        = string
}

variable "GOOGLE_APPLICATION_CREDENTIALS_JSON"{
  description = "Google Cloud service account credentials in JSON format for the dashboard"
  type        = string
  sensitive   = true
}