# Griffle-Guard

Griffle-Guard is an AWS cloud security monitoring project that scans for common security risks, explains findings with AI, and can send findings to different notification providers.

The main deployment path uses **AWS Lambda + EventBridge + Terraform**. Griffle-Guard currently scans:

- Amazon S3 buckets for weak or missing Public Access Block settings
- EC2 Security Groups for risky internet exposure
  - SSH (port 22) open to `0.0.0.0/0`
  - RDP (port 3389) open to `0.0.0.0/0`
  - rules that allow all traffic from `0.0.0.0/0`

Findings can be enriched with **Amazon Bedrock** and written to CloudWatch Logs. The project also includes optional notification providers for Slack and Microsoft Teams.

> Griffle-Guard is currently an MVP / learning and portfolio project. Test it in a non-production AWS account before using it in a production environment.

---

## How it works

```text
EventBridge schedule
        |
        v
AWS Lambda
        |
        +--> Scan S3 Public Access Block
        |
        +--> Scan EC2 Security Groups
        |
        v
Optional AI analysis
Amazon Bedrock / Gemini / none
        |
        v
Notification provider
CloudWatch console / Slack / Teams
```

By default, the current Terraform configuration uses:

```text
AI provider:           bedrock
Notification provider: console
AWS region:            eu-north-1
Bedrock model:         eu.amazon.nova-micro-v1:0
```

With the default configuration, findings are printed to the Lambda logs in Amazon CloudWatch.

---

## Project structure

```text
.
├── lambda_function.py
├── main.tf
├── providers/
│   ├── ai/
│   │   ├── bedrock.py
│   │   ├── factory.py
│   │   ├── gemini.py
│   │   └── none.py
│   └── notifications/
│       ├── console.py
│       ├── factory.py
│       ├── slack.py
│       └── teams.py
├── guard.py
├── Dockerfile
├── requirements.txt
└── README.md
```

`lambda_function.py` is the recommended AWS serverless scanner.

`guard.py` is an older local/container implementation and does not yet use the same provider architecture as the Lambda implementation.

---

## Prerequisites

You need:

- An AWS account
- AWS CLI
- Terraform
- Python 3
- `zip`
- AWS credentials or AWS IAM Identity Center / SSO access with enough permissions to create the resources in `main.tf`

Check that your AWS CLI session works:

```bash
aws sts get-caller-identity
```

If you use a named AWS CLI profile, export it before running Terraform:

```bash
export AWS_PROFILE=your-profile-name
```

---

## 1. Clone the repository

```bash
git clone https://github.com/Sadiiqk/griffle-guard.git
cd griffle-guard
```

---

## 2. Build the Lambda deployment package

Terraform expects a local file called:

```text
lambda_function_payload.zip
```

Create it with:

```bash
zip -r lambda_function_payload.zip lambda_function.py providers \
  -x "*/__pycache__/*" "*.pyc"
```

The ZIP file is intentionally ignored by Git and should not be committed.

You can inspect the package with:

```bash
unzip -l lambda_function_payload.zip
```

It should contain `lambda_function.py` and the `providers/` directory.

---

## 3. Initialize Terraform

```bash
terraform init
```

Validate the configuration:

```bash
terraform fmt
terraform validate
```

---

## 4. Review the Terraform plan

Always review the plan before deploying:

```bash
terraform plan
```

The current configuration creates resources such as:

- AWS Lambda function
- IAM role and inline policy
- EventBridge scheduled rule
- EventBridge target
- Lambda permission for EventBridge

---

## 5. Deploy Griffle-Guard

```bash
terraform apply
```

Review the plan and type:

```text
yes
```

when Terraform asks for confirmation.

The default Lambda function name is:

```text
GriffleGuard-Sentry-v2
```

The default EventBridge schedule runs the scanner once per day.

---

## 6. Test the Lambda manually

For the default Stockholm deployment:

```bash
aws lambda invoke \
  --function-name GriffleGuard-Sentry-v2 \
  --region eu-north-1 \
  response.json
```

Then inspect the Lambda response:

```bash
cat response.json
```

A successful invocation should return:

```json
{"status":"Scan Complete"}
```

`response.json` is a local test output file and should not be committed.

---

## 7. View security findings

The default notification provider is `console`, which means findings are written to CloudWatch Logs.

View recent findings with:

```bash
aws logs tail /aws/lambda/GriffleGuard-Sentry-v2 \
  --since 10m \
  --region eu-north-1
```

A finding can look like:

```text
HIGH: Security Group exposes SSH port 22 to the internet.

AI analysis:
The rule allows internet users to attempt SSH access.
Restrict the rule to trusted IP ranges.
```

