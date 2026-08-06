+++
title = "Introduction & Architecture"
weight: 10
+++

# Introduction & Architecture Overview

## The Manufacturing Intelligence Challenge

Sarah Chen manages 12 assembly lines and 2,000 machines. Before her 10 AM review she needs one answer: *Which lines need attention this week?*

She checks the IoT dashboard—Line 4's motor is running 12°C hot. She pivots to ERP for maintenance history, then to the historian for operating hours, then to OEE trends to see if Line 9's shared coolant loop is related. Three systems, three supervisors, one hour. She gets her answer.

Two floors down, Raj needs the same insight but can't access the dashboard—he's on a three-day-old PDF. Priya just wants one vibration reading; she doesn't have credentials. A CSV arrives four hours later. She's already moved on.

**Three people. Five systems. Hours of waiting—for answers that should take seconds.** The data existed but couldn't speak in one voice.

## How This Solution Works

Instead of building custom integrations between systems, this solution uses three key technologies:

### 1. Model Context Protocol (MCP)

MCP is an open standard that lets AI agents discover and use tools from any data source. Each data source exposes its capabilities as MCP tools—no custom adapters needed.

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│Equipment │    │   IoT    │    │  Supply  │    │Analytics │
│MCP Server│    │MCP Server│    │MCP Server│    │MCP Server│
└────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘
     │               │               │               │
     └───────────────┴───────┬───────┴───────────────┘
                             │
                      ┌──────▼──────┐
                      │ Strands Agent│
                      │ (Claude LLM) │
                      └─────────────┘
```

### 2. Strands Agents SDK

[Strands](https://strandsagents.com/) provides a lightweight Python framework for building AI agents with tool-use. The agent connects to MCP servers, receives all available tools, and the LLM autonomously decides which tools to call for each query.

### 3. Amazon Bedrock AgentCore

AgentCore provides the production infrastructure:
- **Runtime** — Serverless compute (Firecracker microVMs) for agent execution
- **Gateway** — Managed MCP router with policy enforcement
- **Identity** — OAuth integration (Cognito, Okta, Entra ID)
- **Policy** — Cedar-based deterministic authorization
- **Memory** — Cross-session context persistence
- **Observability** — X-Ray tracing + CloudWatch audit logs

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Users (Natural Language Queries)                                        │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                        │
│  │Sarah (All) │  │Raj (Line 7)│  │Priya (M42) │                        │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘                        │
└────────┼────────────────┼────────────────┼──────────────────────────────┘
         │                │                │
         ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Amazon Bedrock AgentCore                                               │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Gateway (MCP Router + Cedar Policy Enforcement)                  │  │
│  │  JWT Validation → REQUEST Interceptor → Policy → Tool Target      │  │
│  └───────────────────────────────────────┬───────────────────────────┘  │
│                                          │                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ │ ┌──────────┐               │
│  │ Runtime  │ │ Identity │ │  Policy  │ │ │  Memory  │               │
│  │(microVM) │ │(Cognito) │ │ (Cedar)  │ │ │(session) │               │
│  └──────────┘ └──────────┘ └──────────┘ │ └──────────┘               │
└──────────────────────────────────────────┼──────────────────────────────┘
                                           │
         ┌──────────────┬──────────────┬───┴───────────┐
         ▼              ▼              ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Equipment   │ │     IoT      │ │ Supply Chain │ │  Analytics   │
│  MCP Server  │ │  Telemetry   │ │  MCP Server  │ │  MCP Server  │
│  (Aurora)    │ │ (Timestream) │ │  (Redshift)  │ │  (Redshift)  │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

## User Personas

This workshop uses three personas to demonstrate role-based access:

| User | Role | Scope | Example Query |
|------|------|-------|---------------|
| **Sarah Chen** | Plant Manager | All 12 lines, all plants | "Which assembly lines need attention this week?" |
| **Raj Patel** | Line Supervisor | Line 7 only | "What's the current status of Line 7?" |
| **Priya Nair** | Maintenance Tech | Machines 41–45 only | "Has vibration on Machine 42 gotten worse?" |

The same agent serves all three users. Access boundaries are enforced at the Gateway—not in application code.

## Key Design Principles

1. **Configuration, not code** — Pre-built MCP servers replace custom integrations
2. **LLM-driven orchestration** — The agent decides which tools to call; no hardcoded workflow
3. **Deterministic security** — Cedar policies enforce access at the Gateway; the LLM cannot bypass them
4. **Zero auth in tools** — MCP servers contain no authorization logic; the Gateway handles it all

## Workshop Flow

| Module | What You Do | Time |
|--------|-------------|------|
| Prerequisites | Set up environment, verify credentials | 10 min |
| MCP Servers | Build and run 4 domain MCP servers | 25 min |
| Strands Agent | Connect agent to MCP servers, test queries | 20 min |
| Access Control | Implement Cedar policies, test deny scenarios | 25 min |
| AgentCore Deploy | Deploy to production with Gateway + Lambda | 25 min |
| Testing | Validate end-to-end across all personas | 15 min |

{{% notice tip %}}
Each module builds on the previous one. If you get stuck, the repository contains complete working code you can reference at any point.
{{% /notice %}}
