import boto3

from providers.ai.factory import get_ai_provider
from providers.notifications.factory import get_notifier


def build_message(ai_provider, finding):
    analysis = ai_provider.analyze(finding)

    if analysis == finding:
        return finding

    return f"{finding}\n\nAI analysis:\n{analysis}"


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

                notifier.send(
                    build_message(ai_provider, finding)
                )

        except Exception:
            finding = (
                f"🚨 CRITICAL: S3 bucket `{name}` has no "
                f"Public Access Block configuration."
            )

            notifier.send(
                build_message(ai_provider, finding)
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

                    notifier.send(
                        build_message(ai_provider, finding)
                    )

                    continue

                for port, service in risky_ports.items():
                    if from_port <= port <= to_port:
                        finding = (
                            f"⚠️ HIGH: Security Group `{group_name}` "
                            f"({group_id}) exposes {service} port {port} "
                            f"to the internet."
                        )

                        notifier.send(
                            build_message(ai_provider, finding)
                        )


def lambda_handler(event, context):
    s3 = boto3.client("s3")
    ec2 = boto3.client("ec2")

    notifier = get_notifier()
    ai_provider = get_ai_provider()

    try:
        scan_s3(s3, notifier, ai_provider)
        scan_security_groups(ec2, notifier, ai_provider)

        return {"status": "Scan Complete"}

    except Exception as e:
        print(f"Error: {e}")

        return {
            "status": "Error",
            "error": str(e),
        }
