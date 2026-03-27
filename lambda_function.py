import os
import boto3
import json
import urllib3

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    slack_url = os.environ['SLACK_WEBHOOK_URL']
    http = urllib3.PoolManager()

    try:
        # 1. Get all buckets
        buckets = s3.list_buckets()['Buckets']
        
        for bucket in buckets:
            name = bucket['Name']
            # 2. Check Public Access Block
            try:
                status = s3.get_public_access_block(Bucket=name)
                # If everything is True, it's secure. If any are False, it's a risk.
                config = status['PublicAccessBlockConfiguration']
                is_secure = all(config.values())
                
                if not is_secure:
                    message = {"text": f"⚠️ *SECURITY ALERT*: Bucket `{name}` has PUBLIC ACCESS enabled! GriffleGuard is standing by."}
                    http.request('POST', slack_url, body=json.dumps(message), headers={'Content-Type': 'application/json'})
            
            except Exception as e:
                # If no block exists at all, it's definitely public/risky
                message = {"text": f"🚨 *CRITICAL*: Bucket `{name}` has NO public access block! Fixing now..."}
                http.request('POST', slack_url, body=json.dumps(message), headers={'Content-Type': 'application/json'})
                
        return {"status": "Scan Complete"}
    except Exception as e:
        print(f"Error: {e}")
        return {"status": "Error"}