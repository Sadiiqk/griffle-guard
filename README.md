# 🛡️ Griffle-Guard: AI-Powered Security Sentry
**An Autonomous Incident Response System driven by Google Gemini 2.5 Flash**

## 🇸🇪 Overview
Griffle-Guard is a cloud-native security tool developed in Stockholm, Sweden. It monitors system logs in real-time and uses Generative AI to perform zero-shot forensic analysis on suspicious activity.

### 🚀 Features
- **AI Triage:** Analyzes log entries (like unauthorized North Korean logins) using `gemini-2.0-flash`.
- **Auto-Defense:** Automatically triggers `gcloud` CLI commands to revoke sessions or adjust firewall rules upon threat detection.
- **Containerized:** Fully Dockerized for deployment across any cloud environment.
- **GitOps Ready:** Integrated with GitHub for incident tracking and version control.

## 🛠️ Tech Stack
- **Language:** Python 3.12
- **AI Model:** Google Vertex AI (Gemini 2.5 Flash)
- **Infrastructure:** Google Cloud Platform (GCP)
- **Containerization:** Docker

## 📦 How to Run
1. Clone the repo: `git clone https://github.com/sadiiqk/griffle-guard.git`
2. Set up your `.env` with your GCP Project ID.
3. Run the sentry: `python3 guard.py`
