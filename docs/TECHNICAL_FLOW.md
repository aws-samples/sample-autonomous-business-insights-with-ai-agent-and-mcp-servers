# Technical Flow: Persona-Based Access Control in AgentCore

## Use Case: Manufacturing Plant Operations

A precision manufacturing company with 3 plants, 12 assembly lines, and 60 machines needs a single AI agent that serves all employees while enforcing strict data boundaries.

### Business Requirement

> "The Plant Manager sees everything. The Line Supervisor sees only Line 7. The Maintenance Tech sees only their assigned machines. Same agent. Same question interface. Different data access."

### Deployed Infrastructure (LIVE on your AWS Account)

| Component | AWS Resource | Identifier |
|-----------|-------------|------------|
| Gateway | AgentCore Gateway (MCP) | `your-gateway-id` |
| Gateway URL | HTTPS endpoint | `https://your-gateway-id.gateway.bedrock-agentcore.us-east-1.amazonaws.com` |
| Policy Engine | AgentCore Policy (Cedar) | `your-policy-engine-id` |
| Cedar Policies | 3 rules (permit_all + 2 forbid) | ENFORCE mode |
| Identity | Cognito User Pool | `us-east-1_EXAMPLE` |
| Tool: Equipment | Lambda | `MfgInsights-EquipmentTools` |
| Tool: IoT | Lambda | `MfgInsights-IoTTools` |
| Tool: Analytics | Lambda | `MfgInsights-AnalyticsTools` |
| IAM Role | Gateway execution | `MfgInsights-Gateway-Role` |

---

## Sequence Diagrams

### Scenario 1: ALLOWED — Line Supervisor Asks About Their Line (Line 7)

```
┌──────┐     ┌──────────┐     ┌───────────┐     ┌──────────┐     ┌─────────┐     ┌──────────┐
│ Raj  │     │ Cognito  │     │   Agent   │     │ Gateway  │     │ Policy  │     │ MCP Tool │
│      │     │(Identity)│     │ (Strands) │     │(Intercept│     │ (Cedar) │     │(Analytics│
└──┬───┘     └────┬─────┘     └─────┬─────┘     └────┬─────┘     └────┬────┘     └────┬─────┘
   │              │                  │                 │                │               │
   │──Login──────>│                  │                 │                │               │
   │              │                  │                 │                │               │
   │<─JWT─────────│                  │                 │                │               │
   │  {role:"line_supervisor",       │                 │                │               │
   │   line_scope:"Line 7",         │                 │                │               │
   │   plant_scope:"Plant 2"}       │                 │                │               │
   │              │                  │                 │                │               │
   │──"What's the OEE for Line 7?"──>                 │                │               │
   │              │                  │                 │                │               │
   │              │    LLM Reasons:  │                 │                │               │
   │              │    "Need OEE for │                 │                │               │
   │              │     Line 7"      │                 │                │               │
   │              │                  │                 │                │               │
   │              │                  │──get_oee_trends(line="Line 7")──>│               │
   │              │                  │                 │                │               │
   │              │                  │                 │──REQUEST       │               │
   │              │                  │                 │  Interceptor:  │               │
   │              │                  │                 │  Decode JWT    │               │
   │              │                  │                 │  Inject context│               │
   │              │                  │                 │                │               │
   │              │                  │                 │──evaluate(     │               │
   │              │                  │                 │  role=line_sup,     │               │
   │              │                  │                 │  line="Line 7")│               │
   │              │                  │                 │                │               │
   │              │                  │                 │  Cedar checks: │               │
   │              │                  │                 │  "Line 7" in   │               │
   │              │                  │                 │  line_scope?   │               │
   │              │                  │                 │  YES → no      │               │
   │              │                  │                 │  forbid match  │               │
   │              │                  │                 │                │               │
   │              │                  │                 │<──ALLOW────────│               │
   │              │                  │                 │                │               │
   │              │                  │                 │──Execute tool──────────────────>│
   │              │                  │                 │                │               │
   │              │                  │                 │<─OEE data: Line 7, 4 weeks─────│
   │              │                  │                 │                │               │
   │              │                  │<──OEE data──────│                │               │
   │              │                  │                 │                │               │
   │              │    LLM synthesizes response        │                │               │
   │              │                  │                 │                │               │
   │<─"Line 7 OEE: 82.3% this week, down 3.1% from last week..."      │               │
   │              │                  │                 │                │               │
```

### Scenario 2: DENIED — Line Supervisor Asks About Line 4 (Not Their Line)

