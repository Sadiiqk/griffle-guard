output "function_name" {
  description = "Lambda function to invoke with a repository task"
  value       = aws_lambda_function.repo_agent.function_name
}

output "function_url" {
  description = "IAM-protected function URL"
  value       = aws_lambda_function_url.repo_agent.function_url
}

output "secret_name" {
  description = "Populate this secret after deployment"
  value       = aws_secretsmanager_secret.repo_agent.name
}
