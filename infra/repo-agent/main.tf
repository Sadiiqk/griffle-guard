terraform {
  required_version = ">= 1.6.0"

  required_providers {
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "aws_secretsmanager_secret" "repo_agent" {
  name                    = "griffle-guard-repo-agent"
  description             = "OpenAI and GitHub credentials for the PR-only repository agent"
  recovery_window_in_days = 7
}

data "archive_file" "repo_agent" {
  type        = "zip"
  source_dir  = "\${path.module}/../../repo_agent"
  output_path = "\${path.module}/repo_agent.zip"
}

resource "aws_iam_role" "repo_agent" {
  name = "griffle-guard-repo-agent"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "sts:AssumeRole"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "basic_execution" {
  role       = aws_iam_role.repo_agent.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "read_agent_secret" {
  name = "read-repository-agent-secret"
  role = aws_iam_role.repo_agent.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = aws_secretsmanager_secret.repo_agent.arn
    }]
  })
}

resource "aws_cloudwatch_log_group" "repo_agent" {
  name              = "/aws/lambda/griffle-guard-repo-agent"
  retention_in_days = 30
}

resource "aws_lambda_function" "repo_agent" {
  function_name    = "griffle-guard-repo-agent"
  description      = "Creates draft pull requests for Griffle-Guard"
  filename         = data.archive_file.repo_agent.output_path
  source_code_hash = data.archive_file.repo_agent.output_base64sha256
  role             = aws_iam_role.repo_agent.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  timeout          = 120
  memory_size      = 512

  environment {
    variables = {
      SECRET_ID         = aws_secretsmanager_secret.repo_agent.id
      GITHUB_REPOSITORY = var.github_repository
      OPENAI_MODEL      = var.openai_model
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.basic_execution,
    aws_iam_role_policy.read_agent_secret,
    aws_cloudwatch_log_group.repo_agent,
  ]
}

resource "aws_lambda_function_url" "repo_agent" {
  function_name      = aws_lambda_function.repo_agent.function_name
  authorization_type = "AWS_IAM"
}
