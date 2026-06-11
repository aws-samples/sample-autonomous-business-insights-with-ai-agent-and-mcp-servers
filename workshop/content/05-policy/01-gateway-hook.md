---
title: "Gateway Policy Hook"
weight: 51
---

# Gateway Policy Enforcement

## The Problem

Without access control, any user can query any data. Raj (Line Supervisor for Line 7) could ask about Line 4 — and get answers he shouldn't have access to.

In AgentCore, the **Gateway** intercepts every tool call and evaluates **Cedar policies** before the MCP server is contacted. We replicate this with a Strands `BeforeToolCallEvent` hook.

## The Implementation

Open `src/identity/gateway_hook.py`:

```python
from strands.hooks import BeforeToolCallEvent, HookProvider, HookRegistry

class GatewayPolicyHook(HookProvider):
    """Intercepts every tool call and enforces access policies."""

    def __init__(self, user: UserIdentity, policy_engine: PolicyEngine):
        self.user = user
        self.policy_engine = policy_engine

    def register_hooks(self, registry: HookRegistry, **kwargs):
        registry.add_callback(BeforeToolCallEvent, self._enforce_policy)

    def _enforce_policy(self, event: BeforeToolCallEvent):
        tool_name = event.tool_use["name"]
        tool_input = event.tool_use.get("input", {})

        # Extract policy-relevant parameters
        params = self._extract_policy_params(tool_input)

        # Evaluate against Cedar-style policies
        decision = self.policy_engine.evaluate(self.user, tool_name, params)

        if not decision.allowed:
            # BLOCK the call — MCP server never sees it
            event.cancel_tool = f"[Policy Enforcement] {decision.reason}"
```

## How It's Wired In

```python
# In agent.py
gateway_hook = GatewayPolicyHook(user=user, policy_engine=self.policy_engine)

agent = Agent(
    system_prompt=system_prompt,
    tools=all_tools,
    hooks=[gateway_hook],  # ← Intercepts EVERY tool call
)
```

## Test It

```bash
python -c "
from src.config import AppConfig
from src.identity.models import RAJ_PATEL
from src.agent.agent import ManufacturingInsightsAgent

agent = ManufacturingInsightsAgent(AppConfig())
# Raj asks about Line 4 — which is OUTSIDE his scope (he only has Line 7)
response = agent.query(RAJ_PATEL, 'What is the status of Line 4?')
print(response)
"
```

Expected: The agent explains that Line 4 is outside Raj's authorized scope and offers to query Line 7 instead.

## What Happened Under the Hood

```
1. Agent decides to call get_equipment_status(line="Line 4")
2. BeforeToolCallEvent fires
3. GatewayPolicyHook evaluates: Raj's scope is ["Line 7"]
4. "Line 4" not in scope → DENY
5. event.cancel_tool set → tool call cancelled
6. Agent receives "Access denied" message
7. Agent explains the limitation to the user
```

The Equipment MCP server was **never contacted**. Policy enforcement happened at the Gateway layer.

{{% notice success %}}
**Checkpoint:** If Raj's query about Line 4 is denied and he's told to ask about Line 7, policy enforcement is working!
{{% /notice %}}
