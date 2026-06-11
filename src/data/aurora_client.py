# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Amazon Aurora PostgreSQL client for Equipment and Maintenance data.

Uses the RDS Data API (serverless, no connection pooling needed).
Source: SAP S/4HANA → Zero-ETL → Aurora PostgreSQL Serverless v2

Environment variables:
  AURORA_CLUSTER_ARN: Aurora cluster ARN
  AURORA_SECRET_ARN: Secrets Manager secret ARN for DB credentials
  AURORA_DATABASE: Database name (default: "manufacturing")
"""

import json
import logging
import os
from typing import Any

import boto3

logger = logging.getLogger(__name__)


class AuroraClient:
    """Client for querying Aurora PostgreSQL via RDS Data API."""

    def __init__(self) -> None:
        self.client = boto3.client("rds-data")
        self.cluster_arn = os.getenv("AURORA_CLUSTER_ARN", "")
        self.secret_arn = os.getenv("AURORA_SECRET_ARN", "")
        self.database = os.getenv("AURORA_DATABASE", "manufacturing")

    def execute_query(self, sql: str, parameters: list[dict] | None = None) -> list[dict[str, Any]]:
        """Execute a SQL query against Aurora via RDS Data API.

        Args:
            sql: SQL query with :param_name placeholders.
            parameters: List of {"name": str, "value": {"stringValue"|"longValue": val}}.

        Returns:
            List of row dictionaries.
        """
        kwargs: dict[str, Any] = {
            "resourceArn": self.cluster_arn,
            "secretArn": self.secret_arn,
            "database": self.database,
            "sql": sql,
            "includeResultMetadata": True,
        }
        if parameters:
            kwargs["parameters"] = parameters

        response = self.client.execute_statement(**kwargs)
        return self._parse_response(response)

    def _parse_response(self, response: dict) -> list[dict[str, Any]]:
        """Parse RDS Data API response into row dictionaries."""
        if "columnMetadata" not in response:
            return []

        columns = [col["name"] for col in response["columnMetadata"]]
        rows = []

        for record in response.get("records", []):
            row = {}
            for i, field in enumerate(record):
                if "stringValue" in field:
                    row[columns[i]] = field["stringValue"]
                elif "longValue" in field:
                    row[columns[i]] = field["longValue"]
                elif "doubleValue" in field:
                    row[columns[i]] = field["doubleValue"]
                elif "booleanValue" in field:
                    row[columns[i]] = field["booleanValue"]
                elif "isNull" in field and field["isNull"]:
                    row[columns[i]] = None
                else:
                    row[columns[i]] = str(field)
            rows.append(row)

        return rows


# --------------------------------------------------------------------------
# Domain query functions
# --------------------------------------------------------------------------

_client: AuroraClient | None = None


def _get_client() -> AuroraClient:
    global _client
    if _client is None:
        _client = AuroraClient()
    return _client


def query_equipment_status(
    line: str | None = None,
    machine_id: int | None = None,
    plant: str | None = None,
) -> list[dict]:
    """Query equipment registry from Aurora."""
    client = _get_client()

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
    elif plant is not None:
        return client.execute_query(
            "SELECT * FROM equipment_registry WHERE plant = :plant ORDER BY line_name, machine_id",
            [{"name": "plant", "value": {"stringValue": plant}}],
        )
    else:
        return client.execute_query(
            "SELECT line_name, plant, COUNT(*) as machine_count, supervisor "
            "FROM assembly_lines GROUP BY line_name, plant, supervisor ORDER BY line_name"
        )


def query_maintenance_history(machine_id: int) -> list[dict]:
    """Query maintenance records from Aurora."""
    client = _get_client()
    return client.execute_query(
        "SELECT maintenance_date, maintenance_type, description, technician, "
        "downtime_hours, cost FROM maintenance_history "
        "WHERE machine_id = :mid ORDER BY maintenance_date DESC LIMIT 20",
        [{"name": "mid", "value": {"longValue": machine_id}}],
    )
