+++
title = "AgentCore Gateway"
weight = 60
+++

# AgentCore Gateway — MCP Router & Security Enforcement

In this module, you'll deploy the AgentCore Gateway — the single chokepoint through which every tool call passes. You'll set up Lambda tool targets, configure MCP routing, and understand the request interception pipeline.

## What Is the Gateway?

The Gateway is a managed HTTPS endpoint that sits between the agent and your MCP servers. Every tool call flows through it. It provides:

- **MCP routing** — Routes `tools/call` to the correct Lambda target based on tool name
- **JWT validation** — Verifies user tokens before any processing
- **Request interception** — Lambda-based enrichment of requests
- **Policy enforcement** — Cedar evaluation before tool execution
- **Response interception** — Filtering/transformation of responses
- **3-tier caching** — Edge (CloudFront), regional (ElastiCache), per-session

```
Agent ─────────────► Gateway ─────────────► Lambda Tool Targets
         HTTPS              Policy check           MCP Servers
         (single URL)       before forward         (multiple)
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

## Step 1: Deploy Lambda Tool Targets

Each MCP server becomes a Lambda function in production. The script creates three Lambda targets:

```bash
python deploy/agentcore/setup_gateway.py --region us-east-1
```

{{% notice note %}}
If you haven't deployed infrastructure yet, this step creates the Lambda functions, IAM roles, and the Gateway resource. It takes about 2-3 minutes.
{{% /notice %}}

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
