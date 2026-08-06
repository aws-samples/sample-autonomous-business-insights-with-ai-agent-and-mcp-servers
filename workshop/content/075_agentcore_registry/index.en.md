---
title: "AgentCore Registry"
weight: 75
---

# AgentCore Registry — Discover, Register & Govern MCP Servers

In this module, you'll explore the AgentCore Registry — the service catalog that lets agents discover available MCP servers and tools at runtime. You'll register your manufacturing MCP servers, configure tool metadata, and understand how the Registry enables governance at scale.

## Why a Registry?

Without a registry, the agent needs to know every MCP server URL upfront. That works for 4 servers — but what about 40? Or 400 across an enterprise?

```
Without Registry:
  Agent code hardcodes: [server1_url, server2_url, server3_url, ...]
  Problem: Every new server = code change + redeploy

With Registry:
  Agent asks: "What tools are available for manufacturing data?"
  Registry returns: [equipment_tools, iot_tools, analytics_tools, ...]
  Benefit: New servers are discoverable immediately, no agent changes
```

The Registry is the **service catalog** for MCP. It enables:

- **Dynamic discovery** — Agents find tools at runtime, not at build time
- **Governance** — Track who registered what, when, and with what schema
- **Versioning** — Multiple versions of a tool can coexist
- **Deprecation** — Mark tools as deprecated without breaking existing agents
- **Search & filter** — Find tools by domain, capability, data source, or tag

## How the Registry Fits in the Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  AgentCore Architecture                                          │
│                                                                  │
│  ┌──────────┐      ┌──────────────┐      ┌──────────────────┐  │
│  │  Agent   │─────►│   Gateway    │─────►│  Tool Targets    │  │
│  │(Runtime) │      │  (routing)   │      │  (Lambda/MCP)    │  │
│  └──────────┘      └──────┬───────┘      └──────────────────┘  │
│       │                    │                                     │
│       │   "What tools      │   Routing table                    │
│       │    exist?"         │   populated from                   │
│       ▼                    ▼   Registry                         │
│  ┌──────────────────────────────────────┐                       │
│  │           REGISTRY                    │                       │
│  │                                       │                       │
│  │  • Equipment Server (v1.2)            │                       │
│  │    Tools: get_equipment_status,       │                       │
│  │           get_maintenance_history,    │                       │
│  │           get_shared_infrastructure   │                       │
│  │    Tags: [manufacturing, equipment]   │                       │
│  │                                       │                       │
│  │  • IoT Telemetry Server (v2.0)        │                       │
│  │    Tools: get_sensor_readings,        │                       │
│  │           detect_anomaly              │                       │
│  │    Tags: [iot, telemetry, sensors]    │                       │
│  │                                       │                       │
│  │  • Analytics Server (v1.1)            │                       │
│  │    Tools: get_oee_trends,             │                       │
│  │           get_quality_metrics         │                       │
│  │    Tags: [analytics, oee, quality]    │                       │
│  │                                       │                       │
│  │  • Supply Chain Server (v1.0)         │                       │
│  │    Tools: check_parts_inventory,      │                       │
│  │           get_supplier_lead_times     │                       │
│  │    Tags: [supply-chain, inventory]    │                       │
│  └───────────────────────────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
```

## Step 1: Register an MCP Server

Each MCP server is registered with metadata that describes its capabilities:

```python
# deploy/agentcore/setup_gateway.py — registering tools with the Gateway

