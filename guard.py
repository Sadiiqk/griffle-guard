import os
import json
import boto3
import requests
import vertexai
from vertexai.generative_models import GenerativeModel

# 1. AWS SECRETS MANAGER SETUP (The Vault)
session = boto3.session.Session()
# Change 'us-east-1' if you stored your secret in a different region!
secrets_client = session.client(service_name='secretsmanager', region_name="eu-north-1")

def get_secrets():
    secret_name = "griffle/sentry/secrets"
    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except Exception as e:
        print(f"⚠️ Warning: Could not pull from AWS Vault ({e}). Falling back to local env.")
        return {}

# Load the secrets
aws_secrets = get_secrets()
SLACK_URL = aws_secrets.get('SLACK_WEBHOOK_URL')

# 2. GOOGLE GEMINI SETUP (The Brain)
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
vertexai.init(project=PROJECT_ID, location="eu-north2") 
model = GenerativeModel("gemini-2.5-flash")

# 3. NOTIFICATION LOGIC (The Voice)
def send_to_slack(text):
    if SLACK_URL:
        payload = {"text": text}
        requests.post(SLACK_URL, json=payload)
    else:
        print("❌ Error: No Slack URL found.")

# 4. THE BRAIN: AI Triage Function
def ai_triage(bucket_name):
    print(f"🕵️ Analyzing: {bucket_name}")
    prompt = f"Analyze the security risk of an AWS S3 bucket named '{bucket_name}' being PUBLIC. Give a 2-sentence warning and a severity level."
    
    try:
        response = model.generate_content(prompt)
        report = response.text
        print(f"\n[SENTRY REPORT] {report}")
        
        # Send the AI's findings to Slack!
        alert_msg = f"🚨 *SENTRY ALERT*\n*Bucket:* {bucket_name}\n*AI Analysis:* {report}"
        send_to_slack(alert_msg)
        
    except Exception as e:
        print(f"❌ Gemini Error: {e}")

# 5. THE PATROL: Scan AWS
s3 = boto3.resource('s3')
s3_client = boto3.client('s3')

print("-" * 50)
print("🛡️ Griffle-Guard: VAULT-POWERED SENTRY ACTIVE")
print("-" * 50)

for bucket in s3.buckets.all():
    name = bucket.name
    try:
        # Check if bucket is public
        status = s3_client.get_public_access_block(Bucket=name)
        is_public = not status['PublicAccessBlockConfiguration']['BlockPublicAll']
    except:
        is_public = True # If no block settings, assume it might be public

    if is_public:
        ai_triage(name)

print("\n✅ Scan Complete.")
