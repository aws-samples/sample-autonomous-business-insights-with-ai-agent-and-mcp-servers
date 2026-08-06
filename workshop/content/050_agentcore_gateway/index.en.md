---
title: "AgentCore Gateway"
weight: 50
---

# AgentCore Gateway — MCP Router & Security Enforcement

In this module, you'll deploy the AgentCore Gateway — the single chokepoint through which every tool call passes. You'll **register all your MCP servers as Lambda tool targets** in the Gateway, configure MCP routing, and understand the request interception pipeline.

## From Local MCP Servers to Gateway

In the earlier modules, you built 4 MCP servers and connected them directly to the Strands Agent:

```
Earlier (local development):
  Agent → Equipment Server (localhost:8001)
  Agent → IoT Server (localhost:8002)
  Agent → Supply Chain Server (localhost:8003)
  Agent → Analytics Server (localhost:8004)
```

Now you're moving to production. Instead of the agent connecting to each MCP server individually, you **register all servers in the Gateway** and the agent connects to a single URL:

```
Production (via Gateway):
  Agent → Gateway (single URL) → Equipment Target (Lambda)
                                → IoT Target (Lambda)
                                → Supply Chain Target (Lambda)
                                → Analytics Target (Lambda)
```

The agent's code changes from connecting to 5 URLs to connecting to 1. The Gateway handles all routing internally.

## What Is the Gateway?

The Gateway is a managed HTTPS endpoint that sits between the agent and your MCP servers. Every tool call flows through it.

## Why Use a Gateway Instead of Direct MCP Connections?

| Concern | Direct MCP (local) | Via Gateway (production) |
|---------|-------------------|--------------------------|
| Security | Auth logic in each server | Centralized Cedar policy enforcement |
| Routing | Agent manages N connections | Single URL, Gateway routes |
| Caching | None | 3-tier: edge, regional, per-session |
| Tool discovery | Agent queries each server | Gateway aggregates all tools |
| Scaling | Each server scales independently | Gateway handles load balancing |
| Observability | Scattered logs | Unified tracing + audit |
| Latency | N round-trips for discovery | Single discovery call, cached |
| Governance | No central control | Interceptor pipeline + policy |

### Gateway Benefits Deep Dive

**3-Tier Caching** — Repeated queries don't hit your data sources:
- **Edge cache (CloudFront)** — Identical requests from any user served at the edge (~5ms)
- **Regional cache (ElastiCache)** — Same tool+params across users within a region (~15ms)
- **Per-session cache (in-microVM)** — Same call within a conversation, instant recall

**Tool Indexing & Discovery** — The Gateway maintains a registry of all registered tool targets. When the agent calls `tools/list`, the Gateway returns a merged, deduplicated list from all targets in one response. No need to query each server.

**Interceptor Pipeline** — Lambda-based hooks that run before/after every tool call:
- Enrich requests with user context (REQUEST interceptor)
- Filter tool visibility by role (RESPONSE interceptor)
- Transform responses (redaction, formatting)

**Deny-by-Default Security** — Cedar policy evaluates before the tool target is invoked. If denied, the MCP server is never contacted. Zero attack surface on your data layer.

**Unified Observability** — Every tool call through the Gateway generates:
- X-Ray trace (end-to-end latency breakdown)
- CloudWatch log (policy decision + request/response)
- Metrics (call count, latency p50/p99, deny rate)

```
Agent ─────────────► Gateway ─────────────► Lambda Tool Targets
         HTTPS              Policy check           MCP Servers
         (single URL)       + caching              (multiple)
                            + indexing
                            + observability
```

The agent only knows the Gateway URL. It cannot bypass the Gateway to reach MCP servers directly.

## The Request Pipeline

Every tool call passes through this pipeline in order:

```
┌───────────────────────────────────────────────────────────────────┐
│                    Gateway Request Pipeline                         │
├───────────────────────────────────────────────────────────────────┤
│                                                                    │
│  1. JWT Validation (built-in)                                      │
│     → Verify token signature against Cognito JWKS                  │
│     → Reject expired or malformed tokens                           │
│                                                                    │
│  2. REQUEST Interceptor (Lambda)                                   │
│     → Decode JWT claims (role, scope attributes)                   │
│     → Inject user_context into tool arguments                      │
│     → Set x-user-role header for response interceptor              │
│                                                                    │
│  3. Policy Engine (Cedar)                                          │
│     → Evaluate permit/forbid rules against enriched request        │
│     → ALLOW → continue to tool target                              │
│     → DENY → return policy denial to agent (tool never called)     │
│                                                                    │
│  4. Tool Target (Lambda)                                           │
│     → Execute MCP tool logic                                       │
│     → Query data source (Aurora, Timestream, Redshift, etc.)       │
│     → Return result                                                │
│                                                                    │
│  5. RESPONSE Interceptor (Lambda)                                  │
│     → For tools/list: filter tools by user role                    │
│     → For tools/call: pass through (already authorized)            │
│                                                                    │
└───────────────────────────────────────────────────────────────────┘
```

