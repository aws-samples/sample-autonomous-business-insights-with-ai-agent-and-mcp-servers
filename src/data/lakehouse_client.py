# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""SageMaker Lakehouse / Redshift data infrastructure client.

This module provides the REAL data layer that MCP servers use in production.
It connects to Amazon Redshift (via SageMaker Lakehouse) using the Redshift
Data API, which is serverless — no connection pooling or JDBC drivers needed.

Architecture flow:
  MCP Server Tool → DataInfraClient → Redshift Data API → SageMaker Lakehouse
                                                            ├── S3 Tables
                                                            ├── Redshift tables
                                                            └── Zero-ETL sources

Prerequisites:
  - Redshift Serverless workgroup OR provisioned cluster
  - IAM role with redshift-data:ExecuteStatement permissions
  - Tables provisioned (see deploy/sql/create_tables.sql)

Environment variables:
  - REDSHIFT_WORKGROUP: Redshift Serverless workgroup name
  - REDSHIFT_DATABASE: Database name (default: "manufacturing")
  - DATA_MODE: "live" to use real infra, "simulated" for in-memory (default)
"""

import json
import logging
import os
import time
from typing import Any

import boto3

logger = logging.getLogger(__name__)

DATA_MODE = os.getenv("DATA_MODE", "simulated")


class DataInfraClient:
    """Client for querying SageMaker Lakehouse via Redshift Data API.

    The Redshift Data API is async — you submit a statement, poll for
    completion, then fetch results. This client wraps that pattern.

    In the blog architecture:
    - SageMaker Lakehouse unifies S3 data lake, Redshift, and operational stores
    - Zero-ETL replicates data from Aurora/DynamoDB into the Lakehouse
    - MCP servers query the Lakehouse using standard SQL
    """

    def __init__(self) -> None:
        self.client = boto3.client("redshift-data")
        self.workgroup = os.getenv("REDSHIFT_WORKGROUP", "manufacturing-insights")
        self.database = os.getenv("REDSHIFT_DATABASE", "manufacturing")

    def execute_query(self, sql: str, parameters: list[dict] | None = None) -> list[dict[str, Any]]:
        """Execute a SQL query against SageMaker Lakehouse (Redshift).

        Uses the Redshift Data API which is serverless and doesn't require
        connection management. Supports parameterized queries for security.

        Args:
            sql: SQL query string. Use :param_name for parameters.
            parameters: Optional list of {"name": str, "value": str} dicts.

        Returns:
            List of row dictionaries with column names as keys.
        """
        # Submit the statement
        submit_kwargs: dict[str, Any] = {
            "WorkgroupName": self.workgroup,
            "Database": self.database,
            "Sql": sql,
        }
        if parameters:
            submit_kwargs["Parameters"] = [
                {"name": p["name"], "value": str(p["value"])} for p in parameters
            ]

        response = self.client.execute_statement(**submit_kwargs)
        statement_id = response["Id"]

        logger.info("Submitted query (id=%s): %s", statement_id[:8], sql[:80])

        # Poll for completion
        rows = self._wait_and_fetch(statement_id)
        return rows

    def _wait_and_fetch(self, statement_id: str, timeout: int = 30) -> list[dict[str, Any]]:
        """Wait for query to complete and fetch results."""
        start = time.time()

        while time.time() - start < timeout:
            status_response = self.client.describe_statement(Id=statement_id)
            status = status_response["Status"]

            if status == "FINISHED":
                return self._fetch_results(statement_id)
            elif status in ("FAILED", "ABORTED"):
                error = status_response.get("Error", "Unknown error")
                raise RuntimeError(f"Query failed: {error}")

            time.sleep(0.5)

        raise TimeoutError(f"Query did not complete within {timeout}s")

    def _fetch_results(self, statement_id: str) -> list[dict[str, Any]]:
        """Fetch all result rows from a completed statement."""
        results = self.client.get_statement_result(Id=statement_id)

        columns = [col["name"] for col in results["ColumnMetadata"]]
        rows = []

        for record in results["Records"]:
            row = {}
            for i, field in enumerate(record):
                # Redshift Data API returns typed fields
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
# Domain-specific query functions used by MCP servers
# --------------------------------------------------------------------------

_client: DataInfraClient | None = None


def _get_client() -> DataInfraClient:
    """Lazy-initialize the data infrastructure client."""
    global _client
    if _client is None:
        _client = DataInfraClient()
    return _client


def query_equipment_status(
    line: str | None = None,
    machine_id: int | None = None,
    plant: str | None = None,
) -> list[dict]:
    """Query equipment registry from Lakehouse.

    Source: SAP S/4HANA → Zero-ETL → Redshift table `equipment_registry`
    """
    client = _get_client()

    if machine_id is not None:
        sql = """
            SELECT machine_id, machine_name, line_name, plant, machine_type,
                   install_date, last_maintenance, operating_hours, rated_capacity_factor
            FROM equipment_registry
            WHERE machine_id = :machine_id
        """
        return client.execute_query(sql, [{"name": "machine_id", "value": machine_id}])

    elif line is not None:
        sql = """
            SELECT machine_id, machine_name, line_name, plant, machine_type,
                   install_date, last_maintenance, operating_hours, rated_capacity_factor
            FROM equipment_registry
            WHERE line_name = :line
            ORDER BY machine_id
        """
        return client.execute_query(sql, [{"name": "line", "value": line}])

    elif plant is not None:
        sql = """
            SELECT machine_id, machine_name, line_name, plant, machine_type,
                   install_date, last_maintenance, operating_hours, rated_capacity_factor
            FROM equipment_registry
            WHERE plant = :plant
            ORDER BY line_name, machine_id
        """
        return client.execute_query(sql, [{"name": "plant", "value": plant}])

    else:
        sql = """
            SELECT line_name, plant, COUNT(*) as machine_count,
                   supervisor
            FROM assembly_lines
            GROUP BY line_name, plant, supervisor
            ORDER BY line_name
        """
        return client.execute_query(sql)


def query_maintenance_history(machine_id: int) -> list[dict]:
    """Query maintenance records from Lakehouse.

    Source: SAP PM → Zero-ETL → Redshift table `maintenance_history`
    """
    client = _get_client()
    sql = """
        SELECT maintenance_date, maintenance_type, description,
               technician, downtime_hours, cost
        FROM maintenance_history
        WHERE machine_id = :machine_id
        ORDER BY maintenance_date DESC
        LIMIT 20
    """
    return client.execute_query(sql, [{"name": "machine_id", "value": machine_id}])


def query_sensor_readings(
    machine_id: int,
    metric: str = "temperature",
    days: int = 7,
) -> list[dict]:
    """Query IoT sensor time-series from Lakehouse.

    Source: AWS IoT Core → Amazon MSK → Zero-ETL → S3 Tables (Iceberg)
    Queried via Redshift Spectrum over S3 Tables in SageMaker Lakehouse.
    """
    client = _get_client()
    sql = """
        SELECT reading_timestamp, machine_id, metric, value, unit
        FROM sensor_readings
        WHERE machine_id = :machine_id
          AND metric = :metric
          AND reading_timestamp >= DATEADD(day, -:days, GETDATE())
        ORDER BY reading_timestamp
    """
    return client.execute_query(sql, [
        {"name": "machine_id", "value": machine_id},
        {"name": "metric", "value": metric},
        {"name": "days", "value": days},
    ])


def query_anomalies(
    line: str | None = None,
    plant: str | None = None,
) -> list[dict]:
    """Query current anomalies from Lakehouse.

    Source: Real-time anomaly detection via SageMaker inference pipeline,
    results stored in Redshift table `detected_anomalies`.
    """
    client = _get_client()

    where_clauses = ["detected_at >= DATEADD(hour, -24, GETDATE())"]
    params = []

    if line:
        where_clauses.append("line_name = :line")
        params.append({"name": "line", "value": line})
    if plant:
        where_clauses.append("plant = :plant")
        params.append({"name": "plant", "value": plant})

    sql = f"""
        SELECT machine_name, line_name, metric, current_value,
               threshold_warning, threshold_critical, unit, severity, detected_at
        FROM detected_anomalies
        WHERE {' AND '.join(where_clauses)}
        ORDER BY
            CASE severity WHEN 'CRITICAL' THEN 0 ELSE 1 END,
            current_value DESC
    """
    return client.execute_query(sql, params if params else None)


def query_parts_inventory(
    part_id: str | None = None,
    machine_id: int | None = None,
) -> list[dict]:
    """Query spare parts inventory from Lakehouse.

    Source: SAP MM → Zero-ETL → Redshift table `parts_inventory`
    """
    client = _get_client()

    if part_id:
        sql = """
            SELECT part_id, description, quantity_on_hand, reorder_point,
                   lead_time_days, supplier, unit_cost
            FROM parts_inventory
            WHERE part_id = :part_id
        """
        return client.execute_query(sql, [{"name": "part_id", "value": part_id}])

    elif machine_id:
        sql = """
            SELECT p.part_id, p.description, p.quantity_on_hand, p.reorder_point,
                   p.lead_time_days, p.supplier, p.unit_cost
            FROM parts_inventory p
            JOIN part_machine_mapping pm ON p.part_id = pm.part_id
            WHERE pm.machine_id = :machine_id
        """
        return client.execute_query(sql, [{"name": "machine_id", "value": machine_id}])

    else:
        sql = """
            SELECT part_id, description, quantity_on_hand, reorder_point,
                   lead_time_days, supplier, unit_cost
            FROM parts_inventory
            ORDER BY
                CASE
                    WHEN quantity_on_hand = 0 THEN 0
                    WHEN quantity_on_hand < reorder_point * 0.5 THEN 1
                    WHEN quantity_on_hand < reorder_point THEN 2
                    ELSE 3
                END
        """
        return client.execute_query(sql)


def query_oee_trends(
    line: str | None = None,
    plant: str | None = None,
) -> list[dict]:
    """Query OEE trends from Lakehouse.

    Source: Production systems → daily ETL → Redshift table `oee_daily`
    Aggregated into weekly trends.
    """
    client = _get_client()

    where_clauses = ["week_start >= DATEADD(week, -4, GETDATE())"]
    params = []

    if line:
        where_clauses.append("line_name = :line")
        params.append({"name": "line", "value": line})
    if plant:
        where_clauses.append("plant = :plant")
        params.append({"name": "plant", "value": plant})

    sql = f"""
        SELECT line_name, plant, week_start, availability, performance,
               quality, oee
        FROM oee_weekly
        WHERE {' AND '.join(where_clauses)}
        ORDER BY line_name, week_start
    """
    return client.execute_query(sql, params if params else None)


def query_quality_metrics(
    line: str | None = None,
    plant: str | None = None,
) -> list[dict]:
    """Query quality metrics from Lakehouse.

    Source: SAP QM → Zero-ETL → Redshift table `quality_metrics`
    """
    client = _get_client()

    where_clauses = ["inspection_date >= DATEADD(week, -4, GETDATE())"]
    params = []

    if line:
        where_clauses.append("line_name = :line")
        params.append({"name": "line", "value": line})
    if plant:
        where_clauses.append("plant = :plant")
        params.append({"name": "plant", "value": plant})

    sql = f"""
        SELECT line_name, inspection_date, scrap_rate_pct,
               defect_category, units_produced, units_scrapped
        FROM quality_metrics
        WHERE {' AND '.join(where_clauses)}
        ORDER BY line_name, inspection_date DESC
    """
    return client.execute_query(sql, params if params else None)
