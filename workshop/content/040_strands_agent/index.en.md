+++
title = "Building the Strands Agent"
weight = 40
+++

# Building the Strands Agent

In this module, you'll connect a Strands Agent to your running MCP servers and see it autonomously reason across all data sources to answer manufacturing questions.

## How the Agent Works

The Strands Agent has three components:

1. **System prompt** — Defines the agent's identity, capabilities, and behavior
2. **Tools** — Collected from all connected MCP servers
3. **LLM** — Claude Sonnet on Amazon Bedrock, which reasons about which tools to call

```python
from strands import Agent

agent = Agent(
    system_prompt=prompt,    # Who am I, what do I know
    tools=all_tools,         # Flat list from all MCP servers
    hooks=[policy_hook],     # Pre-tool-call policy enforcement
)

response = agent("Which assembly lines need attention this week?")
```

The LLM sees ALL tools from ALL servers as a flat list. It decides which to call, in what order, based on the user's question. No routing logic needed.

## Step 1: Explore the Agent Code

Open `src/agent/agent.py`. The key method is how it connects to MCP servers:

```python
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

# Connect to all MCP servers
server_urls = [
    "http://localhost:8001/mcp",  # Equipment
    "http://localhost:8002/mcp",  # IoT Telemetry
    "http://localhost:8003/mcp",  # Supply Chain
    "http://localhost:8004/mcp",  # Analytics
    "http://localhost:8005/mcp",  # Semantic Layer
]

mcp_clients = []
all_tools = []

for url in server_urls:
    client = MCPClient(lambda url=url: streamablehttp_client(url))
    client.start()
    mcp_clients.append(client)
    all_tools.extend(client.list_tools_sync())
```

After this runs, `all_tools` contains every tool from every server—roughly 12 tools total. The agent sees them all.

## Step 2: Understand the System Prompt

Open `src/agent/prompts.py`. The prompt template injects:

- **User identity** — Name, role, scope (injected at runtime)
- **Memory context** — Previous session insights
- **Behavioral instructions** — How to handle denied access, how to synthesize

```python
SYSTEM_PROMPT = """You are a Manufacturing Insights Agent deployed on Amazon Bedrock AgentCore.

Current User: {user_name} ({user_role})
Access Scope: {user_scope}

You have access to tools from multiple MCP servers covering:
- Equipment status and maintenance history
- IoT sensor telemetry and anomaly detection
- Supply chain inventory and supplier lead times
- Production analytics (OEE) and quality metrics
- Semantic layer for data source discovery

When answering questions:
1. Use the semantic layer to understand which data sources are relevant
2. Call multiple tools to build a complete picture
3. Correlate findings across systems (e.g., anomalies + maintenance + parts)
4. If a tool call is denied by policy, explain the scope limitation to the user

{memory_context}
"""
```

## Step 3: Run the Agent in CLI Mode

With your MCP servers still running in another terminal, start the interactive CLI:

```bash
python -m src.main
```

You'll see a persona selection menu:

```
╔══════════════════════════════════════════════════════════╗
║  Manufacturing Insights Agent                           ║
║  Powered by Strands + Amazon Bedrock AgentCore          ║
╠══════════════════════════════════════════════════════════╣
║  Select a persona:                                      ║
║  1. Sarah Chen — Plant Manager (full access)            ║
║  2. Raj Patel — Line Supervisor (Line 7)                ║
║  3. Priya Nair — Maintenance Technician (Machine 41-45) ║
╚══════════════════════════════════════════════════════════╝
```

Select **1 (Sarah Chen)** and ask:

```
> Which assembly lines need attention this week?
```

Watch the agent's reasoning. It will:
1. Call `detect_anomaly()` — finds Machine 42 temperature and vibration elevated
2. Call `get_oee_trends()` — sees Line 4 availability dropping, Line 9 throughput dipping
3. Call `get_equipment_status(line="Line 4")` — discovers Machine 42 at 130% capacity
4. Call `get_shared_infrastructure(line="Line 4")` — finds shared coolant loop with Line 9
5. Synthesize a prioritized response

## Step 4: Try Cross-System Correlation

Still as Sarah, ask:

```
> Why is Line 4 availability dropping? Is it related to Line 9's throughput dip?
```

The agent should correlate:
- IoT anomaly on Machine 42 (bearing vibration trending up)
- Equipment history: bearing replaced 8 months ago, running at 130% capacity
- Shared coolant loop A serves both Line 4 and Line 9
- Parts inventory: bearings below reorder point

This is the power of multi-tool reasoning—no pre-built workflow needed.

## Step 5: Try the Web UI

For a richer experience, launch the Streamlit UI:

```bash
streamlit run src/demo_ui.py
```

Open **http://localhost:8501** in your browser. The UI provides:
- Persona selector with visible access scopes
- Chat interface with markdown-rendered responses
- Clickable sample queries per persona
- Real-time tool call visualization

{{% notice tip %}}
The Streamlit UI shows which tools the agent called and in what order. This is useful for understanding the LLM's reasoning process.
{{% /notice %}}

## Step 6: Observe Memory in Action

In the same session, ask a follow-up:

```
> Has it gotten worse since last week?
```

The agent uses **session memory** to know "it" refers to Machine 42's vibration. It surfaces the previous reading (3.8 mm/s from last week's inspection) and compares with current (4.5 mm/s) to report an 18% increase.

## Understanding the Agent Loop

```
┌─────────────────────────────────────────────────────────┐
│  Agent Reasoning Loop (one iteration per tool call)      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. LLM receives: user query + system prompt + tools     │
│  2. LLM decides: "I need to call detect_anomaly()"       │
│  3. Hook fires: policy_hook.before_tool_call()           │
│     → Policy says ALLOW? Continue.                       │
│     → Policy says DENY? Return deny message to LLM.     │
│  4. Tool executes: MCP server returns result             │
│  5. LLM receives tool result                             │
│  6. LLM decides: "I need more data" → go to step 2      │
│                   OR "I have enough" → synthesize answer │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

The loop continues until the LLM decides it has enough information to answer. For complex queries, this might mean 4-6 tool calls across different servers.

## Key Takeaways

1. **One agent, many tools** — All MCP server tools appear as a flat list; the LLM picks
2. **No orchestration code** — The LLM's reasoning replaces hardcoded workflows
3. **Memory enables follow-ups** — Session context makes conversations natural
4. **Hooks intercept tool calls** — Policy enforcement happens before execution (next module)
5. **Cross-system synthesis** — The real value is correlation across data sources

## Next Steps

The agent works, but right now all users see all data. In the next module, you'll implement Cedar-based access control so each persona only sees data within their authorized scope.
