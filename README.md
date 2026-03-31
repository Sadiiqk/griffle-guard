# Griffle-Guard

Griffle-Guard is a Python-based cloud security monitoring project that checks AWS S3 buckets for risky public access settings, sends Slack alerts, and can optionally use Google Vertex AI (Gemini) to generate short human-readable risk summaries.

This project includes two related components:

- **Local / container scanner** using `guard.py`
- **AWS serverless scanner** using `lambda_function.py` and Terraform

---

## Features

- Scans AWS S3 buckets for missing or weak public access block settings
- Sends alerts to Slack when a potentially exposed bucket is found
- Optional AI-generated security summary using Google Vertex AI / Gemini
- AWS Lambda deployment with scheduled execution using EventBridge
- Infrastructure provisioning with Terraform
- Optional Docker support for local execution

---

## Project Structure

```bash
.
├── Dockerfile
├── README.md
├── guard.py
├── lambda_function.py
├── main.tf
├── requirements.txt
└── response.json