## Step 1: Register MCP Servers as Gateway Tool Targets

This is the key step — you're taking the MCP servers you built in Module 3 and **registering them in the Gateway** as Lambda tool targets. Each local server becomes a Lambda function that the Gateway routes to:

| Local MCP Server (Module 3) | → | Gateway Tool Target |
|-----------------------------|---|---------------------|
| `equipment_server.py` (port 8001) | → | `MfgInsights-EquipmentTools` (Lambda) |
| `iot_telemetry_server.py` (port 8002) | → | `MfgInsights-IoTTools` (Lambda) |
| `supply_chain_server.py` + `analytics_server.py` (ports 8003-8004) | → | `MfgInsights-AnalyticsTools` (Lambda) |

The deployment script packages each server's logic into a Lambda and registers it with the Gateway:

```bash
python deploy/agentcore/setup_gateway.py --region us-east-1
```

:::alert{type="info"}
If you haven't deployed infrastructure yet, this step creates the Lambda functions, IAM roles, and the Gateway resource. It takes about 2-3 minutes.
:::

## Step 1b: The Registration Code — How It Works

Open `deploy/agentcore/setup_gateway.py`. The registration happens in three stages:

**Stage 1: Define tool schemas** — Each MCP server's tools are declared with full JSON Schema:

```python
# deploy/agentcore/setup_gateway.py

TOOL_SCHEMAS = {
    "EquipmentTarget": [
        {
            "name": "get_equipment_status",
            "description": "Get current status and metadata for equipment on an assembly line.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "line": {"type": "string", "description": "Assembly line (e.g., 'Line 4')"},
                    "machine_id": {"type": "integer", "description": "Machine ID number"},
                    "plant": {"type": "string", "description": "Plant identifier"},
                },
            },
        },
        {
            "name": "get_maintenance_history",
            "description": "Get maintenance history for a specific machine.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "machine_id": {"type": "integer", "description": "Machine ID"},
                },
                "required": ["machine_id"],
            },
        },
        # ... get_shared_infrastructure
    ],
    "IoTTarget": [
        {
            "name": "get_sensor_readings",
            "description": "Get sensor readings (temperature, vibration, pressure) for a machine.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "machine_id": {"type": "integer"},
                    "metric": {"type": "string", "enum": ["temperature", "vibration", "pressure"]},
                    "days": {"type": "integer", "description": "Days of history (default 7)"},
                },
                "required": ["machine_id"],
            },
        },
        # ... detect_anomaly
    ],
    "AnalyticsTarget": [
        # ... get_oee_trends, get_quality_metrics, check_parts_inventory, get_supplier_lead_times
    ],
}
```

**Stage 2: Create Lambda targets** — Each target becomes a Lambda function:

```python
def create_tool_lambda(lambda_client, iam_client, function_name, target_name, region):
    """Create a Lambda function that handles tool invocations for a domain."""
    lambda_code = '''
import json

def lambda_handler(event, context):
    """Handle tool invocation from AgentCore Gateway."""
    tool_name = event.get("name", "")
    arguments = event.get("arguments", {})
    
    # Remove injected user_context before passing to tool logic
    user_context = arguments.pop("user_context", None)
    
    # Log for audit trail
    print(f"Tool call: {tool_name}, user: {user_context.get('username', 'unknown')}")
    
    # Route to tool implementation (queries Aurora/Timestream/Redshift)
    return {"status": "success", "tool": tool_name, "arguments": arguments}
'''
    # ... creates IAM role, zips code, deploys Lambda
```

**Stage 3: Register targets with the Gateway** — The Gateway config maps target names to Lambda ARNs + tool schemas:

```python
gateway_config = {
    "region": args.region,
    "gateway_role_arn": gateway_role_arn,
    "identity": {
        "user_pool_id": identity_config["user_pool_id"],
        "client_id": identity_config["client_id"],
    },
    "targets": {
        target_name: {
            "lambda_arn": arn,
            "tool_schema": TOOL_SCHEMAS[target_name],
        }
        for target_name, arn in lambda_arns.items()
    },
}
```

