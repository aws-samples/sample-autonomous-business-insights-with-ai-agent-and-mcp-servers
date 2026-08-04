+++
title = "Cleanup"
weight = 120
+++

# Cleanup

Remove all AWS resources created during this workshop to avoid ongoing charges.

## Step 1: Remove AgentCore Resources

```bash
python deploy/agentcore/cleanup.py --region us-east-1 --confirm
```

This removes:
- AgentCore Gateway
- Policy Engine + Cedar policies
- Lambda tool targets (Equipment, IoT, Analytics)
- Lambda interceptors (Request, Response)
- IAM roles created for the Gateway
- Cognito User Pool + users

Expected output:

```
✅ Deleted Policy Engine: <policy-engine-id>
✅ Deleted Gateway: <gateway-id>
✅ Deleted Test Gateway: <test-gateway-id>
✅ Deleted Lambda: MfgInsights-EquipmentTools
✅ Deleted Lambda: MfgInsights-IoTTools
✅ Deleted Lambda: MfgInsights-AnalyticsTools
✅ Deleted Lambda: MfgInsights-RequestInterceptor
✅ Deleted Lambda: MfgInsights-ResponseInterceptor
✅ Deleted IAM Role: MfgInsights-Gateway-Role
✅ Deleted Cognito User Pool: us-east-1_XXXXXXXX
✅ Cleanup complete!
```

## Step 2: Remove Infrastructure (If Deployed)

If you deployed the full CloudFormation stack (Option 2 — live data mode):

```bash
aws cloudformation delete-stack \
  --stack-name manufacturing-insights-dev \
  --region us-east-1
```

Wait for deletion to complete:

```bash
aws cloudformation wait stack-delete-complete \
  --stack-name manufacturing-insights-dev \
  --region us-east-1
```

This removes:
- Aurora PostgreSQL cluster + instance
- Timestream database + table
- Redshift Serverless namespace + workgroup
- OpenSearch Serverless collection + policies
- S3 buckets (data lake, memory, logging)
- VPC + subnets + security groups
- IoT Core rule
- All associated IAM roles

{{% notice warning %}}
S3 buckets must be empty before CloudFormation can delete them. If deletion fails, empty the buckets manually first:
```bash
aws s3 rm s3://amzn-s3-demo-manufacturing-datalake-<account-id>-dev --recursive
aws s3 rm s3://amzn-s3-demo-agentcore-memory-<account-id>-dev --recursive
aws s3 rm s3://amzn-s3-demo-mfg-insights-logs-<account-id>-dev --recursive
```
{{% /notice %}}

## Step 3: Remove CloudWatch Resources

Delete the monitoring dashboard:

```bash
aws cloudwatch delete-dashboards \
  --dashboard-names "ManufacturingInsights-AgentCore" \
  --region us-east-1
```

Delete alarms:

```bash
aws cloudwatch delete-alarms \
  --alarm-names "AgentCore-HighDenyRate" \
  --region us-east-1
```

## Step 4: Remove Local Files

```bash
# Deactivate virtual environment
deactivate

# Remove the project (optional)
cd ..
rm -rf sample-autonomous-business-insights-with-ai-agent-and-mcp-servers
```

## Step 5: Verify Cleanup

Confirm no resources remain:

```bash
# Check for remaining stacks
aws cloudformation list-stacks \
  --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE \
  --query "StackSummaries[?contains(StackName, 'manufacturing')]" \
  --region us-east-1

# Check for remaining Lambda functions
aws lambda list-functions \
  --query "Functions[?contains(FunctionName, 'MfgInsights')].[FunctionName]" \
  --region us-east-1 --output text
```

Both should return empty results.

## Cost Summary

If you completed the full workshop (all modules, ~2 hours):

| Service | Estimated Cost |
|---------|---------------|
| Amazon Bedrock (Claude Sonnet) | ~$0.50–1.00 |
| Lambda invocations | Free tier |
| Cognito | Free tier |
| AgentCore Gateway | ~$0.10 |
| CloudWatch Logs | ~$0.05 |
| **Total** | **~$0.65–1.15** |

If you deployed full infrastructure (live data mode), add ~$5-10 for the Aurora, Redshift, and OpenSearch resources during the workshop.
