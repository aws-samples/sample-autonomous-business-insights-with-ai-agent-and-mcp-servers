---
title: "Module 1: Introduction"
chapter: true
weight: 10
---

# Module 1: Introduction

In this module, you'll understand the business problem this workshop solves, the architecture we'll build, and what you'll have at the end.

## The Monday Morning Problem

Sarah Chen is a Plant Manager at a precision manufacturing company. She has 12 assembly lines, 2,000+ machines, and one question before her 10 AM production review:

> "Which assembly lines need attention this week?"

Simple question. But the answer requires correlating data from **five disconnected systems**:

1. **IoT Platform** (AWS IoT Core) — sensor data: temperature, vibration, pressure
2. **ERP System** (SAP S/4HANA) — maintenance history, warranty records
3. **Historian Database** — operating hours, capacity utilization
4. **Analytics Dashboard** — OEE trends, throughput metrics
5. **Quality Management** (SAP QM) — scrap rates, defect categories

Today, Sarah manually stitches context across these systems. It takes her **75 minutes**. By then, her production review has started without actionable data.

Two floors down, Line Supervisor Raj Patel needs the same type of answer — but only has access to 3 of the 5 systems. Maintenance Technician Priya Nair can't even log into the IoT platform directly.

**Three people. Five systems. Hours of manual work. For answers that should take seconds.**

## What Makes This Hard

- Each system has its own API, its own query language, its own access model
- No single dashboard can correlate across all five
- Traditional BI shows what happened — not what to do about it
- Building a custom multi-agent system takes months of platform engineering

## The Solution: Configuration, Not Code

Amazon Bedrock AgentCore provides the orchestration platform. You bring your data sources as MCP servers. The agent handles routing, access control, memory, and synthesis.

**What you'll build in this workshop:**
- 5 MCP servers (Semantic Layer + 4 domain servers)
- 1 Strands Agent that uses all of them
- Cedar-style policy enforcement at the Gateway
- Memory that persists context across sessions
- A Streamlit UI to demo it all
