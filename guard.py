import os
import time
import subprocess
import vertexai
from vertexai.generative_models import GenerativeModel

# Initialize Google Cloud
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
# We'll use us-central1 as our stable "Main Hub" for the AI Brain
vertexai.init(project=PROJECT_ID, location="us-central1")
model = GenerativeModel("gemini-2.5-flash")

def auto_defend(verdict):
    """
    The 'Action' phase. If the AI finds a threat, we take defensive steps.
    """
    if "THREAT" in verdict.upper():
        print("🚨 [ACTION TAKEN] AI confirmed threat. Revoking session...")
        try:
            # Running a safe command to demonstrate the 'Kill Switch' capability
            subprocess.run(["gcloud", "config", "list"], check=True)
            print("✅ Defense measures deployed successfully.")
        except Exception as e:
            print(f"❌ Failed to deploy defense: {e}")

def ai_triage(log_data):
    prompt = f"""
    You are a Senior Cyber Security Analyst. Analyze this log.
    If it's suspicious, start with '🚨 THREAT:'. 
    If it's normal, start with '✅ SAFE:'.
    Keep the explanation to one sentence.
    
    LOG: {log_data}
    """
    try:
        response = model.generate_content(prompt)
        verdict = response.text.strip()
        print(f"\n[SENTRY REPORT] {verdict}")
        
        # Trigger the defense system if needed
        auto_defend(verdict)
    except Exception as e:
        print(f"Error calling AI: {e}")

if __name__ == "__main__":
    FILENAME = "events.log"
    print(f"🛡️ Griffle-Guard is now PATROLLING {FILENAME}...")
    print("💡 (Test: Open a new tab and type: echo 'your log' >> events.log)")

    # Ensure the file exists before we try to open it
    if not os.path.exists(FILENAME):
        open(FILENAME, 'a').close()

    # The 'Infinite Patrol' Loop
    with open(FILENAME, "r") as f:
        # Move to the end of the file so we only see NEW logs
        f.seek(0, 2)
        while True:
            line = f.readline()
            if not line:
                time.sleep(1)  # Wait 1 second for activity
                continue
            
            print(f"\n🕵️ New Activity Detected: {line.strip()}")
            ai_triage(line)