tool_targets = [
    {
        "name": "EquipmentTarget",
        "description": "Equipment status, maintenance history, shared infrastructure",
        "version": "1.2",
        "tools": [
            {
                "name": "get_equipment_status",
                "description": "Get equipment status for a line or machine",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "line": {"type": "string", "description": "Assembly line name"},
                        "machine_id": {"type": "integer", "description": "Machine ID"},
                    },
                },
            },
            {
                "name": "get_maintenance_history",
                "description": "Get maintenance history for a machine",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "machine_id": {"type": "integer", "description": "Machine ID"},
                    },
                    "required": ["machine_id"],
                },
            },
            {
                "name": "get_shared_infrastructure",
                "description": "Get shared resources between assembly lines",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "line": {"type": "string"},
                    },
                },
            },
        ],
        "tags": ["manufacturing", "equipment", "maintenance"],
        "dataSource": "Aurora PostgreSQL",
        "owner": "manufacturing-platform-team",
    },
    {
        "name": "IoTTarget",
        "description": "IoT sensor readings and anomaly detection",
        "version": "2.0",
        "tools": [
            {
                "name": "get_sensor_readings",
                "description": "Get recent sensor readings for a machine",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "machine_id": {"type": "integer"},
                        "metric": {"type": "string", "enum": ["temperature", "vibration", "pressure"]},
                        "hours": {"type": "integer", "default": 24},
                    },
                    "required": ["machine_id"],
                },
            },
            {
                "name": "detect_anomaly",
                "description": "Detect anomalies across monitored machines",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "line": {"type": "string"},
                    },
                },
            },
        ],
        "tags": ["iot", "telemetry", "sensors", "anomaly-detection"],
        "dataSource": "Amazon Timestream",
        "owner": "iot-platform-team",
    },
]
```

## Step 2: Understand the Registration Model

Each entry in the Registry captures:

| Field | Purpose | Example |
|-------|---------|---------|
| `name` | Unique server identifier | `EquipmentTarget` |
| `description` | Human-readable purpose | "Equipment status and maintenance" |
| `version` | Semantic version | `1.2` |
| `tools` | Array of tool definitions | `[{name, description, inputSchema}]` |
| `tags` | Searchable categories | `["manufacturing", "equipment"]` |
| `dataSource` | Underlying data system | "Aurora PostgreSQL" |
| `owner` | Responsible team | "manufacturing-platform-team" |
| `status` | Active, deprecated, or disabled | `ACTIVE` |
| `createdAt` | Registration timestamp | `2026-07-01T00:00:00Z` |

## Step 3: Discover Tools at Runtime

The Semantic Layer server in this project (`src/servers/semantic_layer.py`) acts as a lightweight registry — it tells the agent what data sources and tools are available:

```python
# src/servers/semantic_layer.py

@mcp.tool(description="Discover available data sources and their capabilities")
def get_data_catalog() -> str:
    """Returns metadata about all registered data sources and tools.

    The agent calls this FIRST to understand what's available before
    making specific data queries.
    """
    catalog = {
        "data_sources": [
            {
                "name": "Equipment & Maintenance",
                "server": "EquipmentTarget",
                "tools": ["get_equipment_status", "get_maintenance_history",
                          "get_shared_infrastructure"],
                "description": "Machine registry, maintenance records, shared resources",
                "data_freshness": "Real-time (CDC from SAP S/4HANA)",
            },
            {
                "name": "IoT Sensor Telemetry",
                "server": "IoTTarget",
                "tools": ["get_sensor_readings", "detect_anomaly"],
                "description": "Time-series sensor data and anomaly detection",
                "data_freshness": "Real-time (IoT Core → Timestream)",
            },
            {
                "name": "Supply Chain",
                "server": "SupplyChainTarget",
                "tools": ["check_parts_inventory", "get_supplier_lead_times"],
                "description": "Parts inventory levels and supplier information",
                "data_freshness": "Hourly batch (SAP MM → Redshift)",
            },
            {
                "name": "Production Analytics",
                "server": "AnalyticsTarget",
                "tools": ["get_oee_trends", "get_quality_metrics"],
                "description": "OEE weekly aggregations and quality inspection results",
                "data_freshness": "Daily ETL aggregation",
            },
        ],
        "total_tools": 10,
        "last_updated": "2026-07-23T00:00:00Z",
    }
    return json.dumps(catalog, indent=2)
```

The agent's system prompt instructs it to call `get_data_catalog()` first for complex queries — this is the discovery pattern.

## Step 4: How the Agent Uses Discovery

When Sarah asks "Which assembly lines need attention?", the agent's reasoning:

```
1. Agent: "This is a broad query. Let me check what data sources are available."
   → Calls: get_data_catalog()
   → Learns: Equipment, IoT, Supply Chain, Analytics tools available

