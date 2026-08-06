+++
title = "AgentCore Runtime"
weight: 50
+++

# AgentCore Runtime — Serverless Agent Execution

In this module, you'll learn how Amazon Bedrock AgentCore Runtime provides isolated, serverless compute for your agent. You'll deploy the Strands Agent to a Firecracker microVM and understand how session isolation works.

## What Is AgentCore Runtime?

AgentCore Runtime is the compute layer that hosts your agent code. Instead of managing EC2 instances or containers, you deploy your Python agent directly and Runtime handles:

- **Firecracker microVMs** — Each user session runs in its own isolated microVM
- **Sub-50ms cold start** — Lightweight VMs spin up nearly instantly
- **Auto-scale to zero** — No cost when idle, scales up on demand
- **Session isolation** — One user's data and context cannot leak to another
- **Direct code deployment** — Upload a Python zip; no Docker required

```
┌────────────────────────────────────────────────────────────┐
│  AgentCore Runtime                                          │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  microVM     │  │  microVM     │  │  microVM     │     │
│  │  Sarah's     │  │  Raj's       │  │  Priya's     │     │
│  │  session     │  │  session     │  │  session     │     │
│  │              │  │              │  │              │     │
│  │ Strands Agent│  │ Strands Agent│  │ Strands Agent│     │
│  │ + context    │  │ + context    │  │ + context    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                             │
│  Each session: isolated memory, isolated file system,       │
│  isolated network namespace. No cross-session leakage.      │
└────────────────────────────────────────────────────────────┘
```

## Why Not Just Run on Lambda or ECS?

| Concern | Lambda/ECS | AgentCore Runtime |
|---------|------------|-------------------|
| Session isolation | Shared execution context | Dedicated microVM per session |
| State leakage | Possible between invocations | Impossible (VM destroyed) |
| Agent lifecycle | You manage sessions | Managed session lifecycle |
| Cold start | 100-500ms (Lambda) | <50ms (Firecracker) |
| Deployment | Docker image or zip | Python zip (simpler) |
| Scaling | Per-request | Per-session |

The key difference: **session-level isolation**. A multi-turn conversation stays in one microVM; another user's conversation is in a completely separate VM.

## Step 1: Understand the Deployment Model

In production, your agent code is packaged as a Python zip and deployed to Runtime:

```
your-agent/
├── agent.py          # Entry point — creates Strands Agent
├── prompts.py        # System prompt templates
├── requirements.txt  # Dependencies (installed at deploy time)
└── config.py         # Runtime configuration
```

The entry point connects to the **Gateway** (not directly to MCP servers):

```python
# In production: agent connects to Gateway URL only
from strands import Agent
from strands.tools.mcp.mcp_client import MCPClient

# Single Gateway URL — Gateway handles routing to all MCP servers
gateway_url = os.environ["AGENTCORE_GATEWAY_URL"]

mcp_client = MCPClient(lambda: streamablehttp_client(gateway_url))
mcp_client.start()
tools = mcp_client.list_tools_sync()

agent = Agent(
    system_prompt=build_prompt(user_context),
    tools=tools,
    # No policy hook needed — Gateway enforces policy server-side
)
```

{{% notice info %}}
In local simulation mode (`SIMULATION_MODE=true`), the agent connects to individual MCP servers and uses a local policy hook. In production (`SIMULATION_MODE=false`), it connects only to the Gateway URL.
{{% /notice %}}

## Step 2: Explore How Sessions Work

Each invocation of the agent gets a session context from Runtime:

```python
# Runtime injects these into the agent's environment
session_context = {
    "session_id": "sess-abc123",           # Unique per conversation
    "user_id": "sarah.chen",               # From Identity (JWT)
    "user_attributes": {                    # From Cognito/OAuth
        "role": "plant_manager",
        "line_scope": "Line 1,...,Line 12",
        "plant_scope": "Plant 1,Plant 2,Plant 3"
    },
    "memory_namespace": "user/sarah.chen",  # Memory isolation
    "ttl_seconds": 3600,                   # Session expires after 1hr
}
```

