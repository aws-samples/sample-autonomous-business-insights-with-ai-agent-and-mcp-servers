# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Supply Chain MCP Server.

Exposes tools for querying parts inventory and supplier lead times.

Data path (live mode):
  MCP Tool → data_provider → lakehouse_client → Redshift Data API → SageMaker Lakehouse
    └── Source: SAP MM → Zero-ETL → Redshift (hourly batch)

Data path (simulated mode, default):
  MCP Tool → data_provider → sample_data.py (in-memory)

Set DATA_MODE=live in .env to use real infrastructure.
"""

import json
import os

from mcp.server import FastMCP

from src.data.data_provider import check_parts_inventory as _check_parts_inventory
from src.data.sample_data import PARTS_INVENTORY

mcp = FastMCP("Supply Chain Server", port=int(os.getenv("SUPPLY_CHAIN_SERVER_PORT", "8003")))


@mcp.tool(description="Check current inventory levels for spare parts, including stock status and reorder alerts.")
def check_parts_inventory(
    part_id: str | None = None,
    machine_id: int | None = None,
) -> str:
    """Query spare parts inventory with stock level assessment.

    Args:
        part_id: Specific part identifier (e.g., "bearing_6205"). Optional.
        machine_id: Machine ID to find applicable parts. Optional.

    Returns:
        JSON string with inventory status and reorder recommendations.
    """
    if machine_id is not None and (not isinstance(machine_id, int) or machine_id < 1):
        return json.dumps({"error": "machine_id must be a positive integer."})
    if part_id is not None and not isinstance(part_id, str):
        return json.dumps({"error": "part_id must be a string."})
    return _check_parts_inventory(part_id=part_id, machine_id=machine_id)


@mcp.tool(description="Get supplier lead times and procurement options for a specific part or category.")
def get_supplier_lead_times(part_id: str) -> str:
    """Retrieve supplier information and lead times for procurement planning.

    Args:
        part_id: The part identifier to look up.

    Returns:
        JSON string with supplier details and lead time information.
    """
    if not isinstance(part_id, str) or not part_id.strip():
        return json.dumps({"error": "part_id must be a non-empty string."})
    # Supplier data is reference/config data — same structure in both modes
    if part_id not in PARTS_INVENTORY:
        return json.dumps({"error": f"Part '{part_id}' not found in inventory system."})

    part = PARTS_INVENTORY[part_id]

    return json.dumps({
        "part_id": part_id,
        "description": part["description"],
        "primary_supplier": part["supplier"],
        "standard_lead_time_days": part["lead_time_days"],
        "unit_cost": part["unit_cost"],
        "expedited_available": part["lead_time_days"] > 7,
        "expedited_lead_time_days": max(3, part["lead_time_days"] // 2),
        "expedited_surcharge_pct": 25,
        "bulk_discount_threshold": 50,
        "bulk_discount_pct": 10,
    }, indent=2, default=str)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
