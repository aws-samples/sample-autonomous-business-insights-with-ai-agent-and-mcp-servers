---
title: "Prerequisites"
weight: 21
---

# Prerequisites

## AWS Account

You need an AWS account with the following:

1. **Amazon Bedrock access** — Anthropic Claude Sonnet model enabled
2. **AWS CLI** configured with credentials that have Bedrock invoke permissions
3. **(Optional for Module 7)** — Permissions to create CloudFormation stacks with Aurora, Redshift, Timestream, OpenSearch, and IAM resources

### Enable Bedrock Model Access

1. Open the [Amazon Bedrock console](https://console.aws.amazon.com/bedrock/)
2. Navigate to **Model access** in the left sidebar
3. Click **Manage model access**
4. Enable **Anthropic → Claude Sonnet**
5. Click **Save changes**

{{% notice warning %}}
Model access requests are typically approved instantly, but may take up to a few minutes in some regions.
{{% /notice %}}

## Local Tools

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.10+ | Runtime for all code |
| AWS CLI | v2 | AWS credential management |
| Git | Any | Clone the repository |

### Verify your setup

```bash
python3 --version   # Should be 3.10+
aws --version       # Should be aws-cli/2.x
aws sts get-caller-identity  # Should return your account info
```

{{% notice tip %}}
If you're running this in an AWS-provided workshop environment (Event Engine), your credentials are already configured.
{{% /notice %}}
