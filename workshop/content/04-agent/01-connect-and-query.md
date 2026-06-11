---
title: "Connect Agent to MCP Servers"
weight: 41
---

# Connect the Agent to MCP Servers

## The Core Pattern

The entire agent is just this:

```python
from strands import Agent
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client

# 1. Connect to all MCP servers
server_urls = [
    "http://localhost:8005/mcp/",  # Semantic Layer
    "http://localhost:8001/mcp/",  # Equipment
    "http://localhost:8002/mcp/",  # IoT Telemetry
    "http://localhost:8003/mcp/",  # Supply Chain
    "http://localhost:8004/mcp/",  # Analytics
]

mcp_clients = [MCPClient(lambda url=url: streamablehttp_client(url)) for url in server_urls]

# 2. Collect ALL tools from ALL servers
all_tools = []
for client in mcp_clients:
    client.__enter__()
    all_tools.extend(client.list_tools_sync())

print(f"Connected to {len(mcp_clients)} servers, {len(all_tools)} tools available")

# 3. Create agent with all tools
agent = Agent(
    system_prompt="You are a manufacturing insights agent...",
    tools=all_tools,
)

# 4. Ask a question — agent decides which tools to call
response = agent("Which assembly lines need attention this week?")
print(response)
```

That's it. No routing code. No orchestration logic. The LLM reads the tool descriptions and decides what to call.

## How the Agent Decides

When you ask "Which assembly lines need attention?", the agent's reasoning:

1. Calls `discover_data_sources("assembly lines attention anomaly OEE")` → Semantic Layer
2. Gets back: "Use IoT tools (anomaly), Analytics tools (OEE), Equipment tools (status)"
3. Calls `detect_anomaly()` → finds Machine 42 temperature critical
4. Calls `get_oee_trends()` → finds Line 4 OEE dropping
5. Calls `get_equipment_status(line="Line 4")` → gets machine details
6. Synthesizes everything into a severity-ranked response

## Try It

With MCP servers still running from the previous module:

```bash
python -c "
from src.config import AppConfig
from src.identity.models import SARAH_CHEN
from src.agent.agent import ManufacturingInsightsAgent

agent = ManufacturingInsightsAgent(AppConfig())
response = agent.query(SARAH_CHEN, 'Which assembly lines need attention this week?')
print(response)
"
```

You should see a detailed, severity-ranked response that correlates data from IoT sensors, OEE analytics, and equipment records — all synthesized by the agent from multiple MCP tool calls.

{{% notice success %}}
**Checkpoint:** If you get a multi-source synthesized response, your agent is working end-to-end!
{{% /notice %}}

## What's Missing?

The agent works, but it has no access control. Sarah (Plant Manager) and Priya (Technician) would both see the same data. In the next module, we'll add policy enforcement.