```
┌──────┐     ┌───────────┐     ┌──────────┐     ┌─────────┐     ┌──────────┐
│ Raj  │     │   Agent   │     │ Gateway  │     │ Policy  │     │ MCP Tool │
│      │     │ (Strands) │     │(Intercept│     │ (Cedar) │     │(Analytics│
└──┬───┘     └─────┬─────┘     └────┬─────┘     └────┬────┘     └────┬─────┘
   │               │                 │                │               │
   │──"Show equipment status Line 4"─>                │               │
   │               │                 │                │               │
   │         LLM Reasons:            │                │               │
   │         "Need equipment         │                │               │
   │          for Line 4"            │                │               │
   │               │                 │                │               │
   │               │──get_equipment_status(line="Line 4")──>          │
   │               │                 │                │               │
   │               │                 │──REQUEST       │               │
   │               │                 │  Interceptor:  │               │
   │               │                 │  JWT → context │               │
   │               │                 │                │               │
   │               │                 │──evaluate(     │               │
   │               │                 │  role=line_sup,     │               │
   │               │                 │  line="Line 4")│               │
   │               │                 │                │               │
   │               │                 │  Cedar checks: │               │
   │               │                 │  "Line 4" in   │               │
   │               │                 │  ["Line 7"]?   │               │
   │               │                 │  NO → forbid   │               │
   │               │                 │  MATCHES       │               │
   │               │                 │                │               │
   │               │                 │<──DENY─────────│               │
   │               │                 │  "Access denied│               │
   │               │                 │   Line 4 not   │      ╔══════════════╗
   │               │                 │   authorized"  │      ║ MCP SERVER   ║
   │               │                 │                │      ║ NEVER CALLED ║
   │               │<──"[Policy] Access denied..."────│      ╚══════════════╝
   │               │                 │                │               │
   │         LLM reads deny,         │                │               │
   │         adjusts response        │                │               │
   │               │                 │                │               │
   │<─"I don't have access to Line 4. My scope is Line 7.             │
   │   Would you like me to show Line 7 equipment status instead?"    │
   │               │                 │                │               │
```

### Scenario 3: DENIED — Maintenance Tech Asks About Machine 72 (Not Assigned)

```
┌──────┐     ┌───────────┐     ┌──────────┐     ┌─────────┐     ┌──────────┐
│MaintT│     │   Agent   │     │ Gateway  │     │ Policy  │     │ IoT MCP  │
│      │     │ (Strands) │     │(Intercept│     │ (Cedar) │     │(Telemetry│
└──┬───┘     └─────┬─────┘     └────┬─────┘     └────┬────┘     └────┬─────┘
   │               │                 │                │               │
   │──"Check vibration on Machine 72"──>              │               │
   │               │                 │                │               │
   │         LLM Reasons:            │                │               │
   │         "Need sensor data       │                │               │
   │          for machine 72"        │                │               │
   │               │                 │                │               │
   │               │──get_sensor_readings(machine_id=72)──>           │
   │               │                 │                │               │
   │               │                 │──REQUEST       │               │
   │               │                 │  Interceptor:  │               │
   │               │                 │  role=maint_   │               │
   │               │                 │  tech          │               │
   │               │                 │  equipment=    │               │
   │               │                 │  [41-45]       │               │
   │               │                 │                │               │
   │               │                 │──evaluate(     │               │
   │               │                 │  role=maint_tech,   │               │
   │               │                 │  machine=72)   │               │
   │               │                 │                │               │
   │               │                 │  Cedar checks: │               │
   │               │                 │  role=tech AND │               │
   │               │                 │  "Machine 72"  │               │
   │               │                 │  NOT in scope  │               │
   │               │                 │  [41,42,43,    │               │
   │               │                 │   44,45]       │               │
   │               │                 │  → forbid      │               │
   │               │                 │                │      ╔══════════════╗
   │               │                 │<──DENY─────────│      ║ IoT SERVER   ║
   │               │                 │                │      ║ NEVER CALLED ║
   │               │<──"[Policy] Not assigned..."─────│      ╚══════════════╝
   │               │                 │                │               │
   │<─"I'm not assigned to Machine 72. I can check Machines 41-45.   │
   │   Would you like vibration data for Machine 42?"                 │
   │               │                 │                │               │
```

### Scenario 4: Plant Manager's Cross-System Correlation (Full Access)