2. Agent: "I need anomaly data first."
   → Calls: detect_anomaly()  (from IoT server — discovered via catalog)

3. Agent: "I need OEE trends to confirm."
   → Calls: get_oee_trends()  (from Analytics server — discovered via catalog)

4. Agent: "Machine 42 flagged — need equipment context."
   → Calls: get_equipment_status(line="Line 4")  (from Equipment server)

5. Agent synthesizes all results into a prioritized answer.
```

Without the catalog, the agent would have to guess which tools to try. With it, the agent makes informed decisions about which data sources are relevant.

## Step 5: Governance at Scale

In a production enterprise, the Registry enables governance:

### Tool Versioning

```
EquipmentTarget v1.0 → v1.2 (added get_shared_infrastructure)
                     → v2.0 (breaking change: renamed parameters)
```

Agents pinned to v1.x continue working. New agents can adopt v2.0.

### Deprecation Flow

```
Registry:
  IoTTarget v1.0 — status: DEPRECATED (sunset: 2026-09-01)
  IoTTarget v2.0 — status: ACTIVE

Agent receives deprecation warning in tools/list response:
  "detect_anomaly (v1.0) is deprecated. Use detect_anomaly_v2 instead."
```

### Access Control on Registration

Not just anyone can register tools in the Registry:

| Action | Who Can Do It | Why |
|--------|---------------|-----|
| Register new server | Platform team | Prevents unauthorized data exposure |
| Update tool schema | Server owner | Ensures backward compatibility |
| Deprecate a tool | Server owner or admin | Controlled sunset with notice period |
| Delete a server | Admin only | Hard delete, affects all consumers |
| Search/discover | Any authenticated agent | Read-only, safe to expose |

### Audit Trail

Every registration action is logged:

```json
{
  "action": "REGISTER_TOOL",
  "server": "EquipmentTarget",
  "tool": "get_shared_infrastructure",
  "registeredBy": "manufacturing-platform-team",
  "timestamp": "2026-07-01T10:30:00Z",
  "version": "1.2",
  "approval": "auto-approved (schema validation passed)"
}
```

## Step 6: Adding a New MCP Server

To add a 5th data source (e.g., a Quality Inspections server):

1. **Write the MCP server** (FastMCP, same pattern as Module 3)
2. **Register it in the Registry** (add to `setup_gateway.py`)
3. **Update the Semantic Layer catalog** (so agents discover it)
4. **Deploy the Lambda target** (Gateway routes to it)
5. **Add Cedar policies** (if scope restrictions apply)

No agent code changes needed. The agent discovers the new tools via the catalog on next query.

```python
# New server added — agent discovers automatically
{
    "name": "QualityInspectionTarget",
    "version": "1.0",
    "tools": [
        {"name": "get_inspection_results", ...},
        {"name": "search_defect_reports", ...},
    ],
    "tags": ["quality", "inspection", "defects"],
    "dataSource": "Amazon OpenSearch Serverless",
    "owner": "quality-team",
}
```

## Registry vs Direct Connection — Comparison

| Aspect | Direct (hardcoded URLs) | Via Registry |
|--------|------------------------|--------------|
| Adding a new server | Code change + redeploy agent | Register + deploy target |
| Removing a server | Code change + redeploy | Mark deprecated → remove |
| Finding tools | Agent knows all URLs | Agent queries catalog |
| Schema validation | None (runtime errors) | Validated at registration |
| Versioning | None | Semantic versioning |
| Governance | Manual tracking | Audit trail + ownership |
| Scale | Works for 5 servers | Works for 500 servers |

## Key Takeaways

1. **Registry = service catalog for MCP** — Tools are discoverable, not hardcoded
2. **Semantic Layer as lightweight registry** — The `get_data_catalog()` tool enables runtime discovery
3. **Zero agent changes for new tools** — Register, deploy, discover
4. **Governance built in** — Versioning, deprecation, ownership, audit
5. **Gateway uses Registry data** — Routing table is populated from registered targets
6. **Schema validation at registration** — Prevents broken tools from being discoverable

## Next Steps

Your tools are registered and discoverable. In the next module, you'll set up **AgentCore Identity** to control who can access these registered tools.
