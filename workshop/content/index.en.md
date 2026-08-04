+++
title = "Generate Autonomous Business Insights with AI Agents and MCP Servers"
weight = 0
+++

# Generate Autonomous Business Insights with AI Agents and MCP Servers

Welcome to this hands-on workshop! You will build a **multi-agent system** that transforms natural language questions into cross-system manufacturing insights using [Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/), [Strands Agents SDK](https://strandsagents.com/), and the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/).

## The Problem

A plant manager needs to know which assembly lines need attention this week. The answer requires correlating data from IoT sensors, equipment maintenance logs, supply chain inventory, and production analytics — five disconnected systems that today require hours of manual stitching.

## The Solution

A single Strands Agent connects to four domain MCP servers. The LLM's reasoning loop autonomously decides which tools to call — no custom orchestrator needed. Users ask questions in natural language; the agent handles routing, access control, and synthesis.

## What You Will Build

By the end of this workshop, you will have:

1. **Four MCP servers** exposing manufacturing data tools (equipment, IoT telemetry, supply chain, analytics)
2. **A Strands Agent** that autonomously reasons across all data sources
3. **AgentCore Runtime** — serverless agent execution on Firecracker microVMs
4. **AgentCore Gateway** — MCP routing with request/response interceptors
5. **AgentCore Identity** — Cognito authentication with role-based scope attributes
6. **AgentCore Policy** — Cedar deterministic authorization (forbid/permit)
7. **AgentCore Memory** — session + cross-session context persistence
8. **AgentCore Evaluations** — systematic testing and validation
9. **AgentCore Observability** — X-Ray tracing, CloudWatch logging, metrics

## Target Audience

- Solutions Architects interested in multi-agent AI patterns
- Developers building enterprise AI applications with tool-use
- Anyone wanting hands-on experience with Amazon Bedrock AgentCore and MCP

## Duration

Approximately **3 hours**

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

{{% notice info %}}
This workshop uses simulated data by default. You can optionally deploy full AWS infrastructure for live data mode.
{{% /notice %}}