```
┌──────┐     ┌───────────┐     ┌──────────┐     ┌─────────┐     ┌────────────────────────────┐
│PlntMg│     │   Agent   │     │ Gateway  │     │ Policy  │     │      MCP Servers           │
│      │     │ (Strands) │     │          │     │ (Cedar) │     │ Equipment│IoT│Supply│Analyt│
└──┬───┘     └─────┬─────┘     └────┬─────┘     └────┬────┘     └──┬───────┬──┬──────┬──────┘
   │               │                 │                │              │       │  │      │
   │──"Which lines need attention this week?"──>      │              │       │  │      │
   │               │                 │                │              │       │  │      │
   │         LLM plans multi-tool strategy:           │              │       │  │      │
   │         1. discover_data_sources                 │              │       │  │      │
   │         2. detect_anomaly (all)                  │              │       │  │      │
   │         3. get_oee_trends (all)                  │              │       │  │      │
   │         4. get_quality_metrics (all)             │              │       │  │      │
   │               │                 │                │              │       │  │      │
   │               │──detect_anomaly()──>             │              │       │  │      │
   │               │                 │──evaluate──────>              │       │  │      │
   │               │                 │  (plant_mgr, no    │              │       │  │      │
   │               │                 │   line param)  │              │       │  │      │
   │               │                 │<──ALLOW────────│  (full access)       │  │      │
   │               │                 │──────────────────────────────>│       │  │      │
   │               │                 │<─anomalies: Machine 42 temp──│       │  │      │
   │               │                 │                │              │       │  │      │
   │               │──get_oee_trends()──>             │              │       │  │      │
   │               │                 │──evaluate──────>              │       │  │      │
   │               │                 │<──ALLOW────────│              │       │  │      │
   │               │                 │─────────────────────────────────────────>│      │
   │               │                 │<─Line 4 ↓6%, Line 9 ↓3%────────────────│      │
   │               │                 │                │              │       │  │      │
   │               │──get_shared_infrastructure()──>  │              │       │  │      │
   │               │                 │──evaluate──────>              │       │  │      │
   │               │                 │<──ALLOW────────│              │       │  │      │
   │               │                 │──────────────────────────────>│       │  │      │
   │               │                 │<─coolant_loop_A serves L4+L9─│       │  │      │
   │               │                 │                │              │       │  │      │
   │         LLM correlates:         │                │              │       │  │      │
   │         "Machine 42 temp +      │                │              │       │  │      │
   │          Line 4 OEE down +      │                │              │       │  │      │
   │          Shared coolant with    │                │              │       │  │      │
   │          Line 9 → ROOT CAUSE"   │                │              │       │  │      │
   │               │                 │                │              │       │  │      │
   │<─"Priority 1: Line 4 — Machine 42 temperature 12°C above       │       │  │      │
   │   baseline. OEE dropped 6%. Lines 4 and 9 share coolant        │       │  │      │
   │   loop A — possible coolant degradation affecting both.         │       │  │      │
   │   Recommendation: Check coolant loop A filter (60 days          │       │  │      │
   │   since last change) and schedule Machine 42 bearing            │       │  │      │
   │   inspection."                  │                │              │       │  │      │
```

---

## Cedar Policy Evaluation Matrix

### Complete Decision Table

| # | User | Role | Tool | Parameter | User's Scope | Match? | Decision | Cedar Rule |
|---|------|------|------|-----------|-------------|--------|----------|-----------|
| 1 | Plant Manager | plant_manager | Any | Any | Full | N/A | **ALLOW** | `has_full_access` bypass |
| 2 | Line Supervisor | line_supervisor | get_oee_trends | line="Line 7" | line_scope=["Line 7"] | ✅ In scope | **ALLOW** | No forbid matches |
| 3 | Line Supervisor | line_supervisor | get_oee_trends | line="Line 4" | line_scope=["Line 7"] | ❌ Not in scope | **DENY** | forbid_line_scope |
| 4 | Line Supervisor | line_supervisor | get_equipment | plant="Plant 1" | plant_scope=["Plant 2"] | ❌ Not in scope | **DENY** | forbid_plant_scope |
| 5 | Line Supervisor | line_supervisor | get_equipment | (no line/plant) | — | N/A | **ALLOW** | No dimension to check |
| 6 | Maintenance Tech | maintenance_tech | get_sensor | machine_id=42 | equip=["41-45"] | ✅ In scope | **ALLOW** | No forbid matches |
| 7 | Maintenance Tech | maintenance_tech | get_sensor | machine_id=72 | equip=["41-45"] | ❌ Not in scope | **DENY** | forbid_equipment_scope |
| 8 | Maintenance Tech | maintenance_tech | get_oee | line="Line 4" | line_scope=["Line 4"] | ✅ In scope | **ALLOW** | No forbid matches |
| 9 | Maintenance Tech | maintenance_tech | get_oee | line="Line 7" | line_scope=["Line 4"] | ❌ Not in scope | **DENY** | forbid_line_scope |
| 10 | Maintenance Tech | maintenance_tech | check_parts | machine_id=42 | equip=["41-45"] | ✅ In scope | **ALLOW** | Tech check exempts supply |

