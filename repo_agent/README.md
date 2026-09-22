# AWS Repository Agent

This Lambda function reads the configured GitHub repository, asks the OpenAI
Responses API for a structured set of text-file edits, writes those edits to a
new `agent/...` branch, and opens a **draft pull request**.

It does not:

- push directly to `main`
- merge pull requests
- execute repository code
- read arbitrary repositories
- place API credentials in Terraform state or Lambda environment variables

## Secret format

After Terraform creates `griffle-guard-repo-agent`, set its value in AWS
Secrets Manager:

```json
{
  "openai_api_key": "your OpenAI API key",
  "github_token": "your fine-grained GitHub token"
}
```

Limit the GitHub token to `Sadiiqk/griffle-guard` with:

- Contents: Read and write
- Pull requests: Read and write
- Metadata: Read

Use an expiry date and rotate the token regularly.

## Deploy

```bash
cd infra/repo-agent
terraform init
terraform plan
terraform apply
```

Populate the secret in the AWS console, then invoke the function:

```bash
aws lambda invoke \
  --function-name griffle-guard-repo-agent \
  --cli-binary-format raw-in-base64-out \
  --payload '{"task":"Fix the failing tests with the smallest safe change"}' \
  response.json

cat response.json
```

Test the analysis without creating a branch or PR:

```bash
aws lambda invoke \
  --function-name griffle-guard-repo-agent \
  --cli-binary-format raw-in-base64-out \
  --payload '{"task":"Review the repository for correctness issues","dry_run":true}' \
  response.json
```

Always review the draft PR and its CI results before merging.