This config tells the Gateway: "When the agent calls `get_equipment_status`, route it to `MfgInsights-EquipmentTarget` Lambda. When it calls `detect_anomaly`, route to `MfgInsights-IoTTarget` Lambda."

## Step 1c: Trade-offs — Direct MCP vs Gateway Registration

| Consideration | Direct MCP (dev mode) | Gateway Registration (production) |
|---------------|----------------------|-----------------------------------|
| **Setup complexity** | None — just start servers | Need Lambda + IAM + Gateway config |
| **Latency** | ~5ms (localhost) | ~50ms (Lambda cold) / ~15ms (warm) |
| **Security** | No enforcement | Cedar + interceptors + JWT |
| **Scaling** | Manual (process per server) | Auto (Lambda concurrency) |
| **Caching** | None | 3-tier (62% hit rate = big savings) |
| **Cost (idle)** | Always running | $0 (Lambda pay-per-use) |
| **Cost (busy)** | Fixed compute | ~$0.50/1000 requests |
| **Observability** | stdout logs | X-Ray + CloudWatch + metrics |
| **Tool discovery** | Agent queries N servers | One `tools/list` call to Gateway |
| **Adding new tools** | Restart server + agent | Register target, no agent restart |
| **Access control** | In-process hook (soft) | Cedar at Gateway (hard, deterministic) |

**When to use Direct MCP (dev mode):**
- Local development and debugging
- Rapid iteration on tool logic
- No AWS infrastructure available
- Single-user testing

**When to use Gateway Registration (production):**
- Multi-user access with different scopes
- Need audit trail and policy enforcement
- Production workloads that need scaling
- When tool results should be cached
- When you need to add/remove tools without agent restarts

## Step 1d: What Happens When You Register a New MCP Server

Adding a 5th data source (e.g., Quality Inspections from OpenSearch) requires:

```python
# 1. Add tool schema to TOOL_SCHEMAS
TOOL_SCHEMAS["QualityTarget"] = [
    {
        "name": "search_defect_reports",
        "description": "Semantic search across quality inspection documents.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "line": {"type": "string"},
            },
            "required": ["query"],
        },
    },
]

# 2. Create Lambda
arn = create_tool_lambda(lambda_client, iam, "MfgInsights-QualityTarget", "QualityTarget")

# 3. Re-run setup_gateway.py — Gateway config is regenerated
#    The Gateway now routes "search_defect_reports" to the new Lambda
```

**Zero changes to agent code.** The agent discovers the new tool via `tools/list` on the next query. Cedar policies auto-apply if the tool has `line` or `machine_id` parameters.

Expected output:

```
✅ Created Lambda: MfgInsights-EquipmentTools
✅ Created Lambda: MfgInsights-IoTTools
✅ Created Lambda: MfgInsights-AnalyticsTools
✅ Created IAM Role: MfgInsights-Gateway-Role
✅ Created Gateway: <your-gateway-id>
   URL: https://<your-gateway-id>.gateway.bedrock-agentcore.us-east-1.amazonaws.com
✅ Created Test Gateway (no auth): <your-test-gateway-id>
✅ All Lambda targets: READY
```

## Step 2: Understand Tool Target Mapping

The Gateway maps tool names to Lambda targets using prefixes:

| Tool Name | Lambda Target | Data Source |
|-----------|---------------|-------------|
| `get_equipment_status` | MfgInsights-EquipmentTools | Aurora PostgreSQL |
| `get_maintenance_history` | MfgInsights-EquipmentTools | Aurora PostgreSQL |
| `get_shared_infrastructure` | MfgInsights-EquipmentTools | S3 |
| `get_sensor_readings` | MfgInsights-IoTTools | Timestream |
| `detect_anomaly` | MfgInsights-IoTTools | Timestream |
| `check_parts_inventory` | MfgInsights-AnalyticsTools | Redshift |
| `get_oee_trends` | MfgInsights-AnalyticsTools | Redshift |
| `get_quality_metrics` | MfgInsights-AnalyticsTools | OpenSearch |

Each Lambda receives a standard MCP `tools/call` payload and returns a standard MCP response.

## Step 3: Explore a Lambda Target Implementation

Open `deploy/agentcore/lambda_functions/request_interceptor.py` to see what the REQUEST interceptor does:

