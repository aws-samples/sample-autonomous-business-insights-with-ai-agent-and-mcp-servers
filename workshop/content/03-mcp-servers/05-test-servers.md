---
title: "Start & Test All Servers"
weight: 35
---

# Start and Test All MCP Servers

## Start All 5 Servers

```bash
python -m src.servers.start_all
```

Expected output:
```
✓ Semantic Layer Server started (PID: xxxxx)
✓ Equipment Server started (PID: xxxxx)
✓ IoT Telemetry Server started (PID: xxxxx)
✓ Supply Chain Server started (PID: xxxxx)
✓ Analytics Server started (PID: xxxxx)

============================================================
All MCP servers are running. Press Ctrl+C to stop.
============================================================
  Semantic Layer Server:  http://localhost:8005/mcp/
  Equipment Server:       http://localhost:8001/mcp/
  IoT Telemetry Server:   http://localhost:8002/mcp/
  Supply Chain Server:    http://localhost:8003/mcp/
  Analytics Server:       http://localhost:8004/mcp/
============================================================
```

## Test: Discover Tools

Open a **new terminal** (keep servers running):

```bash
source .venv/bin/activate
python -c "
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

servers = {
    'Semantic Layer': 'http://localhost:8005/mcp/',
    'Equipment': 'http://localhost:8001/mcp/',
    'IoT Telemetry': 'http://localhost:8002/mcp/',
    'Supply Chain': 'http://localhost:8003/mcp/',
    'Analytics': 'http://localhost:8004/mcp/',
}

for name, url in servers.items():
    client = MCPClient(lambda u=url: streamablehttp_client(u))
    with client:
        tools = client.list_tools_sync()
        tool_names = [t.tool_name for t in tools]
        print(f'{name}: {tool_names}')
"
```

Expected:
```
Semantic Layer: ['discover_data_sources', 'get_data_catalog']
Equipment: ['get_equipment_status', 'get_maintenance_history', 'get_shared_infrastructure']
IoT Telemetry: ['get_sensor_readings', 'detect_anomaly']
Supply Chain: ['check_parts_inventory', 'get_supplier_lead_times']
Analytics: ['get_oee_trends', 'get_quality_metrics']
```

**Total: 11 tools across 5 MCP servers** — all discoverable via the standard MCP protocol.

## Test: Call a Tool Directly

```python
python -c "
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient
import json

# Test the Semantic Layer
client = MCPClient(lambda: streamablehttp_client('http://localhost:8005/mcp/'))
with client:
    result = client.call_tool_sync(
        tool_use_id='test-1',
        name='discover_data_sources',
        arguments={'query_keywords': 'vibration machine bearing maintenance'}
    )
    data = json.loads(result['content'][0]['text'])
    print(f'Sources found: {data[\"sources_found\"]}')
    for src in data['recommended_sources']:
        print(f'  {src[\"name\"]} (score: {src[\"relevance_score\"]}) → {src[\"recommended_tools\"]}')
"
```

Expected:
```
Sources found: 3
  IoT Sensor Telemetry (score: 6) → ['get_sensor_readings', 'detect_anomaly']
  Equipment Registry (score: 5) → ['get_equipment_status', 'get_maintenance_history', 'get_shared_infrastructure']
  Supply Chain & Inventory (score: 4) → ['check_parts_inventory', 'get_supplier_lead_times']
```

## Test: Full Tool Call Chain

```python
python -c "
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient
import json

# Call equipment server for Machine 42
client = MCPClient(lambda: streamablehttp_client('http://localhost:8001/mcp/'))
with client:
    result = client.call_tool_sync(
        tool_use_id='test-2',
        name='get_maintenance_history',
        arguments={'machine_id': 42}
    )
    data = json.loads(result['content'][0]['text'])
    print(f'Machine: {data[\"machine\"]}')
    print(f'Records: {data[\"total_records\"]}')
    for record in data['maintenance_records']:
        print(f'  {record[\"date\"]} - {record[\"type\"]}: {record[\"description\"]}')
"
```

## Summary: What You've Built

```
┌─────────────────────────────────────────────────────────────┐
│  5 MCP Servers — each independent, each with typed tools    │
├─────────────────────────────────────────────────────────────┤
│  Semantic Layer (8005)  │ discover_data_sources             │
│                         │ get_data_catalog                  │
├─────────────────────────┼───────────────────────────────────┤
│  Equipment (8001)       │ get_equipment_status              │
│                         │ get_maintenance_history           │
│                         │ get_shared_infrastructure         │
├─────────────────────────┼───────────────────────────────────┤
│  IoT Telemetry (8002)   │ get_sensor_readings              │
│                         │ detect_anomaly                    │
├─────────────────────────┼───────────────────────────────────┤
│  Supply Chain (8003)    │ check_parts_inventory            │
│                         │ get_supplier_lead_times           │
├─────────────────────────┼───────────────────────────────────┤
│  Analytics (8004)       │ get_oee_trends                   │
│                         │ get_quality_metrics               │
└─────────────────────────┴───────────────────────────────────┘
```

Each server:
- Runs independently (can be deployed, scaled, updated separately)
- Speaks the open MCP protocol (any MCP-compatible agent can use it)
- Delegates to `data_provider.py` (works in simulated AND live mode)
- Validates all inputs before processing
- Returns structured JSON that the agent can reason about

{{% notice success %}}
**Checkpoint:** If all 5 servers start successfully and you can discover tools and call them, you're ready to build the agent in the next module.
{{% /notice %}}
