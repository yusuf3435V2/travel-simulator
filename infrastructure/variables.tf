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