When a session ends (timeout or explicit close), the microVM is destroyed. Any in-memory state, temp files, or cached data are gone.

## Step 3: Deploy to Runtime (Simulated)

For this workshop, we simulate the deployment flow. In a real deployment:

```bash
# Package the agent
cd src/agent
zip -r agent_package.zip .

# Deploy to AgentCore Runtime
aws bedrock-agentcore create-agent-runtime \
  --agent-name "manufacturing-insights" \
  --runtime-config '{
    "entryPoint": "agent.py",
    "environment": {
      "AGENTCORE_GATEWAY_URL": "https://your-gateway-id.gateway.bedrock-agentcore.us-east-1.amazonaws.com",
      "BEDROCK_MODEL_ID": "us.anthropic.claude-sonnet-4-20250514-v1:0"
    }
  }' \
  --code-zip fileb://agent_package.zip \
  --region us-east-1
```

The response gives you a Runtime endpoint:

```json
{
  "agentRuntimeId": "art-abc123",
  "status": "READY",
  "endpoint": "https://art-abc123.runtime.bedrock-agentcore.us-east-1.amazonaws.com"
}
```

## Step 4: Understand the Request Flow

When a user sends a query, here's what happens at the Runtime level:

```
User → Runtime endpoint
         │
         ▼
┌─────────────────────────────────────────────┐
│  1. Runtime receives request                 │
│  2. Checks: existing session for this user?  │
│     YES → route to existing microVM          │
│     NO  → spin up new microVM (<50ms)        │
│  3. Inject session_context into environment  │
│  4. Agent code executes                      │
│  5. Agent calls Gateway for tool use         │
│  6. Agent returns response                   │
│  7. Session kept alive (TTL countdown)       │
└─────────────────────────────────────────────┘
```

## Step 5: Test Session Isolation Locally

To see isolation in action, run the demo UI and open it in **two browser tabs**:

```bash
streamlit run src/demo_ui.py
```

- Tab 1: Select **Sarah Chen**, ask "Which lines need attention?"
- Tab 2: Select **Raj Patel**, ask "What's Line 7 status?"

Each tab maintains its own session. Sarah's conversation context doesn't bleed into Raj's, and vice versa. In production, this isolation is hardware-enforced by separate Firecracker microVMs.

## Step 6: Verify Session Memory Isolation

In Tab 1 (Sarah), ask a follow-up:

```
> Tell me more about Machine 42
```

The agent uses Sarah's session context to know you were just discussing Line 4 anomalies.

In Tab 2 (Raj), ask:

```
> Tell me more about Machine 42
```

Raj gets a **policy denial** because Machine 42 is outside his scope. Even if Sarah's session discussed it, that context doesn't leak to Raj's session.

## Runtime Configuration Options

| Config | Purpose | Default |
|--------|---------|---------|
| `ttl_seconds` | Session timeout | 3600 (1 hour) |
| `max_concurrent_sessions` | Per-agent limit | 100 |
| `memory_mb` | microVM memory | 512 |
| `timeout_seconds` | Per-request timeout | 300 |
| `environment` | Env vars injected | — |

## Key Takeaways

1. **Firecracker microVMs** — Hardware-level isolation per user session
2. **No Docker needed** — Deploy Python code directly as a zip
3. **Sub-50ms cold start** — Users don't wait for container initialization
4. **Scale to zero** — No cost when nobody's using the agent
5. **Session lifecycle managed** — Runtime handles create/reuse/destroy
6. **Agent connects to Gateway only** — Not directly to MCP servers in production

## Next Steps

Your agent runs in an isolated Runtime. But how does it reach the MCP servers? In the next module, you'll set up the **AgentCore Gateway** — the MCP router and security enforcement point.
