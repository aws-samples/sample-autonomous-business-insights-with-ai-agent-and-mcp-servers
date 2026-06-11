---
title: "Build the Equipment MCP Server"
weight: 32
---

# Build the Equipment MCP Server

In this section, you'll build your first MCP server step by step. This server exposes tools for querying machine data, maintenance history, and shared infrastructure.

## Step 1: Create the Server

An MCP server is just a Python file that uses `FastMCP` to expose functions as typed tools over HTTP.

Open `src/servers/equipment_server.py` and examine the structure:

```python
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import json
import os
from mcp.server import FastMCP

# Create the MCP server with a name and port
# The port is configurable via environment variable
mcp = FastMCP(
    "Equipment Status Server",
    port=int(os.getenv("EQUIPMENT_SERVER_PORT", "8001"))
)
```

**What's happening:**
- `FastMCP` creates an HTTP server that speaks the MCP protocol
- It listens on port 8001 (configurable)
- The name "Equipment Status Server" is what clients see during discovery

## Step 2: Define Tools with `@mcp.tool`

Each tool is a Python function decorated with `@mcp.tool`. The decorator registers it with the MCP server and makes it discoverable by agents.

### Tool 1: `get_equipment_status`

```python
from src.data.data_provider import (
    get_equipment_status as _get_equipment_status,
    get_maintenance_history as _get_maintenance_history,
)

@mcp.tool(description="Get the current status and metadata for equipment on a specific assembly line or for a specific machine.")
def get_equipment_status(
    line: str | None = None,
    machine_id: int | None = None,
    plant: str | None = None,
) -> str:
    """Retrieve equipment status from the equipment registry.

    Args:
        line: Assembly line identifier (e.g., "Line 4"). Optional.
        machine_id: Specific machine ID number. Optional.
        plant: Plant identifier (e.g., "Plant 1"). Optional.

    Returns:
        JSON string with equipment status information.
    """
    # Input validation — protect against malformed requests
    if machine_id is not None and (not isinstance(machine_id, int) or machine_id < 1):
        return json.dumps({"error": "machine_id must be a positive integer."})
    if line is not None and not isinstance(line, str):
        return json.dumps({"error": "line must be a string."})
    if plant is not None and not isinstance(plant, str):
        return json.dumps({"error": "plant must be a string."})

    # Delegate to the data provider (routes to simulated or live backend)
    return _get_equipment_status(line=line, machine_id=machine_id, plant=plant)
```

**Key points:**
- The `description` in `@mcp.tool()` is what the LLM reads to decide when to use this tool
- Type hints (`str | None`, `int | None`) define the input schema — MCP uses these to generate typed parameters
- Always validate inputs before processing
- Return JSON strings (the agent parses these)
- Delegate to `data_provider` so the same tool works in both simulated and live mode

### Tool 2: `get_maintenance_history`

```python
@mcp.tool(description="Get maintenance history for a specific machine including past repairs, inspections, and preventive maintenance records.")
def get_maintenance_history(machine_id: int) -> str:
    """Retrieve maintenance records for a machine.

    Args:
        machine_id: The machine ID number.

    Returns:
        JSON string with maintenance history.
    """
    if not isinstance(machine_id, int) or machine_id < 1:
        return json.dumps({"error": "machine_id must be a positive integer."})
    return _get_maintenance_history(machine_id=machine_id)
```

### Tool 3: `get_shared_infrastructure`

```python
from src.data.sample_data import SHARED_INFRASTRUCTURE

@mcp.tool(description="Get shared infrastructure relationships between assembly lines (coolant loops, power feeds, compressed air systems).")
def get_shared_infrastructure(line: str | None = None) -> str:
    """Identify shared infrastructure that connects assembly lines.

    This is critical context that most dashboards don't model — understanding
    shared resources helps identify correlated failures across lines.
    """
    if line is not None and not isinstance(line, str):
        return json.dumps({"error": "line must be a string or None."})

    results = {}
    for infra_id, info in SHARED_INFRASTRUCTURE.items():
        if line is None or line in info["serves"]:
            results[infra_id] = info

    return json.dumps(results, indent=2, default=str)
```

