# Deployment

This directory contains deployment artifacts for running the multi-agent system in production.

## Contents

| File | Purpose |
|------|---------|
| `agentcore_deploy.py` | Script demonstrating Amazon Bedrock AgentCore deployment workflow |
| `cloudformation/template.yaml` | AWS CloudFormation template (Aurora, Timestream, Redshift, OpenSearch, S3, IoT, DynamoDB) |
| `sql/create_tables.sql` | Redshift DDL for the SageMaker Lakehouse schema |
| `agentcore/setup_identity.py` | Deploy Cognito User Pool + 3 users with scope attributes |
| `agentcore/setup_gateway.py` | Deploy Gateway + Lambda tool targets + IAM roles |
| `agentcore/setup_policy.py` | Deploy Cedar Policy Engine (ENFORCE mode) |
| `agentcore/setup_interceptor.py` | Deploy REQUEST + RESPONSE Lambda interceptors |
| `agentcore/setup_harness.py` | Deploy AgentCore Harness with per-role cost caps |
| `agentcore/setup_budgets.py` | Deploy DynamoDB budget counters + seed limits + alarms |
| `agentcore/budget_config.json` | Central cost config (one file controls all limits) |
| `agentcore/cleanup.py` | Delete ALL deployed resources (9 cleanup steps) |
| `agentcore/deploy_all.py` | Run all 6 setup scripts in sequence |

## CloudFormation Stack

The template provisions:
- **Amazon Cognito User Pool** — authentication with custom role/scope attributes
- **S3 Bucket** — encrypted, versioned storage for AgentCore Memory persistence
- **CloudWatch Log Group** — agent observability and audit logging
- **IAM Role** — least-privilege execution role for AgentCore Runtime

### Deploy

```bash
aws cloudformation deploy \
  --template-file deploy/cloudformation/template.yaml \
  --stack-name manufacturing-insights-dev \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides Environment=dev
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `Environment` | `dev` | Deployment environment (dev, staging, prod) |
| `CognitoUserPoolName` | `manufacturing-insights-users` | Name for the Cognito User Pool |

### Outputs

| Output | Description |
|--------|-------------|
| `UserPoolId` | Cognito User Pool ID for AgentCore Identity |
| `UserPoolClientId` | Cognito Client ID for authentication |
| `MemoryBucketName` | S3 bucket for Memory persistence |
| `ExecutionRoleArn` | IAM role ARN for AgentCore Runtime |
| `LogGroupName` | CloudWatch Log Group name |

## Database Schema (Live Mode)

To use `DATA_MODE=live`, create the Redshift tables:

```bash
# Using Redshift Query Editor v2 in the AWS Console, or:
psql -h <workgroup-endpoint> -U admin -d manufacturing -f deploy/sql/create_tables.sql
```

The schema models:
- `equipment_registry` — machine master data (source: SAP S/4HANA via Zero-ETL)
- `maintenance_history` — work orders and repairs (source: SAP PM via Zero-ETL)
- `sensor_readings` — IoT time-series (source: IoT Core → MSK → S3 Tables)
- `detected_anomalies` — ML anomaly detection results (source: SageMaker pipeline)
- `parts_inventory` — spare parts stock (source: SAP MM via Zero-ETL)
- `oee_weekly` — OEE aggregations (source: daily ETL)
- `quality_metrics` — quality inspection results (source: SAP QM via Zero-ETL)

## Cleanup

```bash
aws cloudformation delete-stack --stack-name manufacturing-insights-dev
```

## Running the Demo UI

After deploying infrastructure and starting MCP servers:

```bash
streamlit run src/demo_ui.py
```

Open http://localhost:8501 for the interactive web interface.
