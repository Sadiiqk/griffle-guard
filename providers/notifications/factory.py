import os

from providers.notifications.console import ConsoleNotifier
from providers.notifications.slack import SlackNotifier
from providers.notifications.teams import TeamsNotifier


def get_notifier():
    provider = os.getenv("NOTIFICATION_PROVIDER", "console").lower()

    if provider == "slack":
        webhook_url = os.getenv("SLACK_WEBHOOK_URL")

        if not webhook_url:
            raise ValueError(
                "SLACK_WEBHOOK_URL must be set when NOTIFICATION_PROVIDER=slack"
            )

        return SlackNotifier(webhook_url)

    if provider == "teams":
        webhook_url = os.getenv("TEAMS_WEBHOOK_URL")

        if not webhook_url:
            raise ValueError(
                "TEAMS_WEBHOOK_URL must be set when NOTIFICATION_PROVIDER=teams"
            )

        return TeamsNotifier(webhook_url)

    if provider == "console":
        return ConsoleNotifier()

    raise ValueError(
        f"Unsupported notification provider: {provider}"
    )
