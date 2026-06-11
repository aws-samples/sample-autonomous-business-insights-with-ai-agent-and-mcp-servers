# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""User identity models representing enterprise authentication context.

In production, identity would be propagated from your IdP (Okta, AWS IAM,
Amazon Cognito) through AgentCore Identity. This module simulates that
identity context for demonstration purposes.
"""

from dataclasses import dataclass, field
from enum import Enum


class UserRole(str, Enum):
    """Enterprise roles for manufacturing operations."""

    PLANT_MANAGER = "plant_manager"
    LINE_SUPERVISOR = "line_supervisor"
    MAINTENANCE_TECHNICIAN = "maintenance_technician"


@dataclass(frozen=True)
class UserIdentity:
    """Represents an authenticated user's identity and access scope.

    In AgentCore, this context is captured at authentication time and propagated
    through the entire call chain via the Mcp-Session-Id header.
    """

    user_id: str
    name: str
    role: UserRole
    plant_scope: list[str] = field(default_factory=list)
    line_scope: list[str] = field(default_factory=list)
    equipment_scope: list[str] = field(default_factory=list)

    @property
    def has_full_access(self) -> bool:
        """Plant managers have unrestricted access."""
        return self.role == UserRole.PLANT_MANAGER


# Pre-defined users from the blog narrative
SARAH_CHEN = UserIdentity(
    user_id="sarah.chen",
    name="Sarah Chen",
    role=UserRole.PLANT_MANAGER,
    plant_scope=["Plant 1", "Plant 2", "Plant 3"],
    line_scope=[f"Line {i}" for i in range(1, 13)],
    equipment_scope=[],  # Full access - no restrictions
)

RAJ_PATEL = UserIdentity(
    user_id="raj.patel",
    name="Raj Patel",
    role=UserRole.LINE_SUPERVISOR,
    plant_scope=["Plant 2"],
    line_scope=["Line 7"],
    equipment_scope=[f"Machine {70 + i}" for i in range(1, 6)],
)

PRIYA_NAIR = UserIdentity(
    user_id="priya.nair",
    name="Priya Nair",
    role=UserRole.MAINTENANCE_TECHNICIAN,
    plant_scope=["Plant 1"],
    line_scope=["Line 4"],
    equipment_scope=["Machine 41", "Machine 42", "Machine 43", "Machine 44", "Machine 45"],
)

# Lookup for demo user selection
DEMO_USERS = {
    "sarah": SARAH_CHEN,
    "raj": RAJ_PATEL,
    "priya": PRIYA_NAIR,
}
