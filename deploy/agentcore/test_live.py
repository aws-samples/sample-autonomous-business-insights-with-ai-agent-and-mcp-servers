#!/usr/bin/env python3
"""Test the LIVE AgentCore Gateway with real Cognito tokens."""

import boto3
import json
import requests

REGION = "us-east-1"
POOL_ID = "us-east-1_wBnf60sfQ"
CLIENT_ID = "5fu4vkccn1ndlr62vp79nnb5po"
GATEWAY_URL = "https://mfginsightsgateway-kbvnf0ga6j.gateway.bedrock-agentcore.us-east-1.amazonaws.com"

cognito = boto3.client("cognito-idp", region_name=REGION)


def get_token(username, password):
    resp = cognito.admin_initiate_auth(
        UserPoolId=POOL_ID, ClientId=CLIENT_ID,
        AuthFlow="ADMIN_USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": username, "PASSWORD": password},
    )
    return resp["AuthenticationResult"]["IdToken"]


def call_tool(token, tool_name, arguments):
    resp = requests.post(
        GATEWAY_URL,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
              "params": {"name": tool_name, "arguments": arguments}},
        timeout=15,
    )
    return resp.status_code, resp.text[:200]


def main():
    print("=" * 70)
    print("  TESTING REAL AGENTCORE GATEWAY")
    print(f"  URL: {GATEWAY_URL}")
    print("=" * 70)

    # Authenticate
    print("\n[Auth] Getting Cognito tokens...")
    sarah_token = get_token("sarah.chen", "SarahChen!2026")
    raj_token = get_token("raj.patel", "RajPatel!2026")
    priya_token = get_token("priya.nair", "PriyaNair!2026")
    print("  OK: All 3 users authenticated via Cognito")

    # Tests
    tests = [
        ("Sarah", sarah_token, "EquipmentTarget___get_equipment_status", {"line": "Line 4"}, "ALLOW"),
        ("Sarah", sarah_token, "IoTTarget___get_sensor_readings", {"machine_id": 72}, "ALLOW"),
        ("Raj", raj_token, "AnalyticsTarget___get_oee_trends", {"line": "Line 7"}, "ALLOW"),
        ("Raj", raj_token, "AnalyticsTarget___get_oee_trends", {"line": "Line 4"}, "DENY"),
        ("Raj", raj_token, "EquipmentTarget___get_equipment_status", {"line": "Line 4"}, "DENY"),
        ("Priya", priya_token, "IoTTarget___get_sensor_readings", {"machine_id": 42}, "ALLOW"),
        ("Priya", priya_token, "IoTTarget___get_sensor_readings", {"machine_id": 72}, "DENY"),
        ("Priya", priya_token, "EquipmentTarget___get_maintenance_history", {"machine_id": 42}, "ALLOW"),
        ("Priya", priya_token, "EquipmentTarget___get_maintenance_history", {"machine_id": 99}, "DENY"),
    ]

    print(f"\n  {'User':<8} {'Tool':<40} {'Args':<22} {'Expected':<8} {'Status':<6} {'Body'}")
    print("  " + "-" * 110)

    for user, token, tool, args, expected in tests:
        status_code, body_text = call_tool(token, tool, args)
        tool_short = tool.split("___")[1] if "___" in tool else tool
        args_str = json.dumps(args)[:20]
        print(f"  {user:<8} {tool_short:<40} {args_str:<22} {expected:<8} {status_code:<6} {body_text[:60]}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
