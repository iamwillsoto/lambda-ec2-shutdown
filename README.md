🚦 EC2 Auto-Shutdown System (Tag-Based + API Trigger + DynamoDB Logging)

This project evolved through layered enhancements — starting with a simple EC2 shutdown Lambda and expanding into a complete, automated operations workflow used across beta and production environments.

🧩 How the System Evolved (Layered Approach)
1. Base Layer — Automated EC2 Shutdown

The project began with a Lambda function scheduled via EventBridge to stop EC2 instances automatically at a set time.

2. Tag-Driven Control

Next, we added tag filtering, allowing the Lambda to selectively shut down instances based on tags (e.g., AutoShutdown=True, Environment=Dev, or any custom key/value pair).

3. REST API Trigger (Manual Override)

We introduced an HTTP API endpoint through API Gateway, enabling manual shutdown triggers using:
GET /shutdown?key=Release&value=2

This lets DevOps teams remotely stop instances without needing console access.

4. GitHub Actions CI/CD Automation

We then implemented separate beta and production pipelines using GitHub Actions:

Builds and zips the Lambda code

Uploads to dedicated S3 buckets

Deploys CloudFormation stacks
This made the entire deployment workflow repeatable and environment-specific.

5. Serverless Logging Layer with DynamoDB

Finally, we added structured logging for every shutdown event:

Instance ID

Timestamp (UTC)

All instance tags

Filter criteria used

Request ID
This creates a durable audit trail and enables future analytics or operational insight.

🏗️ Architecture Summary

AWS Lambda – Executes shutdown logic

Amazon EventBridge – Scheduled automation

HTTP API (API Gateway) – Manual shutdown trigger

DynamoDB – Persistent event log

S3 – Stores Lambda deployment packages

CloudFormation – Full infrastructure as code

GitHub Actions – Continuous delivery for both beta + prod

🎯 Business Impact

Prevents unnecessary EC2 costs

Centralizes shutdown logic across multiple workloads

Provides traceability for compliance and auditing

Enables teams to trigger safe shutdowns without console access

Fully automated deployments reduce human error