### Key Insight: No Tool-Level Blocking

Note that no user is blocked from a **tool** entirely. They're blocked from specific **parameter combinations**. The Line Supervisor CAN call `get_oee_trends` — just not with `line="Line 4"`. This is parameter-level access control, not tool-level.

---

## Interceptor Pipeline Detail

### REQUEST Interceptor (runs BEFORE Cedar)

```python
Input:  { headers: { Authorization: "Bearer eyJ..." },
          body: { method: "tools/call", params: { name: "get_oee_trends", arguments: { line: "Line 4" } } } }

Processing:
  1. Extract JWT: decode(headers.Authorization)
  2. Read claims: { custom:role: "line_supervisor", custom:line_scope: "Line 7" }
  3. Inject: body.params.arguments.user_context = { role: "line_supervisor", line_scope: ["Line 7"] }
  4. Set header: x-user-role = "line_supervisor"

Output: { headers: { ..., x-user-role: "line_supervisor" },
          body: { ...arguments: { line: "Line 4", user_context: {...} } } }
```

### Cedar Evaluation (runs AFTER interceptor)

```
Input from Gateway:
  principal = AgentCore::OAuthUser (from JWT validation)
  action = AgentCore::Action::"AnalyticsTarget___get_oee_trends"
  resource = AgentCore::Gateway::"arn:aws:...:gateway/mfg-insights"
  context.input = { line: "Line 4", user_context: { role: "line_supervisor", ... } }

Evaluation:
  Rule 1 (permit_all): PERMIT matches ← would allow
  Rule 2 (forbid_line_scope):
    - action matches? YES (get_oee_trends is in the list)
    - context.input has line? YES ("Line 4")
    - principal in line_supervisors group? YES
    - line_scope contains "Line 4"? NO (scope is "Line 7")
    → FORBID MATCHES

  Result: FORBID overrides PERMIT → DENY
```

### RESPONSE Interceptor (runs AFTER tool execution)

```
Only applies to tools/list responses:

Input:  { result: { tools: [all 12 tools] } }

Processing (for line_supervisor role):
  allowed_tools = ["get_equipment_status", "detect_anomaly", "get_oee_trends", ...]
  Filter: keep only tools in allowed_tools list

Output: { result: { tools: [8 tools] } }  ← Line Supervisor never sees tools they can't use
```

---

## Security Properties

### Property 1: Deterministic Authorization

Cedar evaluation is pure logic — same input always produces same output. The LLM cannot influence the policy decision regardless of prompt injection.

### Property 2: Fail-Secure

If the interceptor crashes → no context injected → Cedar has nothing to permit → DENY (deny-by-default).

### Property 3: Audit Complete

Every ALLOW and DENY is logged to CloudWatch with full context:
```json
{
  "timestamp": "2026-06-16T14:23:01Z",
  "principal": "line_supervisor",
  "action": "AnalyticsTarget___get_oee_trends",
  "resource": "arn:aws:bedrock-agentcore:...:gateway/mfg-insights",
  "decision": "DENY",
  "reason": "forbid_line_scope: Line 4 not in scope [Line 7]",
  "context": { "input": { "line": "Line 4" } }
}
```

### Property 4: MCP Server Isolation

Denied requests NEVER reach the MCP server. The tool Lambda is not invoked. No data processing occurs. No compute wasted.

### Property 5: Graceful Degradation

The agent (LLM) receives the deny message as a "tool result" and intelligently responds:
- Explains what it CAN access
- Suggests an alternative within scope
- Does NOT retry the denied call

---

## Data Flow Summary

