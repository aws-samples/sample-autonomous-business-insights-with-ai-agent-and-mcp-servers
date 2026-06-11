# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Tests for the Cedar-style policy engine."""

from src.identity.models import PRIYA_NAIR, RAJ_PATEL, SARAH_CHEN
from src.identity.policy import PolicyEngine


class TestPolicyEngine:
    """Test suite for policy enforcement logic."""

    def setup_method(self):
        self.engine = PolicyEngine()

    def test_plant_manager_has_full_access(self):
        """Plant managers should have unrestricted access to all resources."""
        decision = self.engine.evaluate(
            SARAH_CHEN,
            "get_equipment_status",
            {"line": "Line 4", "plant": "Plant 1"},
        )
        assert decision.allowed is True

    def test_plant_manager_access_any_line(self):
        """Plant managers can access any line across all plants."""
        for line_num in range(1, 13):
            decision = self.engine.evaluate(
                SARAH_CHEN,
                "detect_anomaly",
                {"line": f"Line {line_num}"},
            )
            assert decision.allowed is True

    def test_line_supervisor_scoped_to_assigned_line(self):
        """Line supervisors can only access their assigned lines."""
        # Raj is assigned to Line 7
        decision = self.engine.evaluate(
            RAJ_PATEL,
            "get_equipment_status",
            {"line": "Line 7"},
        )
        assert decision.allowed is True

    def test_line_supervisor_denied_other_lines(self):
        """Line supervisors cannot access lines outside their scope."""
        decision = self.engine.evaluate(
            RAJ_PATEL,
            "get_equipment_status",
            {"line": "Line 4"},
        )
        assert decision.allowed is False
        assert "Access denied" in decision.reason

    def test_technician_scoped_to_assigned_equipment(self):
        """Technicians can access their assigned machines."""
        # Priya is assigned to Machine 41-45
        decision = self.engine.evaluate(
            PRIYA_NAIR,
            "get_sensor_readings",
            {"machine_id": 42},
        )
        assert decision.allowed is True

    def test_technician_denied_unassigned_equipment(self):
        """Technicians cannot access machines outside their assignment."""
        decision = self.engine.evaluate(
            PRIYA_NAIR,
            "get_sensor_readings",
            {"machine_id": 72},
        )
        assert decision.allowed is False
        assert "not assigned" in decision.reason

    def test_line_supervisor_denied_other_plant(self):
        """Line supervisors cannot access resources in other plants."""
        decision = self.engine.evaluate(
            RAJ_PATEL,
            "get_equipment_status",
            {"plant": "Plant 1"},
        )
        assert decision.allowed is False

    def test_no_scope_parameters_allowed(self):
        """Queries without scope parameters are allowed for non-managers."""
        decision = self.engine.evaluate(
            RAJ_PATEL,
            "check_parts_inventory",
            {"part_id": "bearing_6205"},
        )
        assert decision.allowed is True
