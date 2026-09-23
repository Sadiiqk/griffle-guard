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


def scan_s3(s3, notifier, ai_provider):
    buckets = s3.list_buckets()["Buckets"]

    for bucket in buckets:
        name = bucket["Name"]

        try:
            status = s3.get_public_access_block(Bucket=name)
            config = status["PublicAccessBlockConfiguration"]
            is_secure = all(config.values())

            if not is_secure:
                finding = (
                    f"⚠️ HIGH: S3 bucket `{name}` may allow public access."
                )
                send_finding(notifier, ai_provider, finding)

        except ClientError as error:
            error_code = error.response.get("Error", {}).get("Code", "Unknown")
            error_message = error.response.get("Error", {}).get(
                "Message",
                "No error message returned",
            )

            if error_code == "NoSuchPublicAccessBlockConfiguration":
                finding = (
                    f"🚨 CRITICAL: S3 bucket `{name}` has no "
                    f"Public Access Block configuration."
                )
                send_finding(notifier, ai_provider, finding)
                continue

            print(
                f"S3 scan error for bucket `{name}`: "
                f"{error_code} - {error_message}"
            )

        except Exception as error:
            print(
                f"Unexpected S3 scan error for bucket `{name}`: {error}"
            )


def scan_security_groups(ec2, notifier, ai_provider):
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
                    finding = (
                        f"🚨 CRITICAL: Security Group `{group_name}` "
                        f"({group_id}) allows ALL traffic from the internet."
                    )
                    send_finding(notifier, ai_provider, finding)
                    continue

                for port, service in risky_ports.items():
                    if from_port <= port <= to_port:
                        finding = (
                            f"⚠️ HIGH: Security Group `{group_name}` "
                            f"({group_id}) exposes {service} port {port} "
                            f"to the internet."
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


def lambda_handler(event, context):
    s3 = boto3.client("s3")
    ec2 = boto3.client("ec2")

    notifier = get_safe_notifier()
    ai_provider = get_safe_ai_provider()

    try:
        scan_s3(s3, notifier, ai_provider)
        scan_security_groups(ec2, notifier, ai_provider)

        return {"status": "Scan Complete"}

    except Exception as error:
        print(f"Scan failed: {error}")

        return {
            "status": "Error",
            "error": str(error),
        }
