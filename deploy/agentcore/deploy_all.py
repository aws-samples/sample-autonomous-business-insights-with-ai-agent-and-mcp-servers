# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Deploy the full AgentCore stack for Manufacturing Insights.

Runs all setup scripts in order:
1. Identity (Cognito User Pool + users)
2. Gateway (Lambda targets + tool schemas)
3. Policy (Cedar rules + Policy Engine)
4. Interceptors (Request + Response Lambda)

Usage:
    python deploy/agentcore/deploy_all.py --region us-west-2

Estimated time: ~5 minutes
Estimated cost: ~$2-5/month for demo usage (Cognito free tier, Lambda pay-per-use)
"""

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
SCRIPTS = [
    ("setup_identity.py", "Identity (Cognito User Pool)"),
    ("setup_gateway.py", "Gateway (Lambda targets)"),
    ("setup_policy.py", "Policy (Cedar rules)"),
    ("setup_interceptor.py", "Interceptors (Request + Response)"),
    ("setup_harness.py", "Harness (Cost-controlled deployment)"),
    ("setup_budgets.py", "Budgets (DynamoDB counters + alarms)"),
]


def main():
    parser = argparse.ArgumentParser(description="Deploy full AgentCore stack")
    parser.add_argument("--region", default="us-west-2")
    parser.add_argument("--skip", nargs="*", default=[], help="Scripts to skip (e.g., identity gateway)")
    args = parser.parse_args()

    print("\n" + "═" * 60)
    print("  Manufacturing Insights — AgentCore Full Deployment")
    print("═" * 60)
    print(f"  Region: {args.region}")
    print(f"  Steps:  {len(SCRIPTS) - len(args.skip)}")
    print("═" * 60 + "\n")

    for i, (script, description) in enumerate(SCRIPTS, 1):
        short_name = script.replace("setup_", "").replace(".py", "")
        if short_name in args.skip:
            print(f"  [{i}/{len(SCRIPTS)}] SKIP: {description}")
            continue

        print(f"\n  [{i}/{len(SCRIPTS)}] {description}")
        print("  " + "─" * 50)

        script_path = SCRIPT_DIR / script
        if not script_path.exists():
            print(f"  ⚠️  Script not found: {script_path}")
            continue

        result = subprocess.run(
            [sys.executable, str(script_path), "--region", args.region],
            capture_output=False,
        )

        if result.returncode != 0:
            print(f"\n  ❌ FAILED: {script}")
            print(f"     Fix the issue and re-run with: --skip {' '.join(s.replace('setup_', '').replace('.py', '') for s, _ in SCRIPTS[:i-1])}")
            sys.exit(1)

    print("\n" + "═" * 60)
    print("  ✅ Full AgentCore Deployment Complete!")
    print("═" * 60)
    print("\n  To test: python deploy/agentcore/test_agentcore.py --region", args.region)
    print("  To clean up: python deploy/agentcore/cleanup.py --region", args.region)
    print()


if __name__ == "__main__":
    main()
