import base64
import json
import os
from decimal import Decimal

import boto3


def json_default(value):
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "content-type": "application/json",
        },
        "body": json.dumps(body, default=json_default),
    }


def get_table():
    table_name = os.environ["FINDINGS_TABLE_NAME"]
    return boto3.resource("dynamodb").Table(table_name)


def decode_next_token(token):
    if not token:
        return None

    try:
        decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        return None


def encode_next_token(last_evaluated_key):
    if not last_evaluated_key:
        return None

    raw = json.dumps(last_evaluated_key)
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8")


def get_finding(finding_id):
    result = get_table().get_item(Key={"FindingId": finding_id})
    item = result.get("Item")

    if not item:
        return response(404, {"message": "Finding not found"})

    return response(200, item)


def list_findings(query_parameters):
    query_parameters = query_parameters or {}
    severity = query_parameters.get("severity")
    status = query_parameters.get("status")
    next_token = query_parameters.get("nextToken")

    try:
        limit = int(query_parameters.get("limit", "50"))
    except ValueError:
        return response(400, {"message": "limit must be a number"})

    limit = max(1, min(limit, 100))

    scan_args = {"Limit": limit}
    exclusive_start_key = decode_next_token(next_token)

    if next_token and not exclusive_start_key:
        return response(400, {"message": "Invalid nextToken"})

    if exclusive_start_key:
        scan_args["ExclusiveStartKey"] = exclusive_start_key

    expressions = []
    names = {}
    values = {}

    if severity:
        expressions.append("Severity = :severity")
        values[":severity"] = severity.upper()

    if status:
        expressions.append("#status = :status")
        names["#status"] = "Status"
        values[":status"] = status.upper()

    if expressions:
        scan_args["FilterExpression"] = " AND ".join(expressions)
        scan_args["ExpressionAttributeValues"] = values

    if names:
        scan_args["ExpressionAttributeNames"] = names

    result = get_table().scan(**scan_args)

    body = {
        "items": result.get("Items", []),
        "count": result.get("Count", 0),
    }

    encoded_token = encode_next_token(result.get("LastEvaluatedKey"))
    if encoded_token:
        body["nextToken"] = encoded_token

    return response(200, body)


def lambda_handler(event, context):
    request_context = event.get("requestContext", {})
    http = request_context.get("http", {})
    method = http.get("method")
    raw_path = event.get("rawPath", "")

    if method != "GET":
        return response(405, {"message": "Method not allowed"})

    path_parameters = event.get("pathParameters") or {}
    finding_id = path_parameters.get("id")

    if finding_id:
        return get_finding(finding_id)

    if raw_path.endswith("/findings"):
        return list_findings(event.get("queryStringParameters"))

    return response(404, {"message": "Route not found"})
