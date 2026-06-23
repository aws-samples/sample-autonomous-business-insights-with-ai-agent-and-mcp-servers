# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""SIMULATION FALLBACK — Local approximation of Gateway policy enforcement.

⚠️  THIS IS NOT THE DEFAULT ARCHITECTURE. It is only active when SIMULATION_MODE=true.

Default (Production) Architecture — AgentCore Gateway:
  Agent → Gateway → REQUEST Interceptor (JWT extraction)
                  → Cedar Policy Engine (ENFORCE mode)
                  → Lambda Tool Target (only if PERMIT)

  The Gateway itself evaluates Cedar policies and blocks unauthorized requests
  BEFORE the MCP server (Lambda target) is ever invoked. See:
    - deploy/agentcore/setup_policy.py — deploys Cedar policies to the Gateway
    - deploy/agentcore/cedar_policies/*.cedar — actual Cedar policy definitions
    - deploy/agentcore/lambda_functions/request_interceptor.py — JWT → user_context

  When running in default mode (SIMULATION_MODE=false or unset), the agent
  connects directly to the Gateway and this module is NOT used.

Simulation Fallback (SIMULATION_MODE=true):
  This module provides a LOCAL SIMULATION of Gateway behavior for development
  when you don't have a deployed AgentCore Gateway. It uses Strands Agents'
  BeforeToolCallEvent hook to approximate what the Gateway does server-side.

  Use cases:
    - Local development without AWS infrastructure
    - Demonstrating the policy enforcement concept offline
    - Testing policy logic before deploying Cedar rules

  To activate: set SIMULATION_MODE=true in your environment or .env file.
"""

import logging
from typing import Any

from strands.hooks import BeforeToolCallEvent, HookProvider, HookRegistry

from src.identity.models import UserIdentity
from src.identity.policy import PolicyDecision, PolicyEngine

logger = logging.getLogger(__name__)


class GatewayPolicyHook(HookProvider):
    """SIMULATION FALLBACK — Local approximation of AgentCore Gateway policy enforcement.

    ⚠️  This hook is ONLY active when SIMULATION_MODE=true.
    In the default mode, the AgentCore Gateway evaluates Cedar policies
    server-side and this class is never instantiated.

    What the real Gateway does (server-side, default):
    - REQUEST Interceptor Lambda extracts JWT claims into user_context
    - Cedar Policy Engine evaluates forbid/permit rules against user_context
    - Denied requests return an error without invoking the Lambda target
    - Every decision is logged to AWS CloudTrail

    What this hook simulates (agent-side, SIMULATION_MODE=true only):
    - Extracts parameters from tool input
    - Evaluates against a local PolicyEngine (Python approximation of Cedar)
    - Cancels denied tool calls via BeforeToolCallEvent.cancel_tool

    Usage (simulation mode only):
        gateway_hook = GatewayPolicyHook(user=current_user, policy_engine=engine)
        agent = Agent(system_prompt=..., tools=..., hooks=[gateway_hook])
    """

    def __init__(self, user: UserIdentity, policy_engine: PolicyEngine) -> None:
        self.user = user
        self.policy_engine = policy_engine

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        """Register the policy enforcement callback on BeforeToolCallEvent."""
        registry.add_callback(BeforeToolCallEvent, self._enforce_policy)

    def _enforce_policy(self, event: BeforeToolCallEvent) -> None:
        """Evaluate policy before each tool call (SIMULATION FALLBACK ONLY).

        In the default mode, this logic lives in the AgentCore Gateway:
        - REQUEST Interceptor extracts JWT → user_context
        - Cedar Policy Engine evaluates context.input.* against forbid rules
        - Gateway blocks denied requests before Lambda target invocation

        This simulation approximates that flow using Python policy logic.
        Active only when SIMULATION_MODE=true.
        """
        tool_name = event.tool_use["name"]
        tool_input = event.tool_use.get("input", {})

        # Extract parameters for policy evaluation
        parameters = self._extract_policy_params(tool_input)

        # Evaluate policy
        decision: PolicyDecision = self.policy_engine.evaluate(
            user=self.user,
            tool_name=tool_name,
            parameters=parameters,
        )

        if not decision.allowed:
            # Block the tool call locally (simulates Gateway deny)
            logger.warning(
                "SIMULATION POLICY DENY: user='%s' tool='%s' params=%s reason='%s'",
                self.user.name,
                tool_name,
                parameters,
                decision.reason,
            )
            event.cancel_tool = (
                f"[Policy Enforcement - Simulation] {decision.reason} "
                f"Please only query data within your authorized scope."
            )
        else:
            logger.info(
                "SIMULATION POLICY ALLOW: user='%s' tool='%s' params=%s",
                self.user.name,
                tool_name,
                parameters,
            )

    def _extract_policy_params(self, tool_input: Any) -> dict[str, Any]:
        """Extract policy-relevant parameters from tool input.

        Maps tool input fields to the dimensions the policy engine evaluates:
        line, machine_id, plant.
        """
        if not isinstance(tool_input, dict):
            return {}

        params = {}
        if "line" in tool_input and tool_input["line"]:
            params["line"] = tool_input["line"]
        if "line_id" in tool_input and tool_input["line_id"]:
            params["line_id"] = tool_input["line_id"]
        if "machine_id" in tool_input and tool_input["machine_id"] is not None:
            params["machine_id"] = tool_input["machine_id"]
        if "plant" in tool_input and tool_input["plant"]:
            params["plant"] = tool_input["plant"]

        return params
