---
title: "Module 9: Cleanup"
chapter: true
weight: 90
---

# Module 9: Cleanup

{{% notice warning %}}
**Important:** If you deployed the CloudFormation stack (Module 7), clean up immediately to avoid ongoing charges. OpenSearch Serverless alone costs ~$350/month.
{{% /notice %}}

## Step 1: Stop Local Services

Press `Ctrl+C` in each terminal running MCP servers or Streamlit.

## Step 2: Empty S3 Buckets

S3 buckets must be empty before CloudFormation can delete them:

```bash
# Replace with your actual account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws s3 rm s3://manufacturing-datalake-${ACCOUNT_ID}-dev --recursive
aws s3 rm s3://agentcore-memory-${ACCOUNT_ID}-dev --recursive
```

## Step 3: Delete CloudFormation Stack

```bash
aws cloudformation delete-stack --stack-name manufacturing-insights-dev
```

## Step 4: Wait for Deletion

```bash
aws cloudformation wait stack-delete-complete --stack-name manufacturing-insights-dev
echo "✓ Stack deleted successfully"
```

{{% notice info %}}
Stack deletion takes 10–15 minutes (OpenSearch collection deletion is the slowest).
{{% /notice %}}

## Step 5: Verify

```bash
aws cloudformation describe-stacks --stack-name manufacturing-insights-dev 2>&1
# Should return: "Stack with id manufacturing-insights-dev does not exist"
```

## Step 6: Remove Local Files (Optional)

```bash
cd ..
rm -rf sample-autonomous-business-insights-mcp-multi-agents
```

## What Was Deleted

| Resource | Deleted? |
|----------|----------|
| Aurora cluster + instance | ✅ (DeletionProtection=false) |
| Timestream database + table | ✅ |
| Redshift namespace + workgroup | ✅ |
| OpenSearch collection | ✅ |
| S3 buckets | ✅ (after emptying) |
| IoT Core rule | ✅ |
| Cognito User Pool | ✅ |
| VPC + subnets | ✅ |
| IAM roles | ✅ |
| CloudWatch Log Group | ✅ |

## Congratulations! 🎉

You've completed the workshop. You built a working multi-source AI agent that:
- Connects to enterprise data through MCP servers
- Uses a Semantic Layer for intelligent data source discovery
- Enforces role-based access control at the Gateway
- Leverages memory for contextual, personalized responses
- Works with both simulated and live AWS infrastructure

## Next Steps

- Deploy to **Amazon Bedrock AgentCore** for production (Firecracker isolation, auto-scaling)
- Add more MCP servers for additional data sources (Salesforce, SAP, custom REST APIs)
- Implement **proactive agents** that monitor IoT data and alert before issues escalate
- Explore **A2A protocol** for cross-organization agent collaboration