```python
def lambda_handler(event, context):
    """REQUEST Interceptor: Enrich tool call with user identity context."""

    # Extract JWT from Authorization header
    token = event["headers"].get("authorization", "").replace("Bearer ", "")
    claims = decode_jwt_claims(token)

    # Extract scope attributes from Cognito custom claims
    user_context = {
        "username": claims.get("cognito:username"),
        "groups": claims.get("cognito:groups", []),
        "role": claims.get("custom:role"),
        "line_scope": claims.get("custom:line_scope", ""),
        "plant_scope": claims.get("custom:plant_scope", ""),
        "equipment_scope": claims.get("custom:equipment_scope", ""),
    }

    # Inject into the tool call arguments (for Cedar to evaluate)
    body = json.loads(event["body"])
    if "params" in body and "arguments" in body["params"]:
        body["params"]["arguments"]["_user_context"] = user_context

    # Set header for response interceptor
    event["headers"]["x-user-role"] = user_context["role"]

    return {
        "statusCode": 200,
        "body": json.dumps(body),
        "headers": event["headers"],
    }
```

{{% notice info %}}
The REQUEST interceptor runs **before** Cedar policy evaluation. It enriches the request so Cedar can check parameters against user scope. Without it, Cedar wouldn't know who the user is.
{{% /notice %}}

## Step 4: Test the Gateway Directly

Use curl to test the Gateway (using the test gateway with no auth for development):

```bash
# List available tools
curl -s -X POST \
  "https://<your-test-gateway-id>.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python -m json.tool
```

You should see all registered tools with their schemas.

```bash
# Call a tool
curl -s -X POST \
  "https://<your-test-gateway-id>.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "method":"tools/call",
    "params":{"name":"get_equipment_status","arguments":{"line":"Line 4"}},
    "id":2
  }' | python -m json.tool
```

{{% notice warning %}}
The test gateway has no auth or policy enforcement. It's for development validation only. The production gateway requires a valid JWT and enforces Cedar policies.
{{% /notice %}}

## Step 5: Understand the Response Interceptor

Open `deploy/agentcore/lambda_functions/response_interceptor.py`:

```python
def lambda_handler(event, context):
    """RESPONSE Interceptor: Filter tools/list by user role."""

    body = json.loads(event["body"])
    user_role = event["headers"].get("x-user-role", "")

    # Only filter tools/list responses (not tools/call)
    if body.get("result", {}).get("tools"):
        visible_tools = filter_tools_for_role(body["result"]["tools"], user_role)
        body["result"]["tools"] = visible_tools

    return {"statusCode": 200, "body": json.dumps(body)}
```

Why filter the tool list? If the LLM sees 12 tools but can only use 8, it might attempt (and fail) to call unauthorized ones. Filtering means the LLM never even considers tools it can't use.

| Role | Visible Tools | Hidden Tools |
|------|---------------|--------------|
| plant_manager | All 12 | None |
| line_supervisor | 8 tools | maintenance_history, sensor by machine |
| maintenance_technician | 8 tools | OEE, quality, shared_infra |

## Step 6: Verify Gateway Status

```bash
aws bedrock-agentcore get-gateway \
  --gateway-id <your-gateway-id> \
  --region us-east-1
```

Expected: `"status": "READY"`

Check Lambda targets are healthy:

```bash
aws lambda get-function --function-name MfgInsights-EquipmentTools --region us-east-1 \
  --query "Configuration.State" --output text
```

Expected: `Active`

## Gateway Architecture Summary

```
                              ┌────────────────────┐
                              │   Agent (Runtime)   │
                              └─────────┬──────────┘
                                        │ tools/call or tools/list
                                        ▼
┌───────────────────────────────────────────────────────────────────┐
│                         GATEWAY                                    │
│  ┌──────────┐  ┌─────────────┐  ┌────────┐  ┌─────────────────┐ │
│  │   JWT    │→ │   REQUEST   │→ │ CEDAR  │→ │  TOOL TARGET    │ │
│  │ Validate │  │ Interceptor │  │ POLICY │  │  (Lambda)       │ │
│  └──────────┘  └─────────────┘  └────────┘  └────────┬────────┘ │
│                                                       │          │
│                                              ┌────────▼────────┐ │
│                                              │    RESPONSE     │ │
│                                              │  Interceptor    │ │
│                                              └─────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
```

## Key Takeaways

1. **Single chokepoint** — All tool calls pass through the Gateway; no bypass possible
2. **Interceptor pipeline** — REQUEST enriches, Cedar evaluates, RESPONSE filters
3. **Tool targets are Lambda** — Each MCP server becomes a serverless function
4. **Deny before execute** — If Cedar says no, the Lambda target is never invoked
5. **Test gateway for dev** — Separate no-auth gateway for development validation
6. **Agent only knows Gateway URL** — Cannot reach MCP servers directly

## Next Steps

The Gateway validates JWTs, but where do those tokens come from? In the next module, you'll set up **AgentCore Identity** with Cognito, creating users with role-based scope attributes.
