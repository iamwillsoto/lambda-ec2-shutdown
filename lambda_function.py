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
    Advanced behavior:
    - Find running EC2 instances with BOTH tags:
        Environment = Dev
        AutoShutdown = True
    - Stop them
    - Log each stopped instance to DynamoDB
    """

    # 1) Filter only the instances we care about
    filters = [
        {"Name": "instance-state-name", "Values": ["running"]},
        {"Name": "tag:Environment", "Values": ["Dev"]},
        {"Name": "tag:AutoShutdown", "Values": ["True"]},
    ]

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

    # 3) Log to DynamoDB, one item per stopped instance
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
                        "RequestId": context.aws_request_id,
                        "AllTagsJson": json.dumps(tags),
                    }
                )
            except Exception as e:
                # Basic error logging; you’ll see this in CloudWatch Logs
                print(
                    f"Failed to log shutdown for {item['InstanceId']}: {e}"
                )

    return {
        "stopped_count": len(instances_to_stop),
        "table": TABLE_NAME,
    }
