---
title: "Generate Autonomous Business Insights with MCP Servers"
chapter: true
weight: 0
---

# Generate Autonomous Business Insights with MCP Servers and Amazon Bedrock AgentCore

## Welcome!

In this workshop, you will build a **multi-source AI agent** that answers natural language questions by autonomously querying data from across an enterprise technology stack — equipment registries, IoT sensors, supply chain systems, and production analytics.

You'll use **Amazon Bedrock AgentCore**, the **Strands Agents SDK**, and the **Model Context Protocol (MCP)** to create a system where:

- A single agent connects to multiple data sources through MCP servers
- A Semantic Layer guides the agent to the right data sources per query
- Cedar-style access policies enforce role-based data isolation
- Memory enables contextual follow-up questions across sessions

## What You'll Build

By the end of this workshop, you'll have a working system where three different manufacturing users — a Plant Manager, a Line Supervisor, and a Maintenance Technician — can each ask questions and receive personalized, access-controlled, cross-system insights in seconds.

{{% notice info %}}
**Time to complete:** 2–3 hours (self-paced) | 90 minutes (instructor-led)
{{% /notice %}}

## Target Audience

- Solutions Architects evaluating AgentCore for enterprise customers
- Developers building multi-source AI assistants
- Data Engineers connecting enterprise systems to AI agents

## Prerequisites

- AWS Account with Amazon Bedrock access (Claude Sonnet enabled)
- Basic Python knowledge
- Familiarity with REST APIs

## Workshop Modules

| Module | Topic | Duration |
|--------|-------|----------|
| 1 | Introduction & Architecture | 10 min |
| 2 | Environment Setup | 15 min |
| 3 | Build MCP Servers | 30 min |
| 4 | Build the Agent | 20 min |
| 5 | Access Control & Policy | 20 min |
| 6 | Memory & Context | 15 min |
| 7 | Live AWS Infrastructure (optional) | 30 min |
| 8 | Web UI Demo | 10 min |
| 9 | Cleanup | 5 min |
