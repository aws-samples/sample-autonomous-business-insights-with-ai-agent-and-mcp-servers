+++
title = "Understanding MCP Servers"
weight: 30
+++

# Understanding MCP Servers

In this module, you'll explore the four domain MCP servers that expose manufacturing data as tools. You'll understand how MCP works, inspect server implementations, start them locally, and test tools directly.

## What is MCP?

The [Model Context Protocol](https://modelcontextprotocol.io/) is an open standard for connecting AI agents to data sources and tools. Think of it as a USB-C for AI—one protocol, many data sources.

Each MCP server:
- Declares a set of **tools** with typed parameters and descriptions
- Runs over **streamable HTTP** (or stdio for local development)
- Is **stateless**—no auth logic, no session management
- Can be **discovered** at runtime by the agent

```
Agent: "What tools do you have?"
MCP Server: "I have get_equipment_status(line, machine_id) and get_maintenance_history(machine_id)"
Agent: "Call get_equipment_status with line='Line 4'"
MCP Server: → returns JSON result
```

## Our Four Domain Servers

| Server | Port | Tools | Data Source |
|--------|------|-------|-------------|
| Equipment Status | 8001 | `get_equipment_status`, `get_maintenance_history`, `get_shared_infrastructure` | Aurora PostgreSQL |
| IoT Telemetry | 8002 | `get_sensor_readings`, `detect_anomaly` | Amazon Timestream |
| Supply Chain | 8003 | `check_parts_inventory`, `get_supplier_lead_times` | Amazon Redshift |
| Analytics | 8004 | `get_oee_trends`, `get_quality_metrics` | Amazon Redshift |

There's also a **Semantic Layer** server (port 8005) that provides data catalog metadata for source discovery.

## Step 1: Explore an MCP Server Implementation

Open `src/servers/equipment_server.py`. Here's the core pattern:

```python
from mcp.server import FastMCP

# Create server with a name and port
mcp = FastMCP("Equipment Status Server", port=8001)

@mcp.tool(description="Get equipment status for a line or machine")
def get_equipment_status(line: str | None = None, machine_id: int | None = None) -> str:
    """Returns current status, operating hours, and health indicators."""
    return data_provider.get_equipment_status(line=line, machine_id=machine_id)

@mcp.tool(description="Get maintenance history for a machine")
def get_maintenance_history(machine_id: int) -> str:
    """Returns past maintenance events, repairs, and inspections."""
    return data_provider.get_maintenance_history(machine_id=machine_id)

@mcp.tool(description="Get shared infrastructure between lines")
def get_shared_infrastructure(line: str | None = None) -> str:
    """Returns shared resources (coolant loops, power feeds) and their status."""
    return data_provider.get_shared_infrastructure(line=line)
```

Key observations:
- **No auth logic** — The server doesn't know or care who the user is
- **Typed parameters** — Python type hints become the tool's input schema
- **Data provider abstraction** — Routes between simulated data and live AWS queries

{{% notice note %}}
The `data_provider` handles the dual-mode routing: `DATA_MODE=simulated` returns in-memory sample data, `DATA_MODE=live` queries real AWS services. For this workshop module, we use simulated mode.
{{% /notice %}}

## Step 2: Explore the IoT Telemetry Server

Open `src/servers/iot_telemetry_server.py`:

```python
@mcp.tool(description="Get recent sensor readings for a machine")
def get_sensor_readings(
    machine_id: int,
    metric: str | None = None,
    hours: int = 24
) -> str:
    """Returns time-series sensor data (temperature, vibration, pressure)."""
    return data_provider.get_sensor_readings(
        machine_id=machine_id, metric=metric, hours=hours
    )

@mcp.tool(description="Detect anomalies across all monitored machines")
def detect_anomaly(line: str | None = None) -> str:
    """Returns machines with readings above warning/critical thresholds."""
    return data_provider.detect_anomaly(line=line)
```

Notice how `detect_anomaly` accepts an optional `line` parameter—this is what Cedar policies will evaluate for access control later.

## Step 3: Start All MCP Servers

Open a terminal and run:

```bash
python -m src.servers.start_all
```

You should see output like:

```
[INFO] Starting Semantic Layer Server on port 8005...
[INFO] Starting Equipment Server on port 8001...
[INFO] Starting IoT Telemetry Server on port 8002...
[INFO] Starting Supply Chain Server on port 8003...
[INFO] Starting Analytics Server on port 8004...
[INFO] All 5 MCP servers running.
```

{{% notice warning %}}
Keep this terminal running. The servers need to stay up for the remaining modules.
{{% /notice %}}

## Step 4: Test a Server Directly

In a **new terminal** (with your venv activated), use curl to test the equipment server's MCP endpoint:

```bash
# List available tools
curl -s http://localhost:8001/mcp -X POST \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python -m json.tool
```

Expected response (abbreviated):

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "get_equipment_status",
        "description": "Get equipment status for a line or machine",
        "inputSchema": {
          "type": "object",
          "properties": {
            "line": {"type": "string"},
            "machine_id": {"type": "integer"}
          }
        }
      }
    ]
  }
}
```

Now call a tool:

```bash
# Get equipment status for Line 4
curl -s http://localhost:8001/mcp -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "method":"tools/call",
    "params":{"name":"get_equipment_status","arguments":{"line":"Line 4"}},
    "id":2
  }' | python -m json.tool
