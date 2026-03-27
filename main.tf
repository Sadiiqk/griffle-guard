# --- 1. THE VARIABLE SLOTS (This fixes the "undeclared" error!) ---
variable "gemini_api_key" {
  type        = string
  description = "Google Gemini API Key"
}

variable "slack_webhook_url" {
  type        = string
  description = "Slack Webhook URL"
}

# --- 2. THE PERMISSIONS (IAM Role) ---
resource "aws_iam_role" "sentry_role" {
  name = "GriffleGuard-Sentry-Role-v2"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "sentry_permissions" {
  name = "SentryS3Access"
  role = aws_iam_role.sentry_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:ListAllMyBuckets",
        "s3:GetBucketPublicAccessBlock",
        "s3:PutBucketPublicAccessBlock",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
      Resource = "*"
    }]
  })
}

# --- 3. THE BRAIN (Lambda Function) ---
resource "aws_lambda_function" "griffleguard" {
  # This must match the name of the zip you created (lambda_function_payload.zip)
  filename      = "lambda_function_payload.zip" 
  function_name = "GriffleGuard-Sentry-v2"
  role          = aws_iam_role.sentry_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.12"
  timeout       = 60

  environment {
    variables = {
      GEMINI_API_KEY    = var.gemini_api_key
      SLACK_WEBHOOK_URL = var.slack_webhook_url
    }
  }
}

# --- 4. THE SCHEDULE (EventBridge) ---
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