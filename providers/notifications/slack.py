import json
import urllib3


class SlackNotifier:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
        self.http = urllib3.PoolManager()

    def send(self, message):
        if not self.webhook_url:
            raise ValueError("SLACK_WEBHOOK_URL is missing.")

        response = self.http.request(
            "POST",
            self.webhook_url,
            body=json.dumps({"text": message}),
            headers={"Content-Type": "application/json"},
        )

        if response.status >= 400:
            raise RuntimeError(
                f"Slack notification failed with HTTP {response.status}"
            )
