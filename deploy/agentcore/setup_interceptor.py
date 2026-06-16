#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Setup AgentCore Gateway Interceptors (Request + Response).

Creates:
1. REQUEST Interceptor Lambda — enriches requests with user identity from JWT
2. RESPONSE Interceptor Lambda — filters tool list based on user role
3. Attaches both to the Gateway

Interceptor execution order:
  Agent → Gateway → REQUEST Interceptor → Cedar Policy → Tool → RESPONSE Interceptor → Agent

Usage:
    python deploy/agentcore/setup_interceptor.py --region us-west-2
"""

import argparse
import io
import json
import logging
import time
import zipfile
from pathlib import Path

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

LAMBDA_DIR = Path(__file__).parent / "lambda_functions"


def create_interceptor_lambda(
    lambda_client, iam_client, function_name: str, code_file: str, description: str
) -> str:
    """Create a Lambda function from a source file."""
    code_path = LAMBDA_DIR / code_file
    code_content = code_path.read_text()

    # Create execution role
    role_name = f"Lambda-{function_name}-Role"
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}
        ],
    }

    try:
        role_resp = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
        )
        iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        )
        role_arn = role_resp["Role"]["Arn"]
        logger.info(f"  Role created: {role_name}")
        time.sleep(10)
    except iam_client.exceptions.EntityAlreadyExistsException:
        role_arn = iam_client.get_role(RoleName=role_name)["Role"]["Arn"]
        logger.info(f"  Role exists: {role_name}")

    # Package code
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("lambda_function.py", code_content)
    zip_buffer.seek(0)

    # Create or update Lambda
    try:
        response = lambda_client.create_function(
            FunctionName=function_name,
            Runtime="python3.12",
            Role=role_arn,
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": zip_buffer.read()},
            Timeout=30,
            MemorySize=256,
            Description=description,
        )
        lambda_arn = response["FunctionArn"]
        logger.info(f"  Lambda created: {function_name}")
    except lambda_client.exceptions.ResourceConflictException:
        # Update existing
        zip_buffer.seek(0)
        lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_buffer.read(),
        )
        lambda_arn = lambda_client.get_function(FunctionName=function_name)["Configuration"]["FunctionArn"]
        logger.info(f"  Lambda updated: {function_name}")

    return lambda_arn


def main():
    parser = argparse.ArgumentParser(description="Setup Gateway Interceptors")
    parser.add_argument("--region", default="us-west-2")
    args = parser.parse_args()

    session = boto3.Session(region_name=args.region)
    lambda_client = session.client("lambda")
    iam_client = session.client("iam")

    print("\n" + "=" * 60)
    print("  AgentCore Gateway Interceptors Setup")
    print("=" * 60 + "\n")

    # Create REQUEST interceptor
    logger.info("Step 1: Creating REQUEST Interceptor Lambda...")
    request_arn = create_interceptor_lambda(
        lambda_client, iam_client,
        function_name="MfgInsights-RequestInterceptor",
        code_file="request_interceptor.py",
        description="AgentCore Gateway - Extract JWT claims, inject user context",
    )

    # Create RESPONSE interceptor
    logger.info("\nStep 2: Creating RESPONSE Interceptor Lambda...")
    response_arn = create_interceptor_lambda(
        lambda_client, iam_client,
        function_name="MfgInsights-ResponseInterceptor",
        code_file="response_interceptor.py",
        description="AgentCore Gateway - Filter tool list by role",
    )

    # Save config
    config = {
        "region": args.region,
        "request_interceptor_arn": request_arn,
        "response_interceptor_arn": response_arn,
        "attachment_instructions": {
            "note": "Use GatewayClient or agentcore CLI to attach interceptors to Gateway",
            "request": f"Attach {request_arn} as REQUEST interceptor",
            "response": f"Attach {response_arn} as RESPONSE interceptor",
        },
    }

    config_path = Path(__file__).parent / "interceptor_config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n{'=' * 60}")
    print("  Interceptors Ready!")
    print(f"{'=' * 60}")
    print(f"  REQUEST:  {request_arn}")
    print(f"  RESPONSE: {response_arn}")
    print(f"  Config:   {config_path}")
    print(f"\n  To test: python deploy/agentcore/test_agentcore.py --region {args.region}\n")


if __name__ == "__main__":
    main()