```
                    ┌────────────────────────────────────────────────┐
                    │            IDENTITY LAYER                       │
                    │  Cognito → JWT → { role, scope attributes }     │
                    └───────────────────────┬────────────────────────┘
                                            │
                    ┌───────────────────────▼────────────────────────┐
                    │         ENRICHMENT LAYER                        │
                    │  REQUEST Interceptor: JWT → user_context        │
                    │  Injects scope into tool arguments              │
                    └───────────────────────┬────────────────────────┘
                                            │
                    ┌───────────────────────▼────────────────────────┐
                    │         AUTHORIZATION LAYER                     │
                    │  Cedar Policy Engine:                           │
                    │    permit_all (baseline)                        │
                    │    forbid_line_scope (parameter check)          │
                    │    forbid_equipment_scope (parameter check)     │
                    │    forbid_plant_scope (parameter check)         │
                    │                                                 │
                    │  forbid > permit > deny-by-default              │
                    └──────────┬─────────────────────┬───────────────┘
                               │                     │
                         ┌─────▼─────┐         ┌─────▼─────┐
                         │   ALLOW   │         │   DENY    │
                         └─────┬─────┘         └─────┬─────┘
                               │                     │
                    ┌──────────▼──────────┐   ┌──────▼──────────────┐
                    │   EXECUTION LAYER   │   │  DENY RESPONSE      │
                    │   Tool Lambda runs  │   │  "[Policy] Access   │
                    │   Returns data      │   │   denied. Scope:    │
                    └──────────┬──────────┘   │   Line 7 only"      │
                               │              └──────┬──────────────┘
                    ┌──────────▼──────────────────────▼──────────────┐
                    │         FILTERING LAYER                         │
                    │  RESPONSE Interceptor:                          │
                    │    tools/list → filter by role                  │
                    │    tool results → pass through                  │
                    └───────────────────────┬────────────────────────┘
                                            │
                    ┌───────────────────────▼────────────────────────┐
                    │         SYNTHESIS LAYER                         │
                    │  Agent (LLM) composes human-readable response   │
                    │  ALLOW → "Here's Line 7 OEE: 82.3%..."         │
                    │  DENY  → "I can't access Line 4. Show Line 7?" │
                    └────────────────────────────────────────────────┘
```

---

## Comparison: Simulated vs Real AgentCore

| Aspect | Simulated (SIMULATION_MODE=true) | Real AgentCore (default, SIMULATION_MODE=false) |
|--------|--------------------------|----------------------------|
| Identity | Hardcoded `UserIdentity` dataclass | Cognito JWT with custom claims |
| Interceptor | N/A (local hook extracts from dataclass) | REQUEST Lambda on Gateway extracts JWT → user_context |
| Policy | Python if/else in `policy.py` | Cedar language, formally verified |
| Enforcement point | In-process `BeforeToolCallEvent` hook (simulation) | Server-side (Gateway evaluates Cedar before Lambda target) |
| Audit | `logging.warning()` | CloudWatch + CloudTrail |
| Tool isolation | Same process | Separate Lambda per target |
| Bypass risk | LLM can't bypass (hook is synchronous) | LLM can't bypass (Gateway is external) |
| Latency | ~0ms (in-memory) | ~5-15ms (Lambda cold start amortized) |
| Scalability | Single process | Infinite (managed service) |

---

## Scenarios for Customer Demonstrations

### Demo 1: "Same Question, Different Answers"

Ask all three users: **"Are there any anomalies on the factory floor?"**

- **Plant Manager** → sees anomalies across all 12 lines, prioritized by severity
- **Line Supervisor** → sees only Line 7 anomalies (or "no anomalies on your line")
- **Maintenance Tech** → sees only Machine 41-45 anomalies (focused on her equipment)

### Demo 2: "Attempted Scope Violation"

The Line Supervisor asks: **"Show me Machine 42 vibration data"**

Machine 42 is on Line 4 (Maintenance Tech's territory, not the Line Supervisor's). The policy engine denies it. Agent explains the boundary and suggests checking Line 7 machines instead.

### Demo 3: "Cross-System Intelligence" (Plant Manager only)

The Plant Manager asks: **"Why is Line 4 availability dropping?"**

Agent correlates across 4 data sources:
1. IoT → Machine 42 temperature +12°C
2. Equipment → Machine 42 bearing replaced 8 months ago, running at 1.3x capacity
3. Supply → Bearing stock below reorder point (12 vs 20)
4. Analytics → Line 4 OEE down 6% over 4 weeks

Synthesizes: root cause = bearing degradation under overload, shared coolant loop affecting Line 9.

### Demo 4: "Memory in Action" (Maintenance Tech)

The Maintenance Tech asks: **"Has the vibration gotten worse since last week?"**

- Memory surfaces: "Last week Machine 42 vibration: 3.8 mm/s"
- IoT tool returns current: 4.5 mm/s
- Agent: "+18% increase, now above warning threshold (4.0 mm/s). Recommend bearing inspection."

