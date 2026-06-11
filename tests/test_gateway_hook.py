# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Tests for the Gateway Policy Hook — simulates policy enforcement at the Gateway."""

from unittest.mock import MagicMock

from src.identity.gateway_hook import GatewayPolicyHook
from src.identity.models import PRIYA_NAIR, RAJ_PATEL, SARAH_CHEN
from src.identity.policy import PolicyEngine


class TestGatewayPolicyHook:
    """Test that the Gateway hook correctly blocks/allows tool calls."""

    def setup_method(self):
        self.policy_engine = PolicyEngine()

    def _make_event(self, tool_name: str, tool_input: dict) -> MagicMock:
        """Create a mock BeforeToolCallEvent."""
        event = MagicMock()
        event.tool_use = {"name": tool_name, "input": tool_input}
        event.cancel_tool = None
        return event

    def test_plant_manager_allowed_all_lines(self):
        """Sarah (Plant Manager) should be allowed to access any line."""
        hook = GatewayPolicyHook(user=SARAH_CHEN, policy_engine=self.policy_engine)
        event = self._make_event("detect_anomaly", {"line": "Line 4"})

        hook._enforce_policy(event)

        assert event.cancel_tool is None  # Not cancelled

    def test_supervisor_blocked_from_other_lines(self):
        """Raj (Line Supervisor) should be blocked from accessing Line 4."""
        hook = GatewayPolicyHook(user=RAJ_PATEL, policy_engine=self.policy_engine)
        event = self._make_event("get_equipment_status", {"line": "Line 4"})

        hook._enforce_policy(event)

        assert event.cancel_tool is not None
        assert "Access denied" in event.cancel_tool

    def test_supervisor_allowed_own_line(self):
        """Raj should be allowed to access Line 7."""
        hook = GatewayPolicyHook(user=RAJ_PATEL, policy_engine=self.policy_engine)
        event = self._make_event("get_equipment_status", {"line": "Line 7"})

        hook._enforce_policy(event)

        assert event.cancel_tool is None

    def test_technician_blocked_from_unassigned_machine(self):
        """Priya should be blocked from Machine 72 (not in her assignment)."""
        hook = GatewayPolicyHook(user=PRIYA_NAIR, policy_engine=self.policy_engine)
        event = self._make_event("get_sensor_readings", {"machine_id": 72})

        hook._enforce_policy(event)

        assert event.cancel_tool is not None
        assert "not assigned" in event.cancel_tool

    def test_technician_allowed_assigned_machine(self):
        """Priya should be allowed to access Machine 42 (in her assignment)."""
        hook = GatewayPolicyHook(user=PRIYA_NAIR, policy_engine=self.policy_engine)
        event = self._make_event("get_sensor_readings", {"machine_id": 42})

        hook._enforce_policy(event)

        assert event.cancel_tool is None

    def test_tool_with_no_scope_params_allowed(self):
        """Tools called without scope params should pass policy for all users."""
        hook = GatewayPolicyHook(user=RAJ_PATEL, policy_engine=self.policy_engine)
        event = self._make_event("check_parts_inventory", {"part_id": "bearing_6205"})

        hook._enforce_policy(event)

        assert event.cancel_tool is None

    def test_cancel_message_includes_policy_prefix(self):
        """Denied calls should include [Policy Enforcement] prefix for clarity."""
        hook = GatewayPolicyHook(user=RAJ_PATEL, policy_engine=self.policy_engine)
        event = self._make_event("get_oee_trends", {"line": "Line 1"})

        hook._enforce_policy(event)

        assert event.cancel_tool is not None
        assert "[Policy Enforcement]" in event.cancel_tool
