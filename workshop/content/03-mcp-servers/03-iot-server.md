---
title: "Build the IoT Telemetry Server"
weight: 33
---

# Build the IoT Telemetry MCP Server

The IoT Telemetry server exposes tools for querying real-time sensor data and detecting anomalies. In production, it connects to Amazon Timestream via the IoT data pipeline: `IoT Core → Amazon MSK → S3 Tables (Iceberg) → Timestream`.

## The Complete Server

Open `src/servers/iot_telemetry_server.py`:

```python
import json
import os
from mcp.server import FastMCP
from src.data.data_provider import (
    get_sensor_readings as _get_sensor_readings,
    detect_anomaly as _detect_anomaly,
)

mcp = FastMCP("IoT Telemetry Server", port=int(os.getenv("IOT_TELEMETRY_SERVER_PORT", "8002")))

# Valid metrics — used for input validation
VALID_METRICS = ("temperature", "vibration", "pressure")
MAX_DAYS = 90
```

### Tool 1: `get_sensor_readings`

Retrieves time-series sensor data with summary statistics:

```python
@mcp.tool(description="Get sensor readings (temperature, vibration, pressure) for a specific machine over a given time period.")
def get_sensor_readings(
    machine_id: int,
    metric: str = "temperature",
    days: int = 7,
) -> str:
    """Retrieve time-series sensor data for a machine.

    Args:
        machine_id: The machine ID number.
        metric: Sensor metric — "temperature", "vibration", or "pressure".
        days: Number of days of historical data (default: 7, max: 90).
    """
    # Strict input validation
    if not isinstance(machine_id, int) or machine_id < 1:
        return json.dumps({"error": "machine_id must be a positive integer."})
    if metric not in VALID_METRICS:
        return json.dumps({"error": f"metric must be one of {VALID_METRICS}."})
    if not isinstance(days, int) or days < 1 or days > MAX_DAYS:
        return json.dumps({"error": f"days must be between 1 and {MAX_DAYS}."})

    return _get_sensor_readings(machine_id=machine_id, metric=metric, days=days)
```

**What gets returned** (example):
```json
{
  "machine_id": 42,
  "metric": "vibration",
  "period_days": 7,
  "total_readings": 42,
  "current_value": 5.4,
  "min_value": 2.47,
  "max_value": 5.41,
  "avg_value": 3.89,
  "unit": "mm/s",
  "trend": "increasing (+105.5%)",
  "latest_readings": [...]
}
```

### Tool 2: `detect_anomaly`

Scans for machines with readings exceeding warning/critical thresholds:

```python
@mcp.tool(description="Detect anomalies across sensors for one or more assembly lines. Returns machines with readings exceeding warning or critical thresholds.")
def detect_anomaly(
    line: str | None = None,
    plant: str | None = None,
    metric: str | None = None,
) -> str:
    """Scan for anomalous sensor readings across equipment.

    Args:
        line: Specific assembly line to check. If None, checks all.
        plant: Specific plant to check. If None, checks all.
        metric: Specific metric to check. If None, checks all metrics.
    """
    if metric is not None and metric not in VALID_METRICS:
        return json.dumps({"error": f"metric must be one of {VALID_METRICS} or None."})
    if line is not None and not isinstance(line, str):
        return json.dumps({"error": "line must be a string or None."})
    if plant is not None and not isinstance(plant, str):
        return json.dumps({"error": "plant must be a string or None."})

    return _detect_anomaly(line=line, plant=plant, metric=metric)
```

**What gets returned** (example):
```json
{
  "scan_scope": {"line": null, "plant": null, "metric": null},
  "anomalies_found": 2,
  "anomalies": [
    {
      "machine": "Machine 42",
      "line": "Line 4",
      "metric": "temperature",
      "current_value": 77.8,
      "threshold_warning": 72.0,
      "threshold_critical": 80.0,
      "unit": "°C",
      "severity": "WARNING"
    }
  ]
}
```

## Tool Design Best Practices