```

You should see equipment data for Line 4 machines, including Machine 42 running at 130% rated capacity.

## Step 5: Test the IoT Telemetry Server

```bash
# Detect anomalies across all lines
curl -s http://localhost:8002/mcp -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "method":"tools/call",
    "params":{"name":"detect_anomaly","arguments":{}},
    "id":3
  }' | python -m json.tool
```

This returns anomaly data—Machine 42's temperature running 12°C above baseline.

## Step 6: Understand the Semantic Layer

The semantic layer server (`src/servers/semantic_layer.py`) doesn't query data directly. It provides **metadata** about available data sources—helping the agent discover which tools to call.

```bash
curl -s http://localhost:8005/mcp -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "method":"tools/call",
    "params":{"name":"get_data_catalog","arguments":{}},
    "id":4
  }' | python -m json.tool
```

The catalog tells the agent: "Equipment data is in Aurora, IoT data is in Timestream, supply chain is in Redshift..." — this is the "SageMaker Data Catalog" equivalent in the architecture.

## How Data Flows in the System

```
User: "Why is Line 4 availability dropping?"
                    │
                    ▼
Agent (LLM reasoning):
  1. Need anomaly data → call detect_anomaly(line="Line 4")
  2. Need equipment context → call get_equipment_status(line="Line 4")
  3. Need trend data → call get_oee_trends(line="Line 4")
  4. Related lines? → call get_shared_infrastructure(line="Line 4")
  5. Parts available? → call check_parts_inventory(part="bearing_6205")
                    │
                    ▼
Agent synthesizes: "Line 4 dropping because Machine 42 bearing degradation
                    under sustained overload. Shares coolant with Line 9.
                    Bearings below reorder point (12 vs 20 needed)."
```

The LLM decides the tool call sequence autonomously. No workflow engine required.

## Key Takeaways

1. **MCP servers are simple** — A few decorated Python functions, no framework complexity
2. **Tools are self-describing** — Type hints and descriptions tell the agent how to use them
3. **No auth in servers** — Security is enforced elsewhere (Gateway), keeping servers clean
4. **Streamable HTTP** — Standard protocol, easy to test with curl
5. **Data provider pattern** — Same server code works with simulated or live data

## Next Steps

Your MCP servers are running and serving data. In the next module, you'll build the Strands Agent that connects to all four servers and reasons across them autonomously.
