---
title: "Generate Autonomous Business Insights with AI Agents and MCP Servers"
weight: 0
---

# Generate Autonomous Business Insights with AI Agents and MCP Servers

Welcome to this hands-on workshop! You will build a **multi-agent system** that transforms natural language questions into cross-system manufacturing insights using [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/), [Strands Agents SDK](https://strandsagents.com/), and the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/).

## Get the Source Code

Clone the sample repository to follow along with the code examples in this workshop:

```bash
git clone https://github.com/aws-samples/sample-autonomous-business-insights-with-ai-agent-and-mcp-servers.git
cd sample-autonomous-business-insights-with-ai-agent-and-mcp-servers
```

This repository contains the complete working implementation — MCP servers, Strands Agent, Cedar policies, deployment scripts, and tests. Each module in this workshop will reference specific files from this codebase.

## The Problem

A plant manager needs to know which assembly lines need attention this week. The answer requires correlating data from IoT sensors, equipment maintenance logs, supply chain inventory, and production analytics — five disconnected systems that today require hours of manual stitching.

## The Solution

A single Strands Agent connects to four domain MCP servers. The LLM's reasoning loop autonomously decides which tools to call — no custom orchestrator needed. Users ask questions in natural language; the agent handles routing, access control, and synthesis.

## What You Will Build

By the end of this workshop, you will have:

1. **Four MCP servers** exposing manufacturing data tools (equipment, IoT telemetry, supply chain, analytics)
2. **A Strands Agent** that autonomously reasons across all data sources
3. **AgentCore Runtime** — serverless agent execution on Firecracker microVMs
4. **AgentCore Harness** — managed deployment with hard cost caps (maxTokens, maxIterations)
5. **AgentCore Gateway** — MCP routing with request/response interceptors
6. **AgentCore Registry** — tool discovery, versioning, and governance
7. **AgentCore Identity** — Cognito authentication with role-based scope attributes
8. **AgentCore Policy** — Cedar deterministic authorization (forbid/permit)
9. **Cost Management** — Three-layer budget enforcement (Harness + Cedar + DynamoDB)
10. **AgentCore Memory** — session + cross-session context persistence (short-term, long-term, episodic)
11. **AgentCore Evaluations** — 7 metrics for systematic testing and validation
12. **AgentCore Observability** — X-Ray tracing, CloudWatch logging, metrics

## Target Audience

- Solutions Architects interested in multi-agent AI patterns
- Developers building enterprise AI applications with tool-use
- Anyone wanting hands-on experience with Amazon Bedrock AgentCore and MCP

## Duration

Approximately **5-6 hours**

## Author

**Sudhanshu Hate** (HiSuds@amazon.com)

## AWS Services Used

| Service | Purpose |
|---------|---------|
| Amazon Bedrock | LLM inference (Claude Sonnet) |
| Amazon Bedrock AgentCore | Agent runtime, gateway, policy, identity |
| Amazon Cognito | User authentication with role attributes |
| AWS Lambda | MCP tool targets |
| Amazon Aurora PostgreSQL | Equipment & maintenance data |
| Amazon Timestream | IoT sensor time-series |
| Amazon Redshift Serverless | Supply chain & OEE analytics |
| Amazon OpenSearch Serverless | Quality metrics (semantic search) |
| Amazon S3 | Configuration & data lake |

:::alert{type="info"}
This workshop uses simulated data by default. You can optionally deploy full AWS infrastructure for live data mode.
:::
