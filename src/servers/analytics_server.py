# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Analytics MCP Server.

Exposes tools for querying OEE trends and quality metrics.

Data path (live mode):
  MCP Tool → data_provider → lakehouse_client → Redshift Data API → SageMaker Lakehouse
    └── Source: Production systems → daily ETL → Redshift (oee_weekly, quality_metrics)

Data path (simulated mode, default):
  MCP Tool → data_provider → sample_data.py (in-memory)

Set DATA_MODE=live in .env to use real infrastructure.
"""

import json
import os

from mcp.server import FastMCP

from src.data.data_provider import (
    get_oee_trends as _get_oee_trends,
    get_quality_metrics as _get_quality_metrics,
)

mcp = FastMCP("Analytics Server", port=int(os.getenv("ANALYTICS_SERVER_PORT", "8004")))


@mcp.tool(description="Get OEE (Overall Equipment Effectiveness) trends for assembly lines over the past 4 weeks. OEE = Availability × Performance × Quality.")
def get_oee_trends(
    line: str | None = None,
    plant: str | None = None,
) -> str:
    """Retrieve OEE trend data for assembly lines.

    Args:
        line: Specific assembly line (e.g., "Line 4"). Optional.
        plant: Specific plant to filter. Optional.

    Returns:
        JSON string with weekly OEE trends and change indicators.
    """
    if line is not None and not isinstance(line, str):
        return json.dumps({"error": "line must be a string or None."})
    if plant is not None and not isinstance(plant, str):
        return json.dumps({"error": "plant must be a string or None."})
    return _get_oee_trends(line=line, plant=plant)


@mcp.tool(description="Get quality metrics including scrap rates, defect categories, and inspection results for assembly lines.")
def get_quality_metrics(
    line: str | None = None,
    plant: str | None = None,
) -> str:
    """Retrieve quality management data for assembly lines.

    Args:
        line: Specific assembly line. Optional.
        plant: Specific plant. Optional.

    Returns:
        JSON string with quality metrics and trend indicators.
    """
    if line is not None and not isinstance(line, str):
        return json.dumps({"error": "line must be a string or None."})
    if plant is not None and not isinstance(plant, str):
        return json.dumps({"error": "plant must be a string or None."})
    return _get_quality_metrics(line=line, plant=plant)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
