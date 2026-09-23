import json
import os

import boto3


class BedrockProvider:
    def __init__(self):
        self.model_id = os.getenv(
            "BEDROCK_MODEL_ID",
            "eu.amazon.nova-micro-v1:0",
        )

        self.client = boto3.client(
            "bedrock-runtime",
            region_name=os.getenv("AWS_REGION", "eu-north-1"),
        )

    def analyze(self, finding):
        prompt = (
            "You are a cloud security assistant. "
            "Explain this security finding in simple language, "
            "include the risk, and give one short recommended action.\n\n"
            f"Finding: {finding}"
        )

        response = self.client.converse(
            modelId=self.model_id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "text": prompt
                        }
                    ],
                }
            ],
        )

        return response["output"]["message"]["content"][0]["text"]
