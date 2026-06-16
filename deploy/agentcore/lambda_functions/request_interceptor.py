# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""AgentCore Gateway REQUEST Interceptor.

This Lambda runs BEFORE Cedar policy evaluation and BEFORE the tool executes.
It enriches the MCP request with user identity context extracted from the JWT.

Flow:
  Agent → Gateway → [THIS INTERCEPTOR] → Policy Engine → Tool Target

What it does:
1. Extracts bearer token from Authorization header
2. Decodes Cognito JWT claims (role, scope attributes)
3. Injects user_context into tool arguments (available to Cedar as context.input.*)
4. Sets x-user-role header for the response interceptor

Why a Lambda interceptor (not Cedar alone):
- JWT decoding requires code execution
- Scope attributes need parsing (comma-separated → list)
- Cedar can only evaluate attributes already present in the request

Reference: https://aws.amazon.com/blogs/machine-learning/secure-ai-agents-with-policy-and-lambda-interceptors-in-amazon-bedrock-agentcore-gateway/
"""

import json
import logging
import base64

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """Enrich MCP request with user identity from Cognito JWT."""
    mcp_data = event.get("mcp", {})
    gateway_request = mcp_data.get("gatewayRequest", {})
    body = gateway_request.get("body", {})
    headers = gateway_request.get("headers", {})

    # Extract bearer token
    auth_header = headers.get("authorization", headers.get("Authorization", ""))
    token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else None

    if not token:
        logger.warning("Missing authorization token")
        return _build_error("Missing authorization token", 401)

    # Decode JWT payload (Cognito tokens are base64-encoded JSON)
    # Note: Signature verification is handled by Gateway's built-in JWT authorizer.
    # The interceptor only needs to read claims.
    try:
        claims = _decode_jwt_payload(token)
    except Exception as e:
        logger.error(f"JWT decode failed: {e}")
        return _build_error(f"Invalid token: {e}", 401)

    # Extract user attributes from Cognito custom claims
    user_context = {
        "user_id": claims.get("sub", ""),
        "username": claims.get("cognito:username", claims.get("username", "")),
        "email": claims.get("email", ""),
        "role": claims.get("custom:role", ""),
        "line_scope": _parse_csv(claims.get("custom:line_scope", "")),
        "plant_scope": _parse_csv(claims.get("custom:plant_scope", "")),
        "equipment_scope": _parse_csv(claims.get("custom:equipment_scope", "")),
        "groups": claims.get("cognito:groups", []),
    }

    logger.info(
        f"Request interceptor: user={user_context['username']}, "
        f"role={user_context['role']}, "
        f"tool={_extract_tool_name(body)}"
    )

    # Inject user context into tool arguments
    # This makes it available to Cedar as context.input.user_context.*
    if "params" in body and "arguments" in body["params"]:
        if body["params"]["arguments"] is None:
            body["params"]["arguments"] = {}
        body["params"]["arguments"]["user_context"] = user_context

    # Set role header for response interceptor to use
    headers["x-user-role"] = user_context["role"]
    headers["x-user-id"] = user_context["user_id"]

    return {
        "interceptorOutputVersion": "1.0",
        "mcp": {
            "transformedGatewayRequest": {
                "headers": headers,
                "body": body,
            }
        },
    }


def _decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload without verification (Gateway handles signature)."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Token is not a valid JWT (expected 3 parts)")

    # Decode payload (second part)
    payload = parts[1]
    # Add padding if needed
    padding = 4 - len(payload) % 4
    if padding != 4:
        payload += "=" * padding

    decoded = base64.urlsafe_b64decode(payload)
    return json.loads(decoded)


def _parse_csv(value: str) -> list[str]:
    """Parse comma-separated value into list, stripping whitespace."""
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _extract_tool_name(body: dict) -> str:
    """Extract tool name from MCP request body."""
    params = body.get("params", {})
    return params.get("name", "unknown")


def _build_error(message: str, status_code: int) -> dict:
    """Build MCP error response that terminates the request."""
    return {
        "interceptorOutputVersion": "1.0",
        "mcp": {
            "transformedGatewayRequest": {
                "headers": {},
                "body": {
                    "jsonrpc": "2.0",
                    "error": {"code": -32600, "message": message},
                    "id": None,
                },
            }
        },
    }
