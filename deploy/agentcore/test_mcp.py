#!/usr/bin/env python3
"""Test Gateway via MCP protocol with Cognito auth."""

import asyncio
import boto3
import json
import httpx

REGION = "us-east-1"
POOL_ID = "us-east-1_EXAMPLE"
CLIENT_ID = "EXAMPLE_CLIENT_ID"
GATEWAY_URL = "https://your-gateway-id.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp/"


def get_token(username, password):
    cognito = boto3.client("cognito-idp", region_name=REGION)
    resp = cognito.admin_initiate_auth(
        UserPoolId=POOL_ID, ClientId=CLIENT_ID,
        AuthFlow="ADMIN_USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": username, "PASSWORD": password},
    )
    return resp["AuthenticationResult"]["IdToken"]


async def mcp_call(token, method, params=None):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params:
        body["params"] = params

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(GATEWAY_URL, headers=headers, json=body)
        return resp.status_code, resp.text


async def main():
    print("=" * 70)
    print("  TESTING GATEWAY via MCP PROTOCOL")
    print("=" * 70)

    # Get tokens
    print("\n[1] Authenticating users via Cognito...")
    raj_token = get_token("raj.patel", "RajPatel!2026")
    sarah_token = get_token("sarah.chen", "SarahChen!2026")
    priya_token = get_token("priya.nair", "PriyaNair!2026")
    print("  OK: 3 tokens obtained")

    # Initialize MCP session
    print("\n[2] MCP Initialize (Raj)...")
    status, body = await mcp_call(raj_token, "initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test-client", "version": "1.0"},
    })
    print(f"  Status: {status}")
    print(f"  Response: {body[:200]}")

    # List tools
    print("\n[3] MCP tools/list (Raj)...")
    status, body = await mcp_call(raj_token, "tools/list", {})
    print(f"  Status: {status}")
    print(f"  Response: {body[:300]}")

    # Call a tool — Raj's line (should work)
    print("\n[4] tools/call — Raj → Line 7 OEE (SHOULD ALLOW)...")
    status, body = await mcp_call(raj_token, "tools/call", {
        "name": "AnalyticsTarget___get_oee_trends",
        "arguments": {"line": "Line 7"},
    })
    print(f"  Status: {status}")
    print(f"  Response: {body[:300]}")

    # Call a tool — NOT Raj's line (should deny via Cedar)
    print("\n[5] tools/call — Raj → Line 4 OEE (SHOULD DENY)...")
    status, body = await mcp_call(raj_token, "tools/call", {
        "name": "AnalyticsTarget___get_oee_trends",
        "arguments": {"line": "Line 4"},
    })
    print(f"  Status: {status}")
    print(f"  Response: {body[:300]}")

    # Priya — her machine
    print("\n[6] tools/call — Priya → Machine 42 (SHOULD ALLOW)...")
    status, body = await mcp_call(priya_token, "tools/call", {
        "name": "IoTTarget___get_sensor_readings",
        "arguments": {"machine_id": 42},
    })
    print(f"  Status: {status}")
    print(f"  Response: {body[:300]}")

    # Priya — NOT her machine
    print("\n[7] tools/call — Priya → Machine 72 (SHOULD DENY)...")
    status, body = await mcp_call(priya_token, "tools/call", {
        "name": "IoTTarget___get_sensor_readings",
        "arguments": {"machine_id": 72},
    })
    print(f"  Status: {status}")
    print(f"  Response: {body[:300]}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
