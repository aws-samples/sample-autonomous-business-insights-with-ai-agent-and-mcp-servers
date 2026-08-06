+++
title = "Prerequisites & Setup"
weight: 20
+++

# Prerequisites & Environment Setup

## What You Need

| Requirement | Details |
|-------------|---------|
| AWS Account | With admin access ([Create one](https://aws.amazon.com/free/)) |
| Amazon Bedrock | Model access enabled for **Anthropic Claude Sonnet** |
| AWS CLI | v2.x, configured with credentials |
| Python | 3.10 or later |
| Git | Any recent version |

## Step 1: Verify AWS Credentials

```bash
# Confirm CLI access
aws sts get-caller-identity
```

You should see your account ID, user ARN, and user ID. If this fails, run `aws configure` first.

## Step 2: Verify Bedrock Model Access

```bash
aws bedrock list-foundation-models \
  --query "modelSummaries[?contains(modelId, 'claude')].[modelId]" \
  --output table
```

You should see Claude Sonnet models listed. If not, [enable model access](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html) in the Bedrock console.

{{% notice warning %}}
Model access must be enabled in the region you plan to use (default: `us-east-1`). This is a one-time setup per region.
{{% /notice %}}

## Step 3: Clone the Repository

```bash
git clone https://github.com/aws-samples/sample-autonomous-business-insights-with-ai-agent-and-mcp-servers.git
cd sample-autonomous-business-insights-with-ai-agent-and-mcp-servers
```

## Step 4: Create Python Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

## Step 5: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `strands-agents` — Agent framework
- `mcp` — Model Context Protocol SDK
- `boto3` — AWS SDK
- `streamlit` — Web UI for the demo
- `fastmcp` — MCP server framework
- Other supporting libraries

## Step 6: Configure Environment

```bash
cp .env.example .env
```

For the workshop, the defaults are sufficient:

```bash
# .env — key settings for the workshop
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
SIMULATION_MODE=true
DATA_MODE=simulated
USE_PREBUILT_MCP=false
```

| Variable | Value | Meaning |
|----------|-------|---------|
| `SIMULATION_MODE` | `true` | Use local MCP servers (not AgentCore Gateway) |
| `DATA_MODE` | `simulated` | In-memory sample data (no infrastructure needed) |
| `USE_PREBUILT_MCP` | `false` | Run custom MCP servers locally |

{{% notice info %}}
We start in simulated mode so you can explore the architecture without deploying infrastructure. Later modules will switch to live mode.
{{% /notice %}}

## Step 7: Verify Everything Works

Run a quick smoke test:

```bash
python -c "
import strands
import mcp
import boto3
print('strands:', strands.__version__)
print('mcp: OK')
print('boto3:', boto3.__version__)
# Verify Bedrock connectivity
client = boto3.client('bedrock-runtime', region_name='us-east-1')
print('Bedrock client: OK')
print()
print('All prerequisites verified!')
"
```

You should see version numbers and "All prerequisites verified!" with no errors.

## Understanding the Project Layout

```
.
├── src/
│   ├── agent/           # Strands Agent (you'll explore in Module 4)
│   ├── servers/         # MCP servers (you'll build in Module 3)
│   ├── identity/        # Policy engine + gateway hook (Module 5)
│   ├── memory/          # Session + long-term memory
│   └── data/            # Data providers (simulated + live)
├── deploy/
│   ├── agentcore/       # AgentCore deployment scripts (Module 6)
│   ├── cloudformation/  # Infrastructure-as-code
│   └── sql/             # Database schemas
└── tests/               # Unit and integration tests
```

## You're Ready!

Your environment is set up. In the next module, you'll build and explore the MCP servers that expose manufacturing data as tools.

{{% notice tip %}}
Keep your terminal open with the virtual environment activated. You'll use it throughout the workshop.
{{% /notice %}}
