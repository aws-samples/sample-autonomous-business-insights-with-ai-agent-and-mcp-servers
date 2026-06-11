---
title: "Module 3: Build MCP Servers"
chapter: true
weight: 30
---

# Module 3: Build MCP Servers

In this module, you'll understand the Model Context Protocol and build domain-specific MCP servers that expose manufacturing data as typed tools.

## What You'll Learn

- What MCP is and why it matters for enterprise AI
- How to create an MCP server with FastMCP
- How to expose typed tools with input validation
- How the Semantic Layer enables data source discovery
- How to test MCP servers independently

## Key Concept

Each domain of your business (equipment, IoT, supply chain, analytics) becomes an **independent MCP server**. Each server:
- Owns its tools, schemas, and authentication context
- Can be deployed, updated, and scaled independently
- Follows the open MCP standard (no vendor lock-in)
- Can run in stateless or stateful mode

## Module Pages

1. [What is MCP?](01-what-is-mcp) — Protocol overview, why it matters
2. [Build the Equipment Server](02-equipment-server) — First MCP server, step by step with code
3. [Build the IoT Telemetry Server](03-iot-server) — Sensor data tools, input validation, design patterns
4. [The Semantic Layer Server](04-semantic-layer) — Data source discovery, catalog registration, scaling
5. [Start & Test All Servers](05-test-servers) — Run all 5 servers, verify tool discovery
