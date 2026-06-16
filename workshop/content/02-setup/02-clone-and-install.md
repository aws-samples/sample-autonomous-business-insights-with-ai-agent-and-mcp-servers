---
title: "Clone & Install"
weight: 22
---

# Clone & Install

## 1. Clone the repository

```bash
git clone https://github.com/aws-samples/sample-autonomous-business-insights-with-ai-agent-and-mcp-servers.git
cd sample-autonomous-business-insights-with-ai-agent-and-mcp-servers
```

## 2. Create a Python virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `strands-agents` — Strands Agents SDK for building the AI agent
- `mcp` — Model Context Protocol SDK for building MCP servers
- `boto3` — AWS SDK for connecting to Bedrock and data services
- `streamlit` — Web UI for the demo
- `pydantic` — Data validation
- `python-dotenv` — Environment variable management

## 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set your AWS region:

```bash
AWS_REGION=us-east-1
DATA_MODE=simulated
```

{{% notice info %}}
For Modules 1–6, you only need `AWS_REGION` and `DATA_MODE=simulated`. The other variables are only needed for Module 7 (Live Infrastructure).
{{% /notice %}}

## 5. Verify the installation

```bash
python -c "from strands import Agent; print('✓ Strands SDK installed')"
python -c "from mcp.server import FastMCP; print('✓ MCP SDK installed')"
python -c "import boto3; print('✓ Boto3 installed')"
```

All three should print success messages.
