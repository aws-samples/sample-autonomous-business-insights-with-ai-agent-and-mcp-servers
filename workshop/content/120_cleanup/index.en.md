---
title: "Cleanup"
weight: 120
---

# Cleanup

Remove all AWS resources created during this workshop to avoid ongoing charges.

## Step 1: Remove AgentCore Resources

```bash
python deploy/agentcore/cleanup.py --region us-east-1 --confirm
```

This removes:
- AgentCore Gateway + test gateway
- Policy Engine + Cedar policies
- Lambda tool targets (Equipment, IoT, Analytics)
- Lambda interceptors (Request, Response)
- IAM roles created for the Gateway and Lambdas
- Cognito User Pool + users + groups
- Registry entries (tool registrations — removed with Gateway)
- Local config files (identity_config.json, gateway_config.json, etc.)

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
✅ Deleted IAM Role: Lambda-MfgInsights-EquipmentTarget-Role
✅ Deleted IAM Role: Lambda-MfgInsights-IoTTarget-Role
✅ Deleted IAM Role: Lambda-MfgInsights-AnalyticsTarget-Role
✅ Deleted Cognito User Pool: us-east-1_XXXXXXXX
✅ Cleanup complete!
```

## Step 2: Remove Memory Bucket Data

If you stored episodic or long-term memory entries in S3:

```bash
aws s3 rm s3://amzn-s3-demo-agentcore-memory-<account-id>-dev --recursive
```

This clears all user-scoped, team-scoped, and org-scoped memory data.

## Step 3: Remove CloudWatch Resources (Observability Module)

Delete the monitoring dashboard created in Module 11:

```bash
aws cloudwatch delete-dashboards \
  --dashboard-names "ManufacturingInsights-AgentCore" \
  --region us-east-1
```

Delete alarms:

```bash
aws cloudwatch delete-alarms \
  --alarm-names "AgentCore-HighDenyRate" "AgentCore-HighLatency" "AgentCore-TokenBudget" \
  --region us-east-1
```

Delete log groups:

```bash
aws logs delete-log-group \
  --log-group-name "/aws/agentcore/gateway/policy-decisions" \
  --region us-east-1
```

## Step 4: Remove Infrastructure (If Deployed)

If you deployed the full CloudFormation stack (live data mode):

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

:::alert{type="warning"}
S3 buckets must be empty before CloudFormation can delete them. If deletion fails, empty the buckets manually first:
```bash
aws s3 rm s3://amzn-s3-demo-manufacturing-datalake-<account-id>-dev --recursive
aws s3 rm s3://amzn-s3-demo-agentcore-memory-<account-id>-dev --recursive
aws s3 rm s3://amzn-s3-demo-mfg-insights-logs-<account-id>-dev --recursive
```
:::

## Step 5: Remove Local Files

```bash
# Deactivate virtual environment
deactivate

# Remove the project (optional)
cd ..
rm -rf sample-autonomous-business-insights-with-ai-agent-and-mcp-servers
```

## Step 6: Verify Cleanup

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

# Check for remaining CloudWatch alarms
aws cloudwatch describe-alarms \
  --alarm-name-prefix "AgentCore-" \
  --region us-east-1 --output text

# Check for remaining dashboards
aws cloudwatch list-dashboards \
  --dashboard-name-prefix "ManufacturingInsights" \
  --region us-east-1
```

All should return empty results.

## Complete Resource Inventory (What This Workshop Created)

| Resource | Service | Created In Module | Cleanup Step |
|----------|---------|-------------------|--------------|
| Gateway | AgentCore | 6 (Gateway) | Step 1 |
| Policy Engine + 4 Cedar policies | AgentCore | 9 (Policy) | Step 1 |
| 3 Lambda tool targets | Lambda | 6 (Gateway) | Step 1 |
| 2 Lambda interceptors | Lambda | 6 (Gateway) | Step 1 |
| 5 IAM roles | IAM | 6 (Gateway) | Step 1 |
| Cognito User Pool + 3 users | Cognito | 8 (Identity) | Step 1 |
| Memory data (episodic + long-term) | S3 | 10 (Memory) | Step 2 |
| CloudWatch Dashboard | CloudWatch | 12 (Observability) | Step 3 |
| 3 CloudWatch Alarms | CloudWatch | 12 (Observability) | Step 3 |
| Policy decision log group | CloudWatch Logs | 12 (Observability) | Step 3 |
| Aurora cluster (live mode only) | RDS | Prerequisites | Step 4 |
| Timestream database (live mode only) | Timestream | Prerequisites | Step 4 |
| Redshift workgroup (live mode only) | Redshift | Prerequisites | Step 4 |
| OpenSearch collection (live mode only) | OpenSearch | Prerequisites | Step 4 |
| 3 S3 buckets (live mode only) | S3 | Prerequisites | Step 4 |

## Cost Summary

If you completed the full workshop (all modules, ~3 hours):

| Service | Estimated Cost | Notes |
|---------|---------------|-------|
| Amazon Bedrock (Claude Sonnet) | ~$0.50–1.50 | ~50 queries × 1500 tokens avg |
| AgentCore Gateway | ~$0.10–0.25 | ~200 tool calls × $0.50/1000 |
| AgentCore Policy Engine | Included | Bundled with Gateway |
| AgentCore Memory (S3) | < $0.01 | Minimal data stored |
| Lambda invocations | Free tier | < 1000 invocations |
| Cognito | Free tier | 3 users |
| CloudWatch Logs | ~$0.05 | Policy audit logs |
| CloudWatch Alarms | Free tier | 3 alarms (free up to 10) |
| X-Ray Traces | Free tier | < 100K traces/month |
| **Total (simulated mode)** | **~$0.65–1.80** | |

If you deployed full infrastructure (live data mode), add:

| Service | Additional Cost | Notes |
|---------|----------------|-------|
| Aurora Serverless v2 | ~$3–5 | 0.5 ACU minimum × 3 hours |
| Redshift Serverless | ~$2–4 | 8 RPU × queries only |
| OpenSearch Serverless | ~$3–5 | 2 OCU minimum |
| Timestream | < $1 | Write/query charges |
| S3 | < $0.10 | Storage + requests |
| **Total (live mode)** | **~$10–16** | |

