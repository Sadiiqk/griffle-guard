import os

import boto3
from botocore.exceptions import ClientError

from providers.ai.factory import get_ai_provider
from providers.ai.none import NoAIProvider
from providers.notifications.console import ConsoleNotifier
from providers.notifications.factory import get_notifier


def build_message(ai_provider, finding):
    try:
        analysis = ai_provider.analyze(finding)
    except Exception as error:
        print(f"AI analysis failed; using raw finding instead: {error}")
        return finding

    if analysis == finding:
        return finding

    return f"{finding}\n\nAI analysis:\n{analysis}"


def send_finding(notifier, ai_provider, finding):
    message = build_message(ai_provider, finding)

    try:
        notifier.send(message)
    except Exception as error:
        print(f"Notification failed; writing finding to logs instead: {error}")
        print(message)


def with_account_context(account_label, finding):
    if not account_label:
        return finding

    return f"[{account_label}] {finding}"


def scan_s3(s3, notifier, ai_provider, account_label=""):
    buckets = s3.list_buckets()["Buckets"]

    for bucket in buckets:
        name = bucket["Name"]

        try:
            status = s3.get_public_access_block(Bucket=name)
            config = status["PublicAccessBlockConfiguration"]
            is_secure = all(config.values())

            if not is_secure:
                finding = with_account_context(
                    account_label,
                    f"⚠️ HIGH: S3 bucket `{name}` may allow public access.",
                )
                send_finding(notifier, ai_provider, finding)

        except ClientError as error:
            error_code = error.response.get("Error", {}).get("Code", "Unknown")
            error_message = error.response.get("Error", {}).get(
                "Message",
                "No error message returned",
            )

            if error_code == "NoSuchPublicAccessBlockConfiguration":
                finding = with_account_context(
                    account_label,
                    (
                        f"🚨 CRITICAL: S3 bucket `{name}` has no "
                        f"Public Access Block configuration."
                    ),
                )
                send_finding(notifier, ai_provider, finding)
                continue

            print(
                f"S3 scan error for bucket `{name}` in {account_label or 'current account'}: "
                f"{error_code} - {error_message}"
            )

        except Exception as error:
            print(
                f"Unexpected S3 scan error for bucket `{name}` "
                f"in {account_label or 'current account'}: {error}"
            )


def scan_security_groups(ec2, notifier, ai_provider, account_label=""):
    security_groups = ec2.describe_security_groups()["SecurityGroups"]

    risky_ports = {
        22: "SSH",
        3389: "RDP",
    }

    for sg in security_groups:
        group_id = sg["GroupId"]
        group_name = sg.get("GroupName", "Unknown")

        for permission in sg.get("IpPermissions", []):
            from_port = permission.get("FromPort")
            to_port = permission.get("ToPort")

            for ip_range in permission.get("IpRanges", []):
                cidr = ip_range.get("CidrIp")

                if cidr != "0.0.0.0/0":
                    continue

                if from_port is None and to_port is None:
                    finding = with_account_context(
                        account_label,
                        (
                            f"🚨 CRITICAL: Security Group `{group_name}` "
                            f"({group_id}) allows ALL traffic from the internet."
                        ),
                    )
                    send_finding(notifier, ai_provider, finding)
                    continue

                for port, service in risky_ports.items():
                    if from_port <= port <= to_port:
                        finding = with_account_context(
                            account_label,
                            (
                                f"⚠️ HIGH: Security Group `{group_name}` "
                                f"({group_id}) exposes {service} port {port} "
                                f"to the internet."
                            ),
                        )
                        send_finding(notifier, ai_provider, finding)


def get_safe_ai_provider():
    try:
        return get_ai_provider()
    except Exception as error:
        print(f"AI provider initialization failed; AI disabled: {error}")
        return NoAIProvider()


def get_safe_notifier():
    try:
        return get_notifier()
    except Exception as error:
        print(
            "Notification provider initialization failed; "
            f"falling back to CloudWatch logs: {error}"
        )
        return ConsoleNotifier()


def scan_account(session, region_name, notifier, ai_provider, account_label):
    s3 = session.client("s3", region_name=region_name)
    ec2 = session.client("ec2", region_name=region_name)

    scan_s3(s3, notifier, ai_provider, account_label)
    scan_security_groups(ec2, notifier, ai_provider, account_label)


def get_active_organization_accounts():
    organizations = boto3.client("organizations")
    paginator = organizations.get_paginator("list_accounts")
    accounts = []

    for page in paginator.paginate():
        for account in page.get("Accounts", []):
            if account.get("Status") == "ACTIVE":
                accounts.append(account)

    return accounts


def assume_member_account_session(account_id, role_name, region_name):
    sts = boto3.client("sts", region_name=region_name)
    role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"

    response = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName="GriffleGuardSecurityScan",
    )

    credentials = response["Credentials"]

    return boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
        region_name=region_name,
    )


def scan_current_account(region_name, notifier, ai_provider):
    sts = boto3.client("sts", region_name=region_name)
    account_id = sts.get_caller_identity()["Account"]
    account_label = f"account {account_id}"

    scan_account(
        boto3.Session(region_name=region_name),
        region_name,
        notifier,
        ai_provider,
        account_label,
    )

    return account_id


def scan_organization(region_name, notifier, ai_provider):
    role_name = os.getenv(
        "MEMBER_SCAN_ROLE_NAME",
        "GriffleGuardReadOnlyRole",
    )

    current_account_id = boto3.client(
        "sts",
        region_name=region_name,
    ).get_caller_identity()["Account"]

    accounts = get_active_organization_accounts()
    scanned_accounts = 0
    failed_accounts = 0

    for account in accounts:
        account_id = account["Id"]
        account_name = account.get("Name", "Unknown")
        account_label = f"{account_name} ({account_id})"

        try:
            if account_id == current_account_id:
                session = boto3.Session(region_name=region_name)
            else:
                session = assume_member_account_session(
                    account_id,
                    role_name,
                    region_name,
                )

            scan_account(
                session,
                region_name,
                notifier,
                ai_provider,
                account_label,
            )
            scanned_accounts += 1

        except Exception as error:
            failed_accounts += 1
            print(
                f"Account scan failed for {account_label}; continuing: {error}"
            )

    return scanned_accounts, failed_accounts


def lambda_handler(event, context):
    notifier = get_safe_notifier()
    ai_provider = get_safe_ai_provider()

    region_name = os.getenv("AWS_REGION", "eu-north-1")
    organization_scan_enabled = (
        os.getenv("ORGANIZATION_SCAN_ENABLED", "false").lower() == "true"
    )

    try:
        if organization_scan_enabled:
            scanned_accounts, failed_accounts = scan_organization(
                region_name,
                notifier,
                ai_provider,
            )

            return {
                "status": "Scan Complete",
                "mode": "organization",
                "accounts_scanned": scanned_accounts,
                "accounts_failed": failed_accounts,
            }

        account_id = scan_current_account(
            region_name,
            notifier,
            ai_provider,
        )

        return {
            "status": "Scan Complete",
            "mode": "single-account",
            "account_id": account_id,
        }

    except Exception as error:
        print(f"Scan failed: {error}")

        return {
            "status": "Error",
            "error": str(error),
        }
