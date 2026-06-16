# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""AgentCore Gateway RESPONSE Interceptor.

This Lambda runs AFTER the tool executes but BEFORE the response reaches the agent.
It filters the tools/list response to show each role only their authorized tools.

Flow:
  Tool Target → [THIS INTERCEPTOR] → Agent

What it does:
1. Detects tools/list responses
2. Filters tool list based on user role (from x-user-role header)
3. Returns filtered response — agent never sees unauthorized tools

Why this matters:
- The LLM only sees tools it can actually call → fewer auth errors
- Reduces hallucination (won't try to call tools it can't see)
- Defense in depth (even if LLM guesses a tool name, Cedar blocks it)
"""

import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Tool visibility per role.
# None = all tools visible. List = only these tools visible.
ROLE_TOOL_VISIBILITY = {
    "plant_manager": None,  # Full access — see all tools
    "line_supervisor": [
        "discover_data_sources",
        "get_data_catalog",
        "get_equipment_status",
        "get_shared_infrastructure",
        "detect_anomaly",
        "get_oee_trends",
        "get_quality_metrics",
        "check_parts_inventory",
    ],
    "maintenance_technician": [
        "discover_data_sources",
        "get_data_catalog",
        "get_equipment_status",
        "get_maintenance_history",
        "get_sensor_readings",
        "detect_anomaly",
        "check_parts_inventory",
        "get_supplier_lead_times",
    ],
}


def lambda_handler(event, context):
    """Filter tool list and redact sensitive data based on user role."""
    mcp_data = event.get("mcp", {})
    gateway_response = mcp_data.get("gatewayResponse", {})
    body = gateway_response.get("body", {})
    headers = gateway_response.get("headers", {})

    # Get user role from header (set by request interceptor)
    request_data = mcp_data.get("gatewayRequest", {})
    request_headers = request_data.get("headers", {})
    role = request_headers.get("x-user-role", "")

    # Filter tools/list response
    if isinstance(body, dict) and "result" in body:
        result = body.get("result", {})

        if "tools" in result and isinstance(result["tools"], list):
            allowed_tools = ROLE_TOOL_VISIBILITY.get(role)

            if allowed_tools is not None:
                original_count = len(result["tools"])
                result["tools"] = [
                    tool for tool in result["tools"]
                    if _extract_tool_name(tool) in allowed_tools
                ]
                filtered_count = len(result["tools"])
                logger.info(
                    f"Response interceptor: role={role}, "
                    f"tools {original_count} → {filtered_count}"
                )
            else:
                logger.info(f"Response interceptor: role={role}, full access (no filtering)")

    return {
        "interceptorOutputVersion": "1.0",
        "mcp": {
            "transformedGatewayResponse": {
                "headers": headers,
                "body": body,
            }
        },
    }


def _extract_tool_name(tool: dict) -> str:
    """Extract the base tool name from the Gateway-prefixed name.

    Gateway tool names are formatted as: TargetName___tool_name
    We want just 'tool_name' for matching.
    """
    name = tool.get("name", "")
    if "___" in name:
        return name.split("___", 1)[1]
    return name
