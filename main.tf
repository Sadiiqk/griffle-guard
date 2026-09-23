variable "ai_provider" {
  type        = string
  description = "AI provider to use: none, gemini, or bedrock"
  default     = "bedrock"
}

variable "notification_provider" {
  type        = string
  description = "Notification provider to use: console, slack, or teams"
  default     = "console"
}

variable "slack_webhook_url" {
  type        = string
  description = "Slack Webhook URL"
  default     = ""
  sensitive   = true
}

variable "teams_webhook_url" {
  type        = string
  description = "Microsoft Teams Webhook URL"
  default     = ""
  sensitive   = true
}

variable "google_cloud_project" {
  type        = string
  description = "Google Cloud project used by Gemini"
  default     = ""
}

variable "google_cloud_location" {
  type        = string
  description = "Google Cloud region used by Gemini"
  default     = "europe-west1"
}

variable "gemini_model" {
  type        = string
  description = "Gemini model name"
  default     = "gemini-2.5-flash"
}

variable "bedrock_model_id" {
  type        = string
  description = "AWS Bedrock model ID"
  default     = "eu.amazon.nova-micro-v1:0"
}


resource "aws_iam_role" "sentry_role" {
  name = "GriffleGuard-Sentry-Role-v2"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"

        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}


resource "aws_iam_role_policy" "sentry_permissions" {
  name = "SentrySecurityAccess"
  role = aws_iam_role.sentry_role.id

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect = "Allow"

        Action = [
          "s3:ListAllMyBuckets",
          "s3:GetBucketPublicAccessBlock",
          "ec2:DescribeSecurityGroups",
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]

        Resource = "*"
      }
    ]
  })
}


resource "aws_lambda_function" "griffleguard" {
  filename         = "lambda_function_payload.zip"
  function_name    = "GriffleGuard-Sentry-v2"
  role             = aws_iam_role.sentry_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  timeout          = 60
  source_code_hash = filebase64sha256("lambda_function_payload.zip")

  environment {
    variables = {
      AI_PROVIDER           = var.ai_provider
      NOTIFICATION_PROVIDER = var.notification_provider

      SLACK_WEBHOOK_URL = var.slack_webhook_url
      TEAMS_WEBHOOK_URL = var.teams_webhook_url

      GOOGLE_CLOUD_PROJECT  = var.google_cloud_project
      GOOGLE_CLOUD_LOCATION = var.google_cloud_location
      GEMINI_MODEL          = var.gemini_model

      BEDROCK_MODEL_ID = var.bedrock_model_id
    }
  }
}


resource "aws_cloudwatch_event_rule" "daily_scan" {
  name                = "GriffleGuard-Daily-Scan"
  schedule_expression = "rate(1 day)"
}


resource "aws_cloudwatch_event_target" "run_lambda" {
  rule      = aws_cloudwatch_event_rule.daily_scan.name
  target_id = "TriggerGriffleGuard"
  arn       = aws_lambda_function.griffleguard.arn
}


resource "aws_lambda_permission" "allow_cloudwatch" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.griffleguard.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_scan.arn
}
