---
title: "Deploy CloudFormation Stack"
weight: 71
---

# Deploy the Full Data Infrastructure

## What Gets Created

The CloudFormation template provisions:

| Service | Resource | Purpose |
|---------|----------|---------|
| Aurora PostgreSQL Serverless v2 | Cluster + instance | Equipment registry, maintenance history |
| Amazon Timestream | Database + table | IoT sensor time-series |
| Redshift Serverless | Namespace + workgroup | Supply chain, OEE analytics |
| OpenSearch Serverless | Collection | Quality metrics, semantic search |
| Amazon S3 | 2 buckets | Data lake + agent memory |
| AWS IoT Core | Topic rule | Sensor data → Timestream pipeline |
| Amazon Cognito | User Pool | Authentication |
| IAM | Execution role | Least-privilege access to all services |
| VPC | VPC + subnets + SG | Network isolation for Aurora/Redshift |

## Deploy

```bash
aws cloudformation deploy \
  --template-file deploy/cloudformation/template.yaml \
  --stack-name manufacturing-insights-dev \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    Environment=dev \
    DatabasePassword=YourSecureP@ssw0rd123
```

{{% notice info %}}
Deployment takes approximately **15–20 minutes** (OpenSearch Serverless collection creation is the longest step).
{{% /notice %}}

## Get Stack Outputs

Once deployment completes:

```bash
aws cloudformation describe-stacks \
  --stack-name manufacturing-insights-dev \
  --query "Stacks[0].Outputs[*].{Key:OutputKey,Value:OutputValue}" \
  --output table
```

## Configure Environment

Copy the output values into your `.env` file:

```bash
DATA_MODE=live

# From stack outputs:
AURORA_CLUSTER_ARN=<AuroraClusterArn output>
AURORA_SECRET_ARN=<AuroraSecretArn output>
AURORA_DATABASE=manufacturing
TIMESTREAM_DATABASE=<TimestreamDatabaseName output>
TIMESTREAM_TABLE=sensor_readings
REDSHIFT_WORKGROUP=<RedshiftWorkgroupName output>
REDSHIFT_DATABASE=manufacturing
OPENSEARCH_ENDPOINT=<OpenSearchEndpoint output>
OPENSEARCH_INDEX=quality_metrics
DATA_LAKE_BUCKET=<DataLakeBucketName output>
```

## Seed Data

Populate all services with sample manufacturing data:

```bash
python deploy/seed_data.py
```

This writes:
- 7 machines + 3 assembly lines + maintenance records → Aurora
- 7 days of sensor readings (vibration + temperature) → Timestream
- Parts inventory + 4 weeks of OEE data → Redshift
- Quality inspection documents → OpenSearch
- Shared infrastructure config + equipment catalog → S3

## Run in Live Mode

```bash
# Start MCP servers (they read DATA_MODE from .env)
python -m src.servers.start_all

# In another terminal, launch the UI
streamlit run src/demo_ui.py
```

The sidebar will show **🔴 Live (real AWS services)** — all queries now hit real Aurora, Timestream, Redshift, and OpenSearch.

{{% notice success %}}
**Checkpoint:** Ask "What is the vibration on Machine 42?" and verify the response includes data from Timestream (real readings) and Aurora (maintenance context). The UI should show "Connected to real AWS infrastructure".
{{% /notice %}}