---

## Appendix: Cedar Policy Files

See `deploy/agentcore/cedar_policies/` for the complete Cedar rules:
- `permit_all.cedar` — Baseline access
- `forbid_line_scope.cedar` — Line restriction
- `forbid_equipment_scope.cedar` — Machine restriction  
- `forbid_plant_scope.cedar` — Plant restriction


---

## Code Structure

```
src/
├── main.py                    ← CLI entry point (select user, ask questions)
├── demo_ui.py                 ← Streamlit web UI (chat + live logs)
├── config.py                  ← Environment config (ports, model, region)
│
├── agent/
│   ├── agent.py               ← THE CORE: ManufacturingInsightsAgent
│   └── prompts.py             ← System prompt template (injects identity + memory)
│
├── identity/
│   ├── models.py              ← UserIdentity dataclass + 3 demo personas
│   ├── policy.py              ← PolicyEngine (local Cedar simulation, dev only)
│   └── gateway_hook.py        ← LOCAL SIMULATION ONLY — BeforeToolCallEvent hook
│                                 approximates Gateway policy (not used in production)
│
├── memory/
│   └── manager.py             ← Session memory + long-term memory store
│
├── servers/
│   ├── start_all.py           ← Launches all 5 MCP servers locally
│   ├── semantic_layer_server.py  ← Data catalog (discover_data_sources)
│   ├── equipment_server.py    ← get_equipment_status, get_maintenance_history
│   ├── iot_telemetry_server.py   ← get_sensor_readings, detect_anomaly
│   ├── supply_chain_server.py ← check_parts_inventory, get_supplier_lead_times
│   └── analytics_server.py    ← get_oee_trends, get_quality_metrics
│
├── data/
│   ├── data_provider.py       ← Routes between simulated/live data backends
│   ├── sample_data.py         ← In-memory factory data (simulated mode)
│   ├── aurora_client.py       ← Aurora PostgreSQL (live mode)
│   ├── timestream_client.py   ← Amazon Timestream (live mode)
│   ├── lakehouse_client.py    ← Redshift Data API (live mode)
│   └── opensearch_client.py   ← OpenSearch (live mode)

deploy/agentcore/
├── deploy_live.py             ← Creates real AWS resources
├── setup_identity.py          ← Cognito User Pool + 3 users
├── setup_gateway.py           ← Gateway + Lambda targets
├── setup_policy.py            ← Cedar policies + Policy Engine
├── setup_interceptor.py       ← Request/Response Lambda interceptors
├── cedar_policies/            ← Raw .cedar policy files
└── lambda_functions/          ← Interceptor Lambda source code
```

---

## The Core Flow (agent.py)

```python
def query(self, user, question):
    # 1. Build system prompt with identity + scope + memory
    system_prompt = self._build_system_prompt(user, session_id)
    
    # 2. Connect to tools (local MCP servers OR real AgentCore Gateway)
    mcp_clients = self._create_mcp_clients()
    
    # 3. Collect all tools into flat list
    all_tools = []
    for client in mcp_clients:
        all_tools.extend(client.list_tools_sync())
    
    # 4. Create agent (with or without local policy hook)
    if not SIMULATION_MODE:
        # PRODUCTION: Gateway handles Cedar policy enforcement server-side
        agent = Agent(system_prompt, tools=all_tools)
    else:
        # DEV ONLY: Local hook simulates Gateway policy enforcement
        agent = Agent(system_prompt, tools=all_tools, hooks=[gateway_hook])
    
    # 5. Agent autonomously reasons and calls tools
    response = agent(question)
    
    # 6. Record in memory for follow-ups
    session.add_interaction(query=question, response_summary=response[:200])
    return response
```

---

## Two Operating Modes

### Mode A: Local Simulation (SIMULATION_MODE=true)

```
User → Agent → GatewayPolicyHook (Python, dev-only simulation) → Local MCP Server → sample_data.py
```

### Mode B: AgentCore Gateway (Default — SIMULATION_MODE=false or unset)

```
User → Agent → Gateway (HTTPS) → REQUEST Interceptor (JWT → user_context) → Cedar Policy Engine → Lambda Target → Response
```

In Mode B, the Gateway itself invokes Cedar policy before invoking the Lambda tool target. The agent has no policy logic — it simply sends tool calls to the Gateway URL.

---

## Request Lifecycle — Concrete Example

**Line Supervisor asks: "What's the OEE for Line 4?"**

