# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Test AgentCore deployment — validates policy enforcement end-to-end.

Tests:
1. Authenticates each user via Cognito
2. Makes tool calls through the Gateway
3. Verifies policy enforcement (allow/deny per role and scope)

Expected Results:
  Sarah (plant_manager): All tools, all lines, all machines → ALLOW
  Raj (line_supervisor): Line 7 → ALLOW, Line 4 → DENY
  Priya (maintenance_technician): Machine 42 → ALLOW, Machine 72 → DENY

Usage:
    python deploy/agentcore/test_agentcore.py --region us-west-2
"""

import argparse
import json
import logging
import os
from pathlib import Path

import boto3
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_user_token(cognito_client, pool_id: str, client_id: str, username: str, password: str) -> str:
    """Authenticate user and get access token."""
    response = cognito_client.admin_initiate_auth(
        UserPoolId=pool_id,
        ClientId=client_id,
        AuthFlow="ADMIN_USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": username, "PASSWORD": password},
    )
    return response["AuthenticationResult"]["AccessToken"]


def call_tool(gateway_url: str, token: str, tool_name: str, arguments: dict) -> dict:
    """Make a tool call through the AgentCore Gateway (MCP JSON-RPC)."""
    response = requests.post(
        gateway_url,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        },
    )
    return {"status": response.status_code, "body": response.json()}


def main():
    parser = argparse.ArgumentParser(description="Test AgentCore Policy Enforcement")
    parser.add_argument("--region", default="us-west-2")
    args = parser.parse_args()

    # Load configs
    base = Path(__file__).parent
    identity_config = json.loads((base / "identity_config.json").read_text())
    gateway_config = json.loads((base / "gateway_config.json").read_text())

    session = boto3.Session(region_name=args.region)
    cognito = session.client("cognito-idp")

    pool_id = identity_config["user_pool_id"]
    client_id = identity_config["client_id"]
    gateway_url = gateway_config.get("gateway_url", "http://localhost:8000/mcp/")

    # Passwords read from environment variables
    passwords = {
        "sarah.chen": os.environ.get("DEMO_PASSWORD_SARAH", ""),
        "raj.patel": os.environ.get("DEMO_PASSWORD_RAJ", ""),
        "priya.nair": os.environ.get("DEMO_PASSWORD_PRIYA", ""),
    }
    missing_pw = [u for u, p in passwords.items() if not p]
    if missing_pw:
        print(f"\n  ERROR: Set password env vars: DEMO_PASSWORD_SARAH, DEMO_PASSWORD_RAJ, DEMO_PASSWORD_PRIYA")
        return

    # Test cases: (user, tool, args, expected_result)
    TESTS = [
        # Sarah (Plant Manager) — full access
        ("sarah.chen", passwords["sarah.chen"], "EquipmentTarget___get_equipment_status",
         {"line": "Line 4"}, "ALLOW"),
        ("sarah.chen", passwords["sarah.chen"], "IoTTarget___get_sensor_readings",
         {"machine_id": 72}, "ALLOW"),

        # Raj (Line Supervisor) — Line 7 only
        ("raj.patel", passwords["raj.patel"], "EquipmentTarget___get_equipment_status",
         {"line": "Line 7"}, "ALLOW"),
        ("raj.patel", passwords["raj.patel"], "EquipmentTarget___get_equipment_status",
         {"line": "Line 4"}, "DENY"),
        ("raj.patel", passwords["raj.patel"], "AnalyticsTarget___get_oee_trends",
         {"line": "Line 4"}, "DENY"),

        # Priya (Maintenance Tech) — Machine 41-45 only
        ("priya.nair", passwords["priya.nair"], "IoTTarget___get_sensor_readings",
         {"machine_id": 42}, "ALLOW"),
        ("priya.nair", passwords["priya.nair"], "IoTTarget___get_sensor_readings",
         {"machine_id": 72}, "DENY"),
        ("priya.nair", passwords["priya.nair"], "EquipmentTarget___get_maintenance_history",
         {"machine_id": 42}, "ALLOW"),
        ("priya.nair", passwords["priya.nair"], "EquipmentTarget___get_maintenance_history",
         {"machine_id": 99}, "DENY"),
    ]

    print("\n" + "=" * 70)
    print("  AgentCore Policy Enforcement — Test Results")
    print("=" * 70)
    print(f"  {'User':<15} {'Tool':<45} {'Args':<20} {'Expected':<8} {'Actual':<8} {'Status'}")
    print("  " + "─" * 68)

    passed = 0
    failed = 0
    tokens = {}

    for username, password, tool, args_dict, expected in TESTS:
        # Get token (cache per user)
        if username not in tokens:
            try:
                tokens[username] = get_user_token(cognito, pool_id, client_id, username, password)
            except Exception as e:
                print(f"  Auth failed for {username}: {e}")
                failed += 1
                continue

        # Make tool call
        try:
            result = call_tool(gateway_url, tokens[username], tool, args_dict)
            status_code = result["status"]

            if status_code == 200:
                actual = "ALLOW"
            elif status_code == 403:
                actual = "DENY"
            else:
                actual = f"HTTP{status_code}"
        except Exception as e:
            actual = f"ERR"

        # Compare
        match = "✅" if actual == expected else "❌"
        if actual == expected:
            passed += 1
        else:
            failed += 1

        tool_short = tool.split("___")[1] if "___" in tool else tool
        args_short = json.dumps(args_dict)[:18]
        print(f"  {username:<15} {tool_short:<45} {args_short:<20} {expected:<8} {actual:<8} {match}")

    print("  " + "─" * 68)
    print(f"\n  Results: {passed} passed, {failed} failed, {passed + failed} total")
    if failed == 0:
        print("  ✅ All tests passed! Policy enforcement working correctly.")
    else:
        print("  ❌ Some tests failed. Check Cedar policies and interceptor logic.")
    print()


if __name__ == "__main__":
    main()
