# 🛡️ Griffle-Guard: Multi-Cloud AI Security Sentry (SOAR)

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-IaC-purple?logo=terraform&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-Cloud-FF9900?logo=amazonaws&logoColor=white)
![GCP](https://img.shields.io/badge/GCP-Vertex_AI-4285F4?logo=googlecloud&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?logo=docker&logoColor=white)

## 📖 Overview

**Griffle-Guard** is a custom Security Orchestration, Automation, and Response (SOAR) tool built in Python. It acts as an automated security sentry that bridges **Google Cloud** and **AWS** to provide full-spectrum threat detection and response.

It continuously monitors local infrastructure and AWS environments (specifically targeting S3 misconfigurations and public exposure). When an anomaly is detected, it leverages **Google Vertex AI (Gemini 2.5)** to perform zero-shot vulnerability analysis, generating detailed Incident Response plans and dispatching real-time alerts to **Slack**.

---

## 🏗️ Architecture & Modules

Griffle-Guard operates using two distinct operational modes:

### 1. The Core AI SOAR Engine (Containerized / Local)
* **Log & Environment Monitoring:** Runs a continuous patrol loop to ingest logs and cloud state data.
* **AI-Driven Triage:** Sends event data to Google Vertex AI via `google-cloud-aiplatform` to classify severity and draft mitigation strategies.
* **Zero-Trust Secrets:** Uses `python-dotenv` and Docker environment variables to ensure AWS Access Keys and GCP credentials remain strictly out of version control.

### 2. The Cloud-Native Sentry (AWS Serverless via Terraform)
* **Infrastructure as Code:** The AWS footprint is deployed 100% via Terraform.
* **Automated Auditing:** An AWS Lambda function (`boto3`) is scheduled by Amazon EventBridge to run every 24 hours, actively querying the `PublicAccessBlock` configuration of all S3 buckets in the region.
* **Instant Alerting:** If a bucket is found exposed, the Lambda function immediately fires an `application/json` payload to a Slack Webhook.

---

## ✨ Key Features

* **Multi-Cloud Integration:** Securely interfaces with AWS resources while utilizing Google Cloud's LLM capabilities.
* **Infrastructure as Code (IaC):** Repeatable, immutable AWS deployment via `main.tf`.
* **Serverless Efficiency:** The AWS Sentry component costs $0 when idle.
* **AI Vulnerability Analysis:** Gemini 1.5 instantly translates raw AWS configuration errors into human-readable security alerts.
* **Automated Slack Integration:** Real-time visibility for the Security Operations Center (SOC).

---

## 🛠️ Tech Stack

* **Language:** Python 3.12
* **Cloud Platforms:** * AWS (Lambda, EventBridge, S3, IAM)
  * Google Cloud Platform (Vertex AI, Cloud Shell)
* **Infrastructure as Code:** Terraform
* **Libraries:** `boto3`, `google-cloud-aiplatform`, `python-dotenv`, `urllib3`
* **Containerization:** Docker (`Dockerfile` included for the SOAR engine)

---

## 🚀 Deployment Guide

### Part A: Deploying the AWS Serverless Sentry (Terraform)
1. Ensure you have [Terraform](https://developer.hashicorp.com/terraform/downloads) installed and your AWS CLI configured.
2. Package the Lambda logic:
   ```bash
   rm -f lambda_function_payload.zip
   zip lambda_function_payload.zip lambda_function.py
