# 🛡️ Griffle-Guard: Multi-Cloud AI Security Sentry

## 📖 Overview
Griffle-Guard is a custom **SOAR (Security Orchestration, Automation, and Response)** tool built in Python. It acts as an automated security sentry that bridges Google Cloud and AWS. 

It continuously monitors local infrastructure and AWS environments (like S3 buckets) for misconfigurations or threats. When an anomaly is detected, it sends the event data to **Google Vertex AI (Gemini 1.5)** to perform zero-shot vulnerability analysis and generate a detailed Incident Response plan.

## ✨ Key Features
* **Multi-Cloud Integration:** Uses `boto3` to securely interface with AWS while running inside a Google Cloud Linux environment.
* **AI-Driven Triage:** Leverages Google's Gemini LLM to instantly analyze security logs and classify severity (e.g., catching Public S3 buckets).
* **Zero-Trust Credential Management:** Implements `python-dotenv` to ensure AWS Access Keys are securely loaded into memory and completely hidden from version control.
* **Automated Patrol Loop:** Runs continuously to monitor log files and cloud infrastructure in real-time.

## 🛠️ Tech Stack
* **Language:** Python 3
* **Cloud Platforms:** AWS (IAM, S3), Google Cloud Platform (Vertex AI, Cloud Shell)
* **Libraries:** `boto3`, `google-cloud-aiplatform`, `python-dotenv`