**Why this tool matters:** Most dashboards don't model that Line 4 and Line 9 share a coolant loop. When both lines show issues, this tool helps the agent identify the correlation.

## Step 3: Run the Server

```python
if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

This starts the server with **Streamable HTTP** transport — the agent connects via `http://localhost:8001/mcp/`.

## How the Agent Discovers Tools

When the agent connects, it performs an MCP protocol handshake and discovers:

| Tool Name | Description | Parameters |
|-----------|-------------|-----------|
| `get_equipment_status` | Get equipment status for a line or machine | `line` (str, optional), `machine_id` (int, optional), `plant` (str, optional) |
| `get_maintenance_history` | Get maintenance records for a machine | `machine_id` (int, required) |
| `get_shared_infrastructure` | Get shared infrastructure relationships | `line` (str, optional) |

The agent sees **only** the tool name, description, and parameter schema. It doesn't know or care about the implementation behind it.

## The Data Provider Pattern

Notice that tools delegate to `data_provider` instead of querying data directly:

```
@mcp.tool → data_provider.get_equipment_status()
                    │
                    ├── DATA_MODE=simulated → sample_data.py (in-memory dicts)
                    │
                    └── DATA_MODE=live → aurora_client.py → RDS Data API → Aurora PostgreSQL
```

### Live Mode: Actual SQL Against Aurora PostgreSQL

When `DATA_MODE=live`, the tool calls execute **real SQL queries** against Aurora via the RDS Data API. Open `src/data/aurora_client.py`:

```python
import boto3

class AuroraClient:
    """Client for querying Aurora PostgreSQL via RDS Data API."""

    def __init__(self):
        self.client = boto3.client("rds-data")
        self.cluster_arn = os.getenv("AURORA_CLUSTER_ARN")
        self.secret_arn = os.getenv("AURORA_SECRET_ARN")
        self.database = os.getenv("AURORA_DATABASE", "manufacturing")

    def execute_query(self, sql, parameters=None):
        response = self.client.execute_statement(
            resourceArn=self.cluster_arn,
            secretArn=self.secret_arn,
            database=self.database,
            sql=sql,
            parameters=parameters or [],
            includeResultMetadata=True,
        )
        return self._parse_response(response)
```

The actual query for `get_equipment_status(machine_id=42)`:

```python
def query_equipment_status(machine_id=None, line=None, plant=None):
    if machine_id is not None:
        return client.execute_query(
            "SELECT * FROM equipment_registry WHERE machine_id = :mid",
            [{"name": "mid", "value": {"longValue": machine_id}}],
        )
    elif line is not None:
        return client.execute_query(
            "SELECT * FROM equipment_registry WHERE line_name = :line ORDER BY machine_id",
            [{"name": "line", "value": {"stringValue": line}}],
        )
```

This hits a **real Aurora PostgreSQL Serverless v2** instance provisioned by the CloudFormation stack.

### Live Mode: IoT Data from Amazon Timestream

For sensor readings, the live backend queries **Amazon Timestream** (purpose-built time-series database). Open `src/data/timestream_client.py`:

```python
class TimestreamClient:
    def __init__(self):
        self.client = boto3.client("timestream-query")
        self.database = os.getenv("TIMESTREAM_DATABASE", "manufacturing_iot")
        self.table = os.getenv("TIMESTREAM_TABLE", "sensor_readings")

    def execute_query(self, query):
        rows = []
        paginator = self.client.get_paginator("query")
        for page in paginator.paginate(QueryString=query):
            columns = [col["Name"] for col in page["ColumnInfo"]]
            for row in page["Rows"]:
                parsed_row = {columns[i]: datum.get("ScalarValue")
                             for i, datum in enumerate(row["Data"])}
                rows.append(parsed_row)
        return rows
```