```
Step 1: UI → agent.query(line_supervisor, "What's the OEE for Line 4?")

Step 2: System prompt built:
  "You are the Manufacturing Insights Agent...
   User role: line_supervisor
   Scope: Plants: Plant 2, Lines: Line 7"

Step 3: Connect to Gateway (1 MCP endpoint, 3 tools visible)

Step 4: LLM reasons → calls get_oee_trends(line="Line 4")

Step 5: Gateway evaluates:
  → REQUEST Interceptor decodes JWT, injects context
  → Cedar: permit_all MATCHES (would allow)
  → Cedar: forbid_line_scope — "Line 4" NOT in ["Line 7"]
  → FORBID OVERRIDES PERMIT → DENY
  → Returns: "[Policy] Access denied. Not authorized for Line 4."

Step 6: LLM reads deny, responds:
  "I can't access Line 4. My scope is Line 7.
   Want Line 7 OEE trends instead?"
```

---

## AgentCore Component Interactions

```
┌──────────────────────────────────────────────────────────────────┐
│  USER authenticates → Cognito → JWT with scope claims            │
└───────────────────────────────┬──────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────┐
│  AGENT (Strands + Bedrock Claude)                                │
│  Receives system prompt with: identity + scope + memory          │
│  LLM autonomously decides which tools to call                    │
└───────────────────────────────┬──────────────────────────────────┘
                                │ tools/call (MCP JSON-RPC)
┌───────────────────────────────▼──────────────────────────────────┐
│  GATEWAY (AgentCore)                                              │
│  1. Validates JWT signature (Cognito JWKS)                        │
│  2. Runs REQUEST Interceptor Lambda:                              │
│     - Decodes JWT claims (role, line_scope, equipment_scope)      │
│     - Injects user_context into tool arguments                    │
│     - Sets x-user-role header                                     │
│  3. Evaluates CEDAR Policy Engine:                                │
│     - permit_all → PERMIT (baseline)                              │
│     - forbid_line_scope → check line param vs user scope          │
│     - forbid_equipment_scope → check machine_id vs user scope     │
│     - If ANY forbid matches → DENY (overrides permit)             │
│  4. If ALLOW → invokes Lambda target                              │
│  5. Runs RESPONSE Interceptor Lambda:                             │
│     - Filters tools/list by role                                  │
│     - Passes tool results through                                 │
└───────────┬──────────────────────────────────┬───────────────────┘
            │ ALLOW                             │ DENY
┌───────────▼───────────┐           ┌──────────▼──────────────────┐
│  LAMBDA TARGET        │           │  DENY RESPONSE               │
│  Executes tool logic  │           │  "Access denied.             │
│  Returns JSON data    │           │   Not authorized for Line 4" │
└───────────┬───────────┘           └──────────┬──────────────────┘
            │                                   │
┌───────────▼───────────────────────────────────▼──────────────────┐
│  AGENT receives result                                            │
│  ALLOW → synthesizes data into response                           │
│  DENY → explains scope limit, suggests alternative                │
└──────────────────────────────────────────────────────────────────┘
```

---

## Key Design Principles

| Principle | Implementation |
|-----------|---------------|
| **LLM decides what, Cedar decides if** | Agent picks tools; Gateway approves/denies |
| **Fail-secure** | No permit match = DENY. Interceptor crash = DENY. |
| **Parameter-level access** | Same tool, different params = different decision |
| **MCP servers are auth-unaware** | Zero access control logic in Lambdas |
| **Memory respects policy** | Can't surface memories from out-of-scope data |
| **Extensible by config** | New tool = new Lambda target, existing policies auto-apply |
| **Forbid overrides permit** | One deny rule blocks regardless of other permits |
| **Deterministic** | Cedar gives same result for same input (unlike LLM) |

---

## AgentCore Registry — Tool Discovery & Governance

The Registry provides a service catalog for MCP tools. The Gateway's routing table is populated from registered targets.

### Registration Model

Each MCP server is registered with:

| Field | Example |
|-------|---------|
| Name | `EquipmentTarget` |
| Version | `1.2` |
| Tools | `[get_equipment_status, get_maintenance_history, get_shared_infrastructure]` |
| Tags | `["manufacturing", "equipment", "maintenance"]` |
| Data Source | Aurora PostgreSQL |
| Owner | manufacturing-platform-team |
| Status | ACTIVE |

### Discovery Flow

```
Agent: "Which lines need attention?" (complex query)
  │
  ├── Agent calls: get_data_catalog()  ← Semantic Layer acts as Registry
  │   Returns: {equipment: [...tools], iot: [...tools], analytics: [...tools]}
  │
  └── Agent now knows which tools exist and what data sources they cover
      → Makes informed decisions about which tools to call
```

