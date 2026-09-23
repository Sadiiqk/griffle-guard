terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

variable "central_griffleguard_role_arn" {
  type        = string
  description = "ARN of the central Griffle-Guard Lambda execution role that may assume this role"
}

variable "member_scan_role_name" {
  type        = string
  description = "Name of the read-only role created in the member AWS account"
  default     = "GriffleGuardReadOnlyRole"
}

resource "aws_iam_role" "griffleguard_read_only" {
  name = var.member_scan_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = var.central_griffleguard_role_arn
        }
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "griffleguard_read_only" {
  name = "GriffleGuardReadOnlySecurityScan"
  role = aws_iam_role.griffleguard_read_only.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:ListAllMyBuckets",
          "s3:GetBucketPublicAccessBlock",
          "ec2:DescribeSecurityGroups"
        ]
        Resource = "*"
      }
    ]
  })
}

output "member_scan_role_arn" {
  description = "ARN of the member-account role Griffle-Guard can assume"
  value       = aws_iam_role.griffleguard_read_only.arn
}
