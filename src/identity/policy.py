# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Cedar-style policy enforcement for tool access control.

In production, AgentCore Policy uses the Cedar authorization language to define
fine-grained access rules. Policies are evaluated at the Gateway level,
intercepting every agent-to-tool call before execution. This module simulates
that behavior for demonstration purposes.

Policy rules can be authored in natural language, and AgentCore generates the
Cedar logic. Automated reasoning validates generated policies for completeness.
"""

import logging
from dataclasses import dataclass
from typing import Any

from src.identity.models import UserIdentity, UserRole

logger = logging.getLogger(__name__)


@dataclass
class PolicyDecision:
    """Result of a policy evaluation."""

    allowed: bool
    reason: str


class PolicyEngine:
    """Evaluates access policies against user identity and tool call parameters.

    In AgentCore, this enforcement happens at the Gateway level, which means it
    intercepts every agent-to-tool call before execution. Every decision is
    logged to AWS CloudTrail, creating a full audit trail.
    """

    def evaluate(
        self, user: UserIdentity, tool_name: str, parameters: dict[str, Any]
    ) -> PolicyDecision:
        """Evaluate whether a user is authorized to call a tool with given parameters.

        Args:
            user: The authenticated user's identity context.
            tool_name: The MCP tool being invoked.
            parameters: The input parameters for the tool call.

        Returns:
            PolicyDecision indicating allow/deny with reason.
        """
        # Plant managers have unrestricted access
        if user.has_full_access:
            return PolicyDecision(
                allowed=True,
                reason=f"Role '{user.role.value}' has full access.",
            )

        # Evaluate line-scoped tools
        if "line" in parameters or "line_id" in parameters:
            requested_line = parameters.get("line") or parameters.get("line_id", "")
            if requested_line and requested_line not in user.line_scope:
                logger.warning(
                    "Policy DENY: User '%s' (role=%s) attempted to access '%s' "
                    "which is outside their scope %s",
                    user.name,
                    user.role.value,
                    requested_line,
                    user.line_scope,
                )
                return PolicyDecision(
                    allowed=False,
                    reason=(
                        f"Access denied. User '{user.name}' with role "
                        f"'{user.role.value}' is not authorized to access "
                        f"'{requested_line}'. Authorized scope: {user.line_scope}"
                    ),
                )

        # Evaluate equipment-scoped tools
        if "machine_id" in parameters:
            machine_id = parameters["machine_id"]
            machine_name = f"Machine {machine_id}"

            if user.role == UserRole.MAINTENANCE_TECHNICIAN:
                if machine_name not in user.equipment_scope:
                    logger.warning(
                        "Policy DENY: Technician '%s' attempted to access '%s' "
                        "which is outside their assignment %s",
                        user.name,
                        machine_name,
                        user.equipment_scope,
                    )
                    return PolicyDecision(
                        allowed=False,
                        reason=(
                            f"Access denied. Technician '{user.name}' is not "
                            f"assigned to '{machine_name}'. Assigned equipment: "
                            f"{user.equipment_scope}"
                        ),
                    )

        # Evaluate plant-scoped access
        if "plant" in parameters:
            requested_plant = parameters["plant"]
            if requested_plant not in user.plant_scope:
                return PolicyDecision(
                    allowed=False,
                    reason=(
                        f"Access denied. User '{user.name}' is not authorized "
                        f"for '{requested_plant}'. Authorized plants: {user.plant_scope}"
                    ),
                )

        # Evaluate budget limits (cost governance)
        if "_budget_context" in parameters:
            budget = parameters["_budget_context"]
            daily_count = budget.get("daily_token_count", 0)
            daily_limit = budget.get("daily_token_limit", 999999)
            if daily_count >= daily_limit:
                logger.warning(
                    "Policy DENY: User '%s' budget exceeded (%d/%d tokens)",
                    user.name, daily_count, daily_limit,
                )
                return PolicyDecision(
                    allowed=False,
                    reason=(
                        f"Daily token budget exceeded for '{user.name}'. "
                        f"Used: {daily_count:,} / Limit: {daily_limit:,} tokens. "
                        f"Budget resets at midnight UTC."
                    ),
                )

        return PolicyDecision(
            allowed=True,
            reason=f"Access granted for user '{user.name}' (role={user.role.value}).",
        )
