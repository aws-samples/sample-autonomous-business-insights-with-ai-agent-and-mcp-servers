#!/usr/bin/env python3
"""Quick Gateway test with ID token."""
import boto3
import httpx
import asyncio

REGION = "us-east-1"
POOL_ID = "us-east-1_EXAMPLE"
CLIENT_ID = "EXAMPLE_CLIENT_ID"
GW_URL = "https://your-gateway-id.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp/"

cognito = boto3.client("cognito-idp", region_name=REGION)


def get_tokens(username, password):
    resp = cognito.admin_initiate_auth(
        UserPoolId=POOL_ID, ClientId=CLIENT_ID,
        AuthFlow="ADMIN_USER_PASSWORD_AUTH",
        AuthParameters={"USERNAME": username, "PASSWORD": password},
    )
    return {
        "id": resp["AuthenticationResult"]["IdToken"],
        "access": resp["AuthenticationResult"]["AccessToken"],
    }


async def call(token, method, params=None):
    body = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params:
        body["params"] = params
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(GW_URL, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=body)
        return r.status_code, r.text[:200]


async def main():
    tokens = get_tokens("raj.patel", "RajPatel!2026")

    print("Testing with ID token:")
    s, b = await call(tokens["id"], "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}})
    print(f"  initialize: {s} | {b}")

    s, b = await call(tokens["id"], "tools/list", {})
    print(f"  tools/list: {s} | {b}")

    print("\nTesting with Access token:")
    s, b = await call(tokens["access"], "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}})
    print(f"  initialize: {s} | {b}")


asyncio.run(main())
