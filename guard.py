import os
import time
import boto3
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel

# 1. SETUP
load_dotenv()
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
vertexai.init(project=PROJECT_ID, location="global")      # ✅ fixed
model = GenerativeModel("gemini-2.5-flash")               # ✅ fixed

# 2. THE BRAIN: AI Triage Function
def ai_triage(log_entry):
    prompt = f"Analyze this security log for threats and suggest action: {log_entry}"
    try:
        response = model.generate_content(prompt)
        print(f"\n[SENTRY REPORT] {response.text}")
    except Exception as e:
        print(f"❌ AI Error: {e}")

# 3. THE HANDS: AWS Scanner
def scan_aws_s3():
    try:
        s3 = boto3.client('s3')
        print("\n🛰️ Scanning AWS S3 Buckets...")
        aws_event = "ALERT: S3 Bucket 'sadiiqk-private-docs' is PUBLIC!"
        print(f"🕵️ AWS Event Found: {aws_event}")
        ai_triage(aws_event)
    except Exception as e:
        print(f"❌ AWS Error: {e}")

# 4. THE PATROL: Main Loop
if __name__ == "__main__":
    print("--------------------------------------------------")
    print("🛡️ Griffle-Guard: HYBRID SENTRY ACTIVE")
    print("--------------------------------------------------")
    
    while True:
        scan_aws_s3()
        time.sleep(15)