---

## Configuration

Terraform exposes these main variables:

| Variable | Default | Purpose |
|---|---|---|
| `ai_provider` | `bedrock` | AI provider: `none`, `gemini`, or `bedrock` |
| `notification_provider` | `console` | Notification provider: `console`, `slack`, or `teams` |
| `bedrock_model_id` | `eu.amazon.nova-micro-v1:0` | Bedrock model/inference profile |
| `google_cloud_project` | empty | Google Cloud project used when Gemini is selected |
| `google_cloud_location` | `europe-west1` | Vertex AI location |
| `gemini_model` | `gemini-2.5-flash` | Gemini model name |
| `slack_webhook_url` | empty | Slack webhook URL |
| `teams_webhook_url` | empty | Microsoft Teams webhook URL |

### Disable AI

```bash
terraform apply -var='ai_provider=none'
```

### Use Amazon Bedrock

The repository currently defaults to Bedrock:

```bash
terraform apply \
  -var='ai_provider=bedrock' \
  -var='bedrock_model_id=eu.amazon.nova-micro-v1:0'
```

The Lambda execution role needs permission to invoke the selected Bedrock model, and the model/inference profile must be available to your AWS account and region.

### Use Slack

Users should provide their **own** Slack webhook. Never commit a webhook URL to Git.

Example:

```bash
terraform apply \
  -var='notification_provider=slack' \
  -var='slack_webhook_url=YOUR_WEBHOOK_URL'
```

For real environments, avoid placing secrets directly in shell history. Prefer a secure secret-management approach such as AWS Secrets Manager.

### Use Microsoft Teams

```bash
terraform apply \
  -var='notification_provider=teams' \
  -var='teams_webhook_url=YOUR_WEBHOOK_URL'
```

Webhook payload compatibility can vary depending on the Teams webhook/workflow type, so test the integration before relying on it for production alerts.

### Use Gemini

The code includes a Gemini provider using Google Vertex AI. It requires Google Cloud configuration and the `google-cloud-aiplatform` Python package.

The current simple Lambda ZIP build does **not** package that external dependency, so additional Lambda packaging or a Lambda layer/container image is required before using Gemini in the deployed Lambda.

---

## Security notes

This is a public repository. Do **not** commit credentials or secrets.

Never commit:

- AWS access keys
- passwords
- Slack or Teams webhook URLs
- API keys
- private keys
- `.env` files containing secrets
- Terraform variable files containing secrets
- Terraform state files containing sensitive values

The repository's `.gitignore` is designed to exclude common secret and generated files, but you should still review changes before every commit.

A useful check before pushing changes is:

```bash
gitleaks git . --verbose
```

If a secret is ever committed to a public repository, removing it from Git history is not enough. Revoke or rotate the exposed credential as well.

---

## Current limitations

Griffle-Guard is an MVP. Important limitations include:

- Security Group scanning currently checks IPv4 `0.0.0.0/0`, not IPv6 `::/0`
- S3 error handling should be made more specific so API/permission failures are not treated as missing Public Access Block
- an AI provider failure can currently interrupt the scan
- a notification provider failure can currently interrupt the scan
- Slack/Teams secrets are currently passed through Terraform/Lambda configuration rather than fetched from Secrets Manager
- the Gemini dependency is not included in the simple Lambda ZIP build
- automated unit/integration tests are still limited
- the older `guard.py` path is not yet fully aligned with the Lambda provider architecture

These are good areas for future contributions.

---

## Destroy the AWS resources

When you no longer want the deployment:

```bash
terraform destroy
```

Review the plan carefully and confirm before Terraform removes the resources it manages.

---

## Development workflow

Before committing changes:

```bash
python3 -m py_compile lambda_function.py
python3 -m py_compile providers/ai/*.py
python3 -m py_compile providers/notifications/*.py
terraform fmt
terraform validate
gitleaks git . --verbose
```

If the Lambda source changes, rebuild `lambda_function_payload.zip` before running Terraform. The Terraform configuration uses `source_code_hash`, so rebuilding the ZIP allows Terraform to detect Lambda code changes.

---

## Contributing

Issues and pull requests are welcome.

When contributing:

1. Do not include credentials or secrets.
2. Run the validation commands above.
3. Keep changes focused and easy to review.
4. Explain what changed and how it was tested in the pull request.

---

## Disclaimer

Griffle-Guard reports potentially risky configurations; it does not guarantee that an AWS environment is secure.

Review every finding before making infrastructure changes. Test changes in a non-production environment first.
