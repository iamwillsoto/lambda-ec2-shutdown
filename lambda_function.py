import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2 = boto3.client("ec2")


def lambda_handler(event, context):
    """
    Foundational: stop ALL running EC2 instances in this region.

    Advanced/Complex later:
    - Tag-based filtering
    - DynamoDB logging
    - API Gateway integration
    """

    # 1) Find all running instances
    filters = [
        {
            "Name": "instance-state-name",
            "Values": ["running"],
        }
    ]

    response = ec2.describe_instances(Filters=filters)

    instance_ids = []
    for reservation in response.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            instance_ids.append(instance["InstanceId"])

    if not instance_ids:
        logger.info("No running instances found. Nothing to stop.")
        return {
            "stopped_count": 0,
            "stopped_instances": [],
        }

    # 2) Stop them
    logger.info(f"Stopping instances: {instance_ids}")
    ec2.stop_instances(InstanceIds=instance_ids)

    return {
        "stopped_count": len(instance_ids),
        "stopped_instances": instance_ids,
    }
