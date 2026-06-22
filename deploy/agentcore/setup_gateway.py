#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Setup AgentCore Gateway with Lambda targets for manufacturing tools.

Creates:
1. AgentCore Gateway with Cognito OAuth authorizer
2. Four Lambda tool targets (Equipment, IoT, Supply Chain, Analytics)
3. Semantic Layer Lambda target
4. Saves Gateway config for policy and interceptor setup

Prerequisites:
- Run setup_identity.py first (creates Cognito)
- AWS CLI configured with appropriate permissions

Usage:
    python deploy/agentcore/setup_gateway.py --region us-west-2
"""

import argparse
import json
import logging
import time
from pathlib import Path

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Tool schemas for each domain Lambda target
TOOL_SCHEMAS = {
    "EquipmentTarget": [
        {
            "name": "get_equipment_status",
            "description": "Get current status and metadata for equipment on a specific assembly line or machine.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "line": {"type": "string", "description": "Assembly line (e.g., 'Line 4')"},
                    "machine_id": {"type": "integer", "description": "Machine ID number"},
                    "plant": {"type": "string", "description": "Plant identifier (e.g., 'Plant 1')"},
                },
            },
        },
        {
            "name": "get_maintenance_history",
            "description": "Get maintenance history for a specific machine including repairs and inspections.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "machine_id": {"type": "integer", "description": "Machine ID number"},
                },
                "required": ["machine_id"],
            },
        },
        {
            "name": "get_shared_infrastructure",
            "description": "Get shared infrastructure relationships between assembly lines (coolant, power, air).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "line": {"type": "string", "description": "Assembly line to filter"},
                },
            },
        },
    ],
    "IoTTarget": [
        {
            "name": "get_sensor_readings",
            "description": "Get sensor readings (temperature, vibration, pressure) for a machine over time.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "machine_id": {"type": "integer", "description": "Machine ID"},
                    "metric": {"type": "string", "enum": ["temperature", "vibration", "pressure"]},
                    "days": {"type": "integer", "description": "Days of history (default 7)"},
                },
                "required": ["machine_id"],
            },
        },
        {
            "name": "detect_anomaly",
            "description": "Detect anomalies across sensors for assembly lines. Returns machines exceeding thresholds.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "line": {"type": "string", "description": "Assembly line to check"},
                    "plant": {"type": "string", "description": "Plant to check"},
                    "metric": {"type": "string", "enum": ["temperature", "vibration", "pressure"]},
                },
            },
        },
    ],
    "SupplyChainTarget": [
        {
            "name": "check_parts_inventory",
            "description": "Check spare parts inventory levels with stock status and reorder alerts.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "part_id": {"type": "string", "description": "Part identifier"},
                    "machine_id": {"type": "integer", "description": "Machine ID for applicable parts"},
                },
            },
        },
        {
            "name": "get_supplier_lead_times",
            "description": "Get supplier lead times and procurement options for a part.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "part_id": {"type": "string", "description": "Part identifier"},
                },
                "required": ["part_id"],
            },
        },
    ],
    "AnalyticsTarget": [
        {
            "name": "get_oee_trends",
            "description": "Get OEE (Overall Equipment Effectiveness) trends for assembly lines over 4 weeks.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "line": {"type": "string", "description": "Assembly line"},
                    "plant": {"type": "string", "description": "Plant"},
                },
            },
        },
        {
            "name": "get_quality_metrics",
            "description": "Get quality metrics including scrap rates, defects, and inspection results.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "line": {"type": "string", "description": "Assembly line"},
                    "plant": {"type": "string", "description": "Plant"},
                },
            },
        },
    ],
}


def load_identity_config() -> dict:
    """Load identity config from setup_identity.py output."""
    config_path = Path(__file__).parent / "identity_config.json"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Identity config not found at {config_path}. "
            f"Run setup_identity.py first."
        )
    with open(config_path) as f:
        return json.load(f)


def create_gateway_role(iam_client, role_name: str) -> str:
    """Create IAM role for the Gateway to invoke Lambda targets."""
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }

    try:
        response = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Role for AgentCore Gateway to invoke Lambda targets",
        )
        role_arn = response["Role"]["Arn"]

        # Inline policy: invoke only MfgInsights Lambda tool targets (least-privilege)
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName="InvokeMfgInsightsLambdaTargets",
            PolicyDocument=json.dumps({
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": "lambda:InvokeFunction",
                        "Resource": f"arn:aws:lambda:*:*:function:MfgInsights-*",
                    }
                ],
            }),
        )

        logger.info(f"  Gateway role created: {role_arn}")
        return role_arn
    except iam_client.exceptions.EntityAlreadyExistsException:
        response = iam_client.get_role(RoleName=role_name)
        role_arn = response["Role"]["Arn"]
        logger.info(f"  Gateway role exists: {role_arn}")
        return role_arn


def create_tool_lambda(lambda_client, iam_client, function_name: str, target_name: str, region: str) -> str:
    """Create a Lambda function that handles tool invocations for a domain."""
    # Lambda code that dispatches to the right tool based on event
    lambda_code = f'''
import json
import sys
import os

# Import the data provider (packaged as a layer or inline)
# For demo: return simulated data
def lambda_handler(event, context):
    """Handle tool invocation from AgentCore Gateway."""
    tool_name = event.get("name", "")
    arguments = event.get("arguments", {{}})
    
    # Remove injected user_context before passing to tool logic
    user_context = arguments.pop("user_context", None)
    
    # Log for audit trail
    print(f"Tool call: {{tool_name}}, user: {{user_context.get('username', 'unknown') if user_context else 'unknown'}}")
    
    # Route to tool implementation
    # In production, this would call the actual data services
    return {{"status": "success", "tool": tool_name, "arguments": arguments, "target": "{target_name}"}}
'''

    # Create execution role
    exec_role_name = f"Lambda-{function_name}-Role"
    trust = {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}
        ],
    }

    try:
        role_resp = iam_client.create_role(
            RoleName=exec_role_name,
            AssumeRolePolicyDocument=json.dumps(trust),
        )
        iam_client.attach_role_policy(
            RoleName=exec_role_name,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        )
        exec_role_arn = role_resp["Role"]["Arn"]
        time.sleep(10)  # Wait for role propagation
    except iam_client.exceptions.EntityAlreadyExistsException:
        exec_role_arn = iam_client.get_role(RoleName=exec_role_name)["Role"]["Arn"]

    # Create Lambda
    import zipfile
    import io

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("lambda_function.py", lambda_code)
    zip_buffer.seek(0)

    try:
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime="python3.12",
            Role=exec_role_arn,
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": zip_buffer.read()},
            Timeout=30,
            MemorySize=256,
            Description=f"Manufacturing Insights - {target_name} tool handler",
        )
        lambda_arn = response["FunctionArn"]
        logger.info(f"  Lambda created: {function_name}")
    except lambda_client.exceptions.ResourceConflictException:
        lambda_arn = lambda_client.get_function(FunctionName=function_name)["Configuration"]["FunctionArn"]
        logger.info(f"  Lambda exists: {function_name}")

    return lambda_arn


def main():
    parser = argparse.ArgumentParser(description="Setup AgentCore Gateway")
    parser.add_argument("--region", default="us-west-2")
    args = parser.parse_args()

    identity_config = load_identity_config()
    session = boto3.Session(region_name=args.region)
    iam = session.client("iam")
    lambda_client = session.client("lambda")

    print("\n" + "=" * 60)
    print("  AgentCore Gateway Setup")
    print("=" * 60 + "\n")

    # Step 1: Create Gateway IAM role
    logger.info("Step 1: Creating Gateway IAM role...")
    gateway_role_arn = create_gateway_role(iam, "AgentCore-ManufacturingGateway-Role")

    # Step 2: Create Lambda functions for each target
    logger.info("\nStep 2: Creating Lambda tool targets...")
    lambda_arns = {}
    for target_name in TOOL_SCHEMAS:
        function_name = f"MfgInsights-{target_name}-{int(time.time()) % 10000}"
        arn = create_tool_lambda(lambda_client, iam, function_name, target_name, args.region)
        lambda_arns[target_name] = arn

    # Step 3: Create Gateway (using starter toolkit or boto3)
    logger.info("\nStep 3: Creating AgentCore Gateway...")
    logger.info("  NOTE: Use the bedrock-agentcore-starter-toolkit GatewayClient")
    logger.info("  or the AgentCore CLI (@aws/agentcore) for Gateway creation.")
    logger.info("  The following shows the configuration needed:")

    gateway_config = {
        "region": args.region,
        "gateway_role_arn": gateway_role_arn,
        "identity": {
            "user_pool_id": identity_config["user_pool_id"],
            "user_pool_arn": identity_config["user_pool_arn"],
            "client_id": identity_config["client_id"],
        },
        "targets": {
            target_name: {
                "lambda_arn": arn,
                "tool_schema": TOOL_SCHEMAS[target_name],
            }
            for target_name, arn in lambda_arns.items()
        },
    }

    config_path = Path(__file__).parent / "gateway_config.json"
    with open(config_path, "w") as f:
        json.dump(gateway_config, f, indent=2)

    print(f"\n{'=' * 60}")
    print("  Gateway Configuration Ready!")
    print(f"{'=' * 60}")
    print(f"  Role ARN:    {gateway_role_arn}")
    print(f"  Targets:     {list(lambda_arns.keys())}")
    print(f"  Config:      {config_path}")
    print(f"\n  To complete Gateway creation, run:")
    print(f"    pip install bedrock-agentcore-starter-toolkit")
    print(f"    # Then use GatewayClient.create_mcp_gateway()")
    print(f"\n  Next: python deploy/agentcore/setup_policy.py --region {args.region}\n")


if __name__ == "__main__":
    main()
