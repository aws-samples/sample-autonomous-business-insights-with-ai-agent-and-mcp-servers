# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Amazon Timestream client for IoT sensor telemetry data.

Uses Timestream Query API for time-series sensor readings.
Source: AWS IoT Core → IoT Rule → Amazon Timestream

Environment variables:
  TIMESTREAM_DATABASE: Timestream database name (default: "manufacturing_iot")
  TIMESTREAM_TABLE: Timestream table name (default: "sensor_readings")
"""

import json
import logging
import os
from typing import Any

import boto3

logger = logging.getLogger(__name__)


class TimestreamClient:
    """Client for querying Amazon Timestream."""

    def __init__(self) -> None:
        self.client = boto3.client("timestream-query")
        self.database = os.getenv("TIMESTREAM_DATABASE", "manufacturing_iot")
        self.table = os.getenv("TIMESTREAM_TABLE", "sensor_readings")

    def execute_query(self, query: str) -> list[dict[str, Any]]:
        """Execute a Timestream SQL query.

        Args:
            query: Timestream SQL query string.

        Returns:
            List of row dictionaries.
        """
        rows = []
        paginator = self.client.get_paginator("query")

        for page in paginator.paginate(QueryString=query):
            columns = [col["Name"] for col in page["ColumnInfo"]]
            for row in page["Rows"]:
                parsed_row = {}
                for i, datum in enumerate(row["Data"]):
                    value = datum.get("ScalarValue")
                    parsed_row[columns[i]] = value
                rows.append(parsed_row)

        return rows


# --------------------------------------------------------------------------
# Domain query functions
# --------------------------------------------------------------------------

_client: TimestreamClient | None = None


def _get_client() -> TimestreamClient:
    global _client
    if _client is None:
        _client = TimestreamClient()
    return _client


def query_sensor_readings(
    machine_id: int,
    metric: str = "temperature",
    days: int = 7,
) -> list[dict]:
    """Query IoT sensor time-series from Timestream."""
    client = _get_client()
    query = (
        f"SELECT time, machine_id, metric, measure_value::double as value, unit "
        f"FROM \"{client.database}\".\"{client.table}\" "
        f"WHERE machine_id = '{machine_id}' "
        f"AND metric = '{metric}' "
        f"AND time >= ago({days}d) "
        f"ORDER BY time ASC"
    )
    return client.execute_query(query)


def query_anomalies(
    line: str | None = None,
    plant: str | None = None,
) -> list[dict]:
    """Query recent anomalies — readings exceeding thresholds.

    Uses Timestream to find the latest readings per machine that exceed
    known thresholds. In production, this could also query a materialized
    anomaly table populated by a SageMaker inference pipeline.
    """
    client = _get_client()

    # Get latest readings per machine and check against thresholds
    where_clauses = ["time >= ago(24h)"]
    if line:
        where_clauses.append(f"line_name = '{line}'")
    if plant:
        where_clauses.append(f"plant = '{plant}'")

    query = (
        f"SELECT machine_id, machine_name, line_name, metric, "
        f"MAX(measure_value::double) as current_value, unit "
        f"FROM \"{client.database}\".\"{client.table}\" "
        f"WHERE {' AND '.join(where_clauses)} "
        f"GROUP BY machine_id, machine_name, line_name, metric, unit "
        f"HAVING MAX(measure_value::double) > 4.0 "  # Simplified threshold
        f"ORDER BY current_value DESC"
    )
    return client.execute_query(query)