| Practice | Why | Example |
|----------|-----|---------|
| **Descriptive tool name** | LLM uses it to decide when to call | `detect_anomaly` not `check_data` |
| **Clear description** | LLM reads this to understand context | "Returns machines with readings exceeding thresholds" |
| **Typed parameters** | MCP generates input schema from types | `machine_id: int`, `metric: str` |
| **Default values** | Makes tools usable with minimal params | `days: int = 7` |
| **Input validation** | Prevents garbage-in from LLM hallucination | Check `metric in VALID_METRICS` |
| **Structured JSON output** | Agent can parse and reason about results | Include units, thresholds, severity |

## Live Mode: Real Timestream Queries

When `DATA_MODE=live`, the same tools execute **real queries against Amazon Timestream** — a purpose-built time-series database that ingests sensor data via the IoT Core → MSK → Timestream pipeline.

### Data Ingestion Pipeline

```
Factory Sensors → Kepware OPC-UA → AWS IoT Core → IoT Rule → Amazon Timestream
                                                                    ↓
                                     MCP Tool ← data_provider ← timestream_client
```

The IoT Core rule (provisioned by CloudFormation) routes MQTT messages to Timestream:

```sql
-- IoT Rule SQL
SELECT machine_id, machine_name, line_name, plant, metric, value, unit
FROM 'manufacturing/sensors/+'
```

### Timestream Query for `get_sensor_readings`

```python
# In src/data/timestream_client.py
def query_sensor_readings(machine_id, metric, days):
    client = boto3.client("timestream-query")
    query = (
        f"SELECT time, machine_id, metric, measure_value::double as value, unit "
        f"FROM \"{database}\".\"{table}\" "
        f"WHERE machine_id = '{machine_id}' "
        f"AND metric = '{metric}' "
        f"AND time >= ago({days}d) "
        f"ORDER BY time ASC"
    )
    rows = []
    paginator = client.get_paginator("query")
    for page in paginator.paginate(QueryString=query):
        columns = [col["Name"] for col in page["ColumnInfo"]]
        for row in page["Rows"]:
            parsed_row = {columns[i]: datum.get("ScalarValue")
                         for i, datum in enumerate(row["Data"])}
            rows.append(parsed_row)
    return rows
```

### Timestream Query for `detect_anomaly`

```python
def query_anomalies(line=None, plant=None):
    where_clauses = ["time >= ago(24h)"]
    if line:
        where_clauses.append(f"line_name = '{line}'")

    query = (
        f"SELECT machine_id, machine_name, line_name, metric, "
        f"MAX(measure_value::double) as current_value, unit "
        f"FROM \"{database}\".\"{table}\" "
        f"WHERE {' AND '.join(where_clauses)} "
        f"GROUP BY machine_id, machine_name, line_name, metric, unit "
        f"HAVING MAX(measure_value::double) > 4.0 "
        f"ORDER BY current_value DESC"
    )
    return client.execute_query(query)
```

### Simulating IoT Data (for testing)

The `deploy/seed_data.py` script writes sample sensor readings to Timestream:

```python
# Writes 7 days of vibration data for Machine 42 (trending upward)
for hours_ago in range(168, 0, -4):
    ts = str(now - (hours_ago * 3600 * 1000))
    base = 2.5 + (168 - hours_ago) * 0.02  # Gradual increase
    records.append({
        "Time": ts,
        "Dimensions": [
            {"Name": "machine_id", "Value": "42"},
            {"Name": "metric", "Value": "vibration"},
            {"Name": "unit", "Value": "mm/s"},
        ],
        "MeasureName": "value",
        "MeasureValue": f"{base:.2f}",
        "MeasureValueType": "DOUBLE",
    })

write_client.write_records(DatabaseName=database, TableName=table, Records=batch)
```

You can also publish live sensor data via MQTT to test the IoT Core → Timestream pipeline:

```bash
aws iot-data publish \
  --topic "manufacturing/sensors/machine42" \
  --payload '{"machine_id":"42","machine_name":"Machine 42","line_name":"Line 4","plant":"Plant 1","metric":"vibration","value":5.2,"unit":"mm/s"}'
```

{{% notice tip %}}
**Exercise:** Look at `src/servers/supply_chain_server.py` and `src/servers/analytics_server.py`. They follow the same pattern. Can you identify what tools each exposes and what data they return?
{{% /notice %}}
