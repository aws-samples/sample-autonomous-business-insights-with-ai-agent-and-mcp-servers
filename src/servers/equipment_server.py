# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Equipment Status MCP Server.

Exposes tools for querying equipment registry, maintenance history, and
shared infrastructure. In production, this connects to your ERP system
(SAP S/4HANA) via SageMaker Lakehouse using the Redshift Data API.

Data path (live mode):
  MCP Tool → data_provider → lakehouse_client → Redshift Data API → SageMaker Lakehouse
    └── Source: SAP S/4HANA → Zero-ETL → Redshift

Data path (simulated mode, default):
  MCP Tool → data_provider → sample_data.py (in-memory)

Set DATA_MODE=live in .env to use real infrastructure.
"""

import json
import os

from mcp.server import FastMCP

from src.data.data_provider import (
    get_equipment_status as _get_equipment_status,
    get_maintenance_history as _get_maintenance_history,
)
from src.data.sample_data import SHARED_INFRASTRUCTURE

mcp = FastMCP("Equipment Status Server", port=int(os.getenv("EQUIPMENT_SERVER_PORT", "8001")))


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
    if machine_id is not None and (not isinstance(machine_id, int) or machine_id < 1):
        return json.dumps({"error": "machine_id must be a positive integer."})
    if line is not None and not isinstance(line, str):
        return json.dumps({"error": "line must be a string."})
    if plant is not None and not isinstance(plant, str):
        return json.dumps({"error": "plant must be a string."})
    return _get_equipment_status(line=line, machine_id=machine_id, plant=plant)


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


@mcp.tool(description="Get shared infrastructure relationships between assembly lines (coolant loops, power feeds, compressed air systems).")
def get_shared_infrastructure(line: str | None = None) -> str:
    """Identify shared infrastructure that connects assembly lines.

    This is critical context that most dashboards don't model — understanding
    shared resources helps identify correlated failures across lines.

    Args:
        line: Optional assembly line to filter relationships for.

    Returns:
        JSON string with shared infrastructure information.
    """
    if line is not None and not isinstance(line, str):
        return json.dumps({"error": "line must be a string or None."})
    # Shared infrastructure is configuration data — same in both modes
    results = {}
    for infra_id, info in SHARED_INFRASTRUCTURE.items():
        if line is None or line in info["serves"]:
            results[infra_id] = info

    return json.dumps(results, indent=2, default=str)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
