import os

import boto3

from providers.notifications.console import ConsoleNotifier
from providers.notifications.slack import SlackNotifier
from providers.notifications.teams import TeamsNotifier


def get_secret_value(env_var_name):
    secret_arn = os.getenv(env_var_name)

    if not secret_arn:
        raise ValueError(
            f"{env_var_name} must be set for the selected notification provider"
        )

    response = boto3.client("secretsmanager").get_secret_value(
        SecretId=secret_arn
    )

    secret_value = response.get("SecretString")

    if not secret_value:
        raise ValueError(
            f"Secret {secret_arn} does not contain a SecretString value"
        )

    return secret_value


def get_notifier():
    provider = os.getenv("NOTIFICATION_PROVIDER", "console").lower()

    if provider == "slack":
        webhook_url = get_secret_value("SLACK_WEBHOOK_SECRET_ARN")
        return SlackNotifier(webhook_url)

    if provider == "teams":
        webhook_url = get_secret_value("TEAMS_WEBHOOK_SECRET_ARN")
        return TeamsNotifier(webhook_url)

    if provider == "console":
        return ConsoleNotifier()

    raise ValueError(
        f"Unsupported notification provider: {provider}"
    )
