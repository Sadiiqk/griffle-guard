# 🛡️ Griffle-Guard: AI-Powered Security Sentry (v1.0)
Built with 🇸🇪 in Stockholm | Powered by Google Gemini 2.5 Flash

Griffle-Guard is a cloud-native **Intrusion Detection & Automated Response (IDAR)** system. It uses Large Language Models to analyze system logs in real-time and execute defensive actions against detected threats.

## 🚀 Features
* **Real-time Log Tailing:** Monitors `events.log` for instant activity detection.
* **AI Forensic Analysis:** Uses Gemini 2.5 to identify "Impossible Travel" and high-risk geopolitical logins.
* **Automated Defense:** Triggers `gcloud` infrastructure commands to mitigate threats immediately.
* **GitOps Integration:** Automatically logs security incidents as GitHub Issues.

## 🛠️ Technical Stack
* **Language:** Python 3.12
* **AI:** Vertex AI (Gemini 2.5 Flash)
* **Cloud:** Google Cloud Platform (GCP)
* **Version Control:** Git & GitHub

## 📝 How to Run
1. Initialize Google Cloud ADC.
2. Run `python3 guard.py`.
3. Monitor `events.log` for automated AI verdicts.

---
*Created by sadiiqk as a demonstration of AI-driven Cybersecurity.*
