# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""IoT Telemetry MCP Server.

Exposes tools for querying real-time sensor data and detecting anomalies.

Data path (live mode):
  MCP Tool → data_provider → timestream_client → Amazon Timestream
    └── Source: AWS IoT Core → IoT Rule → Amazon Timestream (time-series)

Data path (simulated mode, default):
  MCP Tool → data_provider → sample_data.py (in-memory generation)

Set DATA_MODE=live in .env to use real infrastructure.
"""

import json
import os

from mcp.server import FastMCP

from src.data.data_provider import (
    get_sensor_readings as _get_sensor_readings,
    detect_anomaly as _detect_anomaly,
)

mcp = FastMCP("IoT Telemetry Server", port=int(os.getenv("IOT_TELEMETRY_SERVER_PORT", "8002")))


VALID_METRICS = ("temperature", "vibration", "pressure")
MAX_DAYS = 90


@mcp.tool(description="Get sensor readings (temperature, vibration, pressure) for a specific machine over a given time period.")
def get_sensor_readings(
    machine_id: int,
    metric: str = "temperature",
    days: int = 7,
) -> str:
    """Retrieve time-series sensor data for a machine.

    Args:
        machine_id: The machine ID number.
        metric: Sensor metric type — "temperature", "vibration", or "pressure".
        days: Number of days of historical data to retrieve (default: 7).

    Returns:
        JSON string with sensor readings and summary statistics.
    """
    if not isinstance(machine_id, int) or machine_id < 1:
        return json.dumps({"error": "machine_id must be a positive integer."})
    if metric not in VALID_METRICS:
        return json.dumps({"error": f"metric must be one of {VALID_METRICS}."})
    if not isinstance(days, int) or days < 1 or days > MAX_DAYS:
        return json.dumps({"error": f"days must be an integer between 1 and {MAX_DAYS}."})
    return _get_sensor_readings(machine_id=machine_id, metric=metric, days=days)


@mcp.tool(description="Detect anomalies across sensors for one or more assembly lines. Returns machines with readings exceeding warning or critical thresholds.")
def detect_anomaly(
    line: str | None = None,
    plant: str | None = None,
    metric: str | None = None,
) -> str:
    """Scan for anomalous sensor readings across equipment.

    Args:
        line: Specific assembly line to check. If None, checks all accessible lines.
        plant: Specific plant to check. If None, checks all accessible plants.
        metric: Specific metric to check. If None, checks all metrics.

    Returns:
        JSON string with detected anomalies ranked by severity.
    """
    if metric is not None and metric not in VALID_METRICS:
        return json.dumps({"error": f"metric must be one of {VALID_METRICS} or None."})
    if line is not None and not isinstance(line, str):
        return json.dumps({"error": "line must be a string or None."})
    if plant is not None and not isinstance(plant, str):
        return json.dumps({"error": "plant must be a string or None."})
    return _detect_anomaly(line=line, plant=plant, metric=metric)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
