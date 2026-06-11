# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""AgentCore Gateway Hook — policy enforcement on every tool call.

In production, the AgentCore Gateway intercepts every agent-to-tool call
before execution. This hook simulates that behavior using Strands Agents'
BeforeToolCallEvent hook mechanism.

When a tool call is made:
1. The hook extracts parameters from the tool input
2. Evaluates the user's identity against Cedar-style policies
3. If denied → cancels the tool call with an access-denied message
4. If allowed → the call proceeds to the MCP server

This is the "Gateway enforces policy before MCP server is ever called" pattern
described in the blog. The MCP server never sees unauthorized requests.
"""

import logging
from typing import Any

from strands.hooks import BeforeToolCallEvent, HookProvider, HookRegistry

from src.identity.models import UserIdentity
from src.identity.policy import PolicyDecision, PolicyEngine

logger = logging.getLogger(__name__)


class GatewayPolicyHook(HookProvider):
    """Strands Agent hook that enforces access policies before every tool call.

    This replicates AgentCore Gateway behavior:
    - Every tool call flows through the Gateway
    - Policy is evaluated against the user's identity and the tool parameters
    - Denied calls are blocked BEFORE reaching the MCP server
    - Every decision is logged (in production: to AWS CloudTrail)

    Usage:
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
        """Evaluate policy before each tool call. Cancel if denied.

        This is the Gateway intercepting the call. If the user doesn't have
        access, the tool call is cancelled with an access-denied message and
        the MCP server is never contacted.
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
            # Block the tool call — MCP server never sees it
            logger.warning(
                "GATEWAY DENY: user='%s' tool='%s' params=%s reason='%s'",
                self.user.name,
                tool_name,
                parameters,
                decision.reason,
            )
            event.cancel_tool = (
                f"[Policy Enforcement] {decision.reason} "
                f"Please only query data within your authorized scope."
            )
        else:
            logger.info(
                "GATEWAY ALLOW: user='%s' tool='%s' params=%s",
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
