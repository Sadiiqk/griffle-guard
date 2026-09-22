variable "aws_region" {
  type        = string
  description = "AWS region for the repository agent"
  default     = "eu-north-1"
}

variable "github_repository" {
  type        = string
  description = "The only GitHub repository the agent may modify"
  default     = "Sadiiqk/griffle-guard"
}

variable "openai_model" {
  type        = string
  description = "OpenAI model used to propose repository edits"
  default     = "gpt-6-astra"
}