The actual query for `get_sensor_readings(machine_id=42, metric="vibration", days=7)`:

```sql
SELECT time, machine_id, metric, measure_value::double as value, unit
FROM "manufacturing_iot"."sensor_readings"
WHERE machine_id = '42'
  AND metric = 'vibration'
  AND time >= ago(7d)
ORDER BY time ASC
```

### Live Mode: Supply Chain from Amazon Redshift Serverless

Inventory and OEE queries go to **Redshift** via the Redshift Data API. Open `src/data/lakehouse_client.py`:

```python
class DataInfraClient:
    def __init__(self):
        self.client = boto3.client("redshift-data")
        self.workgroup = os.getenv("REDSHIFT_WORKGROUP")
        self.database = os.getenv("REDSHIFT_DATABASE", "manufacturing")

    def execute_query(self, sql, parameters=None):
        response = self.client.execute_statement(
            WorkgroupName=self.workgroup,
            Database=self.database,
            Sql=sql,
            Parameters=parameters or [],
        )
        statement_id = response["Id"]
        return self._wait_and_fetch(statement_id)
```

The actual query for `check_parts_inventory(machine_id=42)`:

```sql
SELECT p.part_id, p.description, p.quantity_on_hand, p.reorder_point,
       p.lead_time_days, p.supplier, p.unit_cost
FROM parts_inventory p
JOIN part_machine_mapping pm ON p.part_id = pm.part_id
WHERE pm.machine_id = :machine_id
```

### Live Mode: Quality Metrics from Amazon OpenSearch Serverless

Quality documents are queried via **OpenSearch** with SigV4 authentication. Open `src/data/opensearch_client.py`:

```python
class OpenSearchClient:
    def search(self, query_body):
        url = f"{self.endpoint}/{self.index}/_search"
        body = json.dumps(query_body).encode("utf-8")

        # Sign with SigV4 for OpenSearch Serverless
        request = AWSRequest(method="POST", url=url, data=body, headers={...})
        SigV4Auth(credentials, "aoss", self.region).add_auth(request)

        # Execute and parse hits
        ...
```

The actual query for `get_quality_metrics(line="Line 4")`:

```json
{
  "size": 50,
  "sort": [{"inspection_date": {"order": "desc"}}],
  "query": {
    "bool": {
      "must": [{"term": {"line_name.keyword": "Line 4"}}],
      "filter": [{"range": {"inspection_date": {"gte": "now-28d"}}}]
    }
  }
}
```

### Summary: Real Service per Domain

| MCP Tool | Live Backend | Protocol | Actual Query Type |
|----------|-------------|----------|-------------------|
| `get_equipment_status` | Aurora PostgreSQL | RDS Data API | SQL (parameterized) |
| `get_maintenance_history` | Aurora PostgreSQL | RDS Data API | SQL (parameterized) |
| `get_sensor_readings` | Amazon Timestream | Timestream Query API | Time-series SQL |
| `detect_anomaly` | Amazon Timestream | Timestream Query API | Aggregation + threshold |
| `check_parts_inventory` | Amazon Redshift | Redshift Data API | SQL (parameterized) |
| `get_oee_trends` | Amazon Redshift | Redshift Data API | SQL (weekly aggregation) |
| `get_quality_metrics` | Amazon OpenSearch | HTTPS + SigV4 | OpenSearch DSL JSON |
| `get_shared_infrastructure` | Amazon S3 | S3 GetObject | JSON config file |

This means:
- You can develop and test without any AWS infrastructure (simulated mode)
- Switching to live mode is just `DATA_MODE=live` + CloudFormation stack outputs in `.env`
- The MCP tool interface stays **identical** in both modes — the agent doesn't know or care which backend is active

{{% notice tip %}}
**Design Principle:** Write your tools to be thin wrappers — validate input, delegate to a data provider, return JSON. This keeps tools testable and backend-swappable.
{{% /notice %}}
