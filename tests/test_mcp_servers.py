# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Tests for MCP server tool implementations.

These tests validate the tool logic directly without requiring the MCP
transport layer, ensuring data retrieval and processing work correctly.
"""

import json

from src.servers.equipment_server import (
    get_equipment_status,
    get_maintenance_history,
    get_shared_infrastructure,
)
from src.servers.iot_telemetry_server import detect_anomaly, get_sensor_readings
from src.servers.supply_chain_server import check_parts_inventory, get_supplier_lead_times
from src.servers.analytics_server import get_oee_trends, get_quality_metrics


class TestEquipmentServer:
    """Tests for the Equipment MCP server tools."""

    def test_get_equipment_status_all_lines(self):
        """Should return summary of all 12 assembly lines."""
        result = json.loads(get_equipment_status())
        assert len(result) == 12

    def test_get_equipment_status_by_line(self):
        """Should return machines for a specific line."""
        result = json.loads(get_equipment_status(line="Line 4"))
        assert len(result) > 0
        assert all(r["line"] == "Line 4" for r in result)

    def test_get_equipment_status_by_machine_id(self):
        """Should return specific machine details."""
        result = json.loads(get_equipment_status(machine_id=42))
        assert len(result) == 1
        assert result[0]["machine"] == "Machine 42"
        assert result[0]["type"] == "Conveyor Motor"

    def test_get_maintenance_history(self):
        """Should return maintenance records for Machine 42."""
        result = json.loads(get_maintenance_history(machine_id=42))
        assert result["machine"] == "Machine 42"
        assert result["total_records"] > 0
        assert "Bearing replacement" in result["maintenance_records"][0]["description"]

    def test_get_shared_infrastructure(self):
        """Should identify shared infrastructure between lines."""
        result = json.loads(get_shared_infrastructure(line="Line 4"))
        assert "coolant_loop_A" in result
        assert "Line 9" in result["coolant_loop_A"]["serves"]


class TestIoTTelemetryServer:
    """Tests for the IoT Telemetry MCP server tools."""

    def test_get_sensor_readings_temperature(self):
        """Should return temperature readings with trend analysis."""
        result = json.loads(get_sensor_readings(machine_id=42, metric="temperature"))
        assert result["machine_id"] == 42
        assert result["metric"] == "temperature"
        assert result["total_readings"] > 0
        assert result["unit"] == "°C"

    def test_get_sensor_readings_vibration(self):
        """Should return vibration readings."""
        result = json.loads(get_sensor_readings(machine_id=42, metric="vibration"))
        assert result["metric"] == "vibration"
        assert result["unit"] == "mm/s"

    def test_detect_anomaly_specific_line(self):
        """Should detect anomalies on a specific line."""
        result = json.loads(detect_anomaly(line="Line 4"))
        assert "anomalies_found" in result
        assert isinstance(result["anomalies"], list)

    def test_detect_anomaly_returns_severity(self):
        """Anomalies should include severity ranking."""
        result = json.loads(detect_anomaly())
        if result["anomalies"]:
            anomaly = result["anomalies"][0]
            assert anomaly["severity"] in ("WARNING", "CRITICAL")
            assert "machine" in anomaly
            assert "metric" in anomaly


class TestSupplyChainServer:
    """Tests for the Supply Chain MCP server tools."""

    def test_check_parts_inventory_all(self):
        """Should return all inventory items with status."""
        result = json.loads(check_parts_inventory())
        assert result["total_items"] > 0
        for item in result["inventory_items"]:
            assert item["stock_status"] in ("ADEQUATE", "LOW", "CRITICAL", "OUT_OF_STOCK")

    def test_check_parts_inventory_by_machine(self):
        """Should return parts applicable to a specific machine."""
        result = json.loads(check_parts_inventory(machine_id=42))
        assert result["total_items"] > 0

    def test_get_supplier_lead_times(self):
        """Should return supplier details with lead time options."""
        result = json.loads(get_supplier_lead_times(part_id="bearing_6205"))
        assert result["primary_supplier"] == "SKF Industrial"
        assert result["standard_lead_time_days"] == 14
        assert "expedited_lead_time_days" in result

    def test_get_supplier_lead_times_not_found(self):
        """Should return error for unknown parts."""
        result = json.loads(get_supplier_lead_times(part_id="nonexistent_part"))
        assert "error" in result


class TestAnalyticsServer:
    """Tests for the Analytics MCP server tools."""

    def test_get_oee_trends_all_lines(self):
        """Should return OEE trends for all lines."""
        result = json.loads(get_oee_trends())
        assert result["lines_analyzed"] == 12
        assert "trends" in result

    def test_get_oee_trends_line_4_declining(self):
        """Line 4 should show declining availability."""
        result = json.loads(get_oee_trends(line="Line 4"))
        line_4 = result["trends"].get("Line 4", {})
        assert line_4["availability_change_4w"] < 0
        assert line_4["needs_attention"] is True

    def test_get_quality_metrics(self):
        """Should return quality metrics with alert flags."""
        result = json.loads(get_quality_metrics())
        assert result["lines_analyzed"] > 0
        # Line 4 should have a quality alert (scrap rate jumped)
        line_4 = result["metrics"].get("Line 4", {})
        assert line_4["quality_alert"] is True

    def test_get_quality_metrics_by_plant(self):
        """Should filter quality metrics by plant."""
        result = json.loads(get_quality_metrics(plant="Plant 1"))
        assert result["lines_analyzed"] > 0
        assert result["lines_analyzed"] <= 4  # Plant 1 has Lines 1-4
