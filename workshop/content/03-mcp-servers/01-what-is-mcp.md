---
title: "What is MCP?"
weight: 31
---

# What is the Model Context Protocol?

The **Model Context Protocol (MCP)** is an open standard that defines how AI agents discover and invoke tools. Think of it like REST for AI — a standardized interface between agents and the services they use.

## Why MCP Matters

Without MCP, connecting an AI agent to enterprise data requires:
- Custom API wrappers per data source
- Bespoke schema definitions per tool
- Agent-specific integration code
- Tight coupling between agent and data source

With MCP:
- Tools are **self-describing** (name, description, typed input schema)
- Agents discover tools at runtime via a standard protocol
- Any MCP-compatible agent works with any MCP server
- Servers are independently deployable and versionable

## Pre-Built vs Custom MCP Servers

AWS provides **pre-built MCP servers** for many services at [awslabs.github.io/mcp](https://awslabs.github.io/mcp/). These require zero code — just configure and connect.

In this workshop, we use **both**:

| Data Source | MCP Server | Why |
|-------------|-----------|-----|
| Aurora PostgreSQL (equipment) | **Pre-built**: `awslabs.postgres-mcp-server` | AWS provides it out of the box |
| Amazon Redshift (supply chain) | **Pre-built**: `awslabs.redshift-mcp-server` | AWS provides it out of the box |
| Amazon Timestream (IoT sensors) | **Custom**: `iot_telemetry_server.py` | No pre-built Timestream MCP exists |
| Amazon OpenSearch (quality) | **Custom**: `analytics_server.py` | No pre-built OpenSearch search MCP exists |
| Semantic Layer (discovery) | **Custom**: `semantic_layer_server.py` | Domain-specific business logic |

This demonstrates the real-world pattern:
- **Use pre-built** when available (saves engineering time)
- **Build custom** only for services or domain logic not covered

## Transport: stdio vs Streamable HTTP

MCP supports multiple transports:

| Transport | Used By | How It Works |
|-----------|---------|-------------|
| **stdio** | Pre-built AWS MCP servers | Agent spawns the server as a subprocess via `uvx`, communicates over stdin/stdout |
| **Streamable HTTP** | Custom MCP servers | Server runs as HTTP service, agent connects via `http://localhost:port/mcp/` |

```python
# Pre-built (stdio via uvx) — zero code, just config
postgres_client = MCPClient(lambda: stdio_client(
    StdioServerParameters(command="uvx", args=["awslabs.postgres-mcp-server@latest"])
))

# Custom (streamable HTTP) — you build the server
iot_client = MCPClient(lambda: streamablehttp_client("http://localhost:8002/mcp/"))
```

The agent doesn't care which transport is used — it sees the same MCP tools either way.

## In Production (AgentCore)

In Amazon Bedrock AgentCore, you don't manage transports:
- Register MCP servers in the **AgentCore Registry**
- The **Gateway** handles routing, discovery, and caching
- Agent calls tools by name — Gateway routes to the correct server
