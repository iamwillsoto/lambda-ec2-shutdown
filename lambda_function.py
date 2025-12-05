import boto3
import os
import json
from datetime import datetime, timezone

# EC2 + DynamoDB clients/resources
ec2 = boto3.client("ec2")
dynamodb = boto3.resource("dynamodb")

# Table name passed from CloudFormation via env var
TABLE_NAME = os.environ.get("SHUTDOWN_LOG_TABLE", "")


def lambda_handler(event, context):
    """
    COMPLEX behavior:

    - Always target EC2 instances with:
        AutoShutdown = True
        AND EITHER:
          * Environment = Dev           (default / scheduled)
          * {key: value} from API call (when provided)

    - Supports two trigger types:
        1) EventBridge scheduled event  -> no query params
        2) API Gateway HTTP API (GET)   -> ?key=Release&value=2

    - Stops matching running instances
    - Logs each shutdown to DynamoDB
    """

    # Detect if this is an API Gateway HTTP API call
    source = "schedule"
    tag_key = None
    tag_value = None

    # HTTP API v2 payloads include requestContext.http
    if isinstance(event, dict) and "requestContext" in event and "http" in event["requestContext"]:
        source = "api"
        qs = event.get("queryStringParameters") or {}
        tag_key = qs.get("key")
        tag_value = qs.get("value")

    # Base filters always applied
    filters = [
        {"Name": "instance-state-name", "Values": ["running"]},
        {"Name": "tag:AutoShutdown", "Values": ["True"]},
    ]

    # If API provided ?key=Release&value=2, use that tag
    if tag_key and tag_value:
        filters.append({"Name": f"tag:{tag_key}", "Values": [tag_value]})
        effective_filter = f"{tag_key}={tag_value}"
    else:
        # Default scheduled behavior: Environment=Dev
        filters.append({"Name": "tag:Environment", "Values": ["Dev"]})
        tag_key = "Environment"
        tag_value = "Dev"
        effective_filter = "Environment=Dev"

    print(f"Trigger source: {source}")
    print(f"Using filters: AutoShutdown=True AND {effective_filter}")

    response = ec2.describe_instances(Filters=filters)

    instances_to_stop = []

    for reservation in response.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            instance_id = instance["InstanceId"]
            tags = {t["Key"]: t["Value"] for t in instance.get("Tags", [])}

            instances_to_stop.append(
                {
                    "InstanceId": instance_id,
                    "Tags": tags,
                }
            )

    # 2) Stop all matching instances (if any)
    if instances_to_stop:
        ec2.stop_instances(
            InstanceIds=[i["InstanceId"] for i in instances_to_stop]
        )
        print(f"Stopping instances: {[i['InstanceId'] for i in instances_to_stop]}")
    else:
        print("No matching instances found to stop.")

    # 3) Log to DynamoDB, one item per stopped instance
    logged = 0
    if TABLE_NAME and instances_to_stop:
        table = dynamodb.Table(TABLE_NAME)
        timestamp = datetime.now(timezone.utc).isoformat()

        for item in instances_to_stop:
            tags = item["Tags"]
            try:
                table.put_item(
                    Item={
                        "InstanceId": item["InstanceId"],
                        "ShutdownTimeUtc": timestamp,
                        "Environment": tags.get("Environment", ""),
                        "Name": tags.get("Name", ""),
                        "AutoShutdown": tags.get("AutoShutdown", ""),
                        "Source": source,  # 'api' or 'schedule'
                        "FilterKey": tag_key or "",
                        "FilterValue": tag_value or "",
                        "RequestId": context.aws_request_id,
                        "AllTagsJson": json.dumps(tags),
                    }
                )
                logged += 1
            except Exception as e:
                print(f"Failed to log shutdown for {item['InstanceId']}: {e}")

    result = {
        "trigger_source": source,
        "filter_key": tag_key,
        "filter_value": tag_value,
        "stopped_count": len(instances_to_stop),
        "logged_count": logged,
        "table": TABLE_NAME,
    }

    # If called by HTTP API, return proper HTTP response
    if source == "api":
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result),
        }

    # For EventBridge schedule, plain JSON is fine
    return result