### Governance Capabilities

- **Versioning** — Multiple versions can coexist (v1.0 alongside v2.0)
- **Deprecation** — Mark tools as deprecated with sunset date
- **Ownership** — Each target has a responsible team
- **Schema validation** — Tool schemas validated at registration time
- **Audit trail** — Every register/update/deprecate action is logged

### Adding a New MCP Server (Zero Agent Code Changes)

1. Write the MCP server (FastMCP pattern)
2. Register tool schemas in `setup_gateway.py`
3. Deploy the Lambda target
4. Update the Semantic Layer catalog
5. Existing Cedar policies auto-apply if parameters match (line, machine_id, plant)

---

## Memory Architecture — Three Constructs

### Memory Types

| Type | Scope | Lifetime | Storage | Purpose |
|------|-------|----------|---------|---------|
| **Short-term** | Session | Destroyed on end | microVM RAM | Turn context, coreference |
| **Long-term** | User/Team/Org | TTL (90-365 days) | S3 | Baselines, preferences, thresholds |
| **Episodic** | User | TTL (90 days) | S3 | Timestamped events, past decisions |

### Memory APIs (src/memory/manager.py)

```python
# Store an episodic event
memory.store(
    user_id="priya.nair",
    key="vibration_flagged",
    value="Machine 42 vibration at 4.5 mm/s — flagged for review",
    memory_type="episodic",
    tags=["machine_42", "vibration"],
    source_tool="get_sensor_readings",
    user_action="flagged_for_review",
)

# Recall relevant memories (keyword search across all namespaces)
results = memory.recall("priya.nair", query="machine 42", memory_types=["episodic"])

# Get chronological timeline
timeline = memory.get_episodic_timeline("priya.nair", topic="machine 42", days=30)

# Get long-term baselines (excludes episodic)
baselines = memory.get_long_term_context("priya.nair", tags=["baseline"])

# Get user preferences
prefs = memory.get_user_preferences("sarah.chen")
```

### Namespace Isolation

| Namespace | Who Can Access | Example Content |
|-----------|----------------|-----------------|
| User (private) | Only that user | Priya's Machine 42 baselines |
| Team | All team members | Maintenance team vibration thresholds |
| Organization | Everyone | Global OEE critical threshold (80%) |

### Memory + Policy Integration

- Memory derived from denied data is **NOT** stored
- Recall respects namespaces — user A cannot access user B's memories
- Team memories are accessible to all members of that team

---

## Evaluation Framework — 7 Metrics

All evaluations use the [Strands Evals SDK](https://strandsagents.com/latest/user-guide/concepts/evals/).

### Metrics Summary

| # | Metric | Target | Type | File |
|---|--------|--------|------|------|
| 1 | Tool Selection Accuracy | > 90% | Deterministic | `evals/eval_tool_use.py` |
| 2 | Tool Parameter Accuracy | > 95% | Deterministic | `evals/eval_tool_use.py` |
| 3 | Policy Denial Compliance | 100% | Deterministic | `evals/eval_policy.py` |
| 4 | Faithfulness | > 0.90 | LLM-judged | `evals/eval_quality.py` |
| 5 | Helpfulness | > 0.85 | LLM-judged | `evals/eval_quality.py` |
| 6 | Trajectory Quality | > 0.85 | LLM-judged | `evals/eval_trajectory.py` |
| 7 | Goal Success Rate | > 0.85 | LLM-judged | `evals/eval_trajectory.py` |

### When to Run Each

| Metric | Trigger |
|--------|---------|
| Tool Selection | After prompt changes or new tools added |
| Tool Parameters | After schema changes or identity model changes |
| Policy Compliance | After every Cedar policy change (mandatory, 100% target) |
| Faithfulness | After model upgrades or synthesis prompt changes |
| Helpfulness | When users report unhelpful responses |
| Trajectory | After adding MCP servers or changing semantic layer |
| Goal Success | Weekly regression cadence |

### Running Evaluations

```bash
python -m evals.eval_tool_use      # Metrics 1 & 2
python -m evals.eval_policy        # Metric 3
python -m evals.eval_quality       # Metrics 4 & 5
python -m evals.eval_trajectory    # Metrics 6 & 7
```

### Test Suite (63 tests, no AWS needed)

```bash
pytest tests/ -v   # 63 tests: agent, policy, gateway hook, MCP servers, memory
```
