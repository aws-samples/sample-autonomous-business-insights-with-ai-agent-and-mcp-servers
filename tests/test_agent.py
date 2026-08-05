# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Tests for the Manufacturing Insights Agent.

Tests validate:
- System prompt construction with identity, scope, memory
- Memory manager (session + long-term)
- Agent configuration (pre-built vs custom MCP client selection)
- Data provider routing (simulated vs live)

No live AWS services or MCP server connections required.
"""

import os
from unittest.mock import patch

from src.config import AppConfig
from src.identity.models import PRIYA_NAIR, RAJ_PATEL, SARAH_CHEN
from src.memory.manager import MemoryManager
from src.agent.prompts import build_agent_prompt
from src.agent.agent import ManufacturingInsightsAgent


class TestAgentPrompts:
    """Tests for system prompt construction."""

    def test_plant_manager_prompt_has_full_access(self):
        """Plant manager prompt should indicate full access scope."""
        prompt = build_agent_prompt(
            user_name="Sarah Chen",
            user_role="Plant Manager",
            user_scope="Full access - all plants, all assembly lines",
        )
        assert "Sarah Chen" in prompt
        assert "Plant Manager" in prompt
        assert "Full access" in prompt

    def test_line_supervisor_prompt_has_limited_scope(self):
        """Line supervisor prompt should reflect limited line scope."""
        prompt = build_agent_prompt(
            user_name="Raj Patel",
            user_role="Line Supervisor",
            user_scope="Plants: ['Plant 2'], Lines: ['Line 7']",
        )
        assert "Line 7" in prompt
        assert "Line Supervisor" in prompt

    def test_prompt_includes_memory_context(self):
        """Prompt should include relevant memory context."""
        prompt = build_agent_prompt(
            user_name="Priya Nair",
            user_role="Maintenance Technician",
            user_scope="Equipment: ['Machine 41', 'Machine 42']",
            memory_context="Last week's vibration on Machine 42: 3.8 mm/s",
        )
        assert "3.8 mm/s" in prompt

    def test_prompt_includes_preferences(self):
        """Prompt should include user preferences from memory."""
        prompt = build_agent_prompt(
            user_name="Sarah Chen",
            user_role="Plant Manager",
            user_scope="Full access",
            user_preferences="Prefers severity-ranked output",
        )
        assert "severity-ranked" in prompt

    def test_prompt_instructs_semantic_layer_first(self):
        """Prompt should instruct agent to call discover_data_sources first."""
        prompt = build_agent_prompt(
            user_name="Sarah Chen",
            user_role="Plant Manager",
            user_scope="Full access",
        )
        assert "discover_data_sources" in prompt

    def test_prompt_includes_access_control_section(self):
        """Prompt should have access control instructions."""
        prompt = build_agent_prompt(
            user_name="Raj Patel",
            user_role="Line Supervisor",
            user_scope="Lines: ['Line 7']",
        )
        assert "Access Control" in prompt
        assert "authorized scope" in prompt.lower()


class TestMemoryManager:
    """Tests for memory management functionality."""

    def test_session_creation(self):
        """Should create and retrieve session memory."""
        manager = MemoryManager()
        session = manager.get_or_create_session("sarah.chen", "session-1")
        assert session.user_id == "sarah.chen"
        assert session.entries == []

    def test_session_reuse(self):
        """Should reuse existing session for same user+session pair."""
        manager = MemoryManager()
        session1 = manager.get_or_create_session("sarah.chen", "session-1")
        session1.add_interaction("test query", "test response")

        session2 = manager.get_or_create_session("sarah.chen", "session-1")
        assert len(session2.entries) == 1

    def test_separate_sessions_isolated(self):
        """Different sessions should not share data."""
        manager = MemoryManager()
        session1 = manager.get_or_create_session("sarah.chen", "session-1")
        session1.add_interaction("query A", "response A")

        session2 = manager.get_or_create_session("sarah.chen", "session-2")
        assert len(session2.entries) == 0

    def test_long_term_memory_retrieval(self):
        """Should retrieve pre-populated long-term memory."""
        manager = MemoryManager()
        entries = manager.get_long_term_context("priya.nair")
        assert len(entries) > 0
        assert any("Machine 42" in e.content for e in entries)

    def test_long_term_memory_includes_team_scope(self):
        """Should include team-scoped memory (anomaly thresholds)."""
        manager = MemoryManager()
        entries = manager.get_long_term_context("priya.nair")
        assert any("threshold" in e.content.lower() for e in entries)

    def test_user_preferences_extraction(self):
        """Should extract user preferences from long-term memory."""
        manager = MemoryManager()
        prefs = manager.get_user_preferences("sarah.chen")
        assert "severity-ranked" in prefs.get("output_format", "")

    def test_user_with_no_preferences(self):
        """Unknown user should return empty preferences."""
        manager = MemoryManager()
        prefs = manager.get_user_preferences("unknown.user")
        assert prefs == {}

    def test_session_context_retrieval(self):
        """Should return recent interactions for context."""
        manager = MemoryManager()
        session = manager.get_or_create_session("test.user", "session-1")
        session.add_interaction("Query 1", "Response 1")
        session.add_interaction("Query 2", "Response 2")
        session.add_interaction("Query 3", "Response 3")
        session.add_interaction("Query 4", "Response 4")

        recent = session.get_recent_context(n=2)
        assert len(recent) == 2
        assert recent[0]["query"] == "Query 3"
        assert recent[1]["query"] == "Query 4"

    def test_store_episodic_memory(self):
        """Should store a new episodic memory entry."""
        manager = MemoryManager()
        entry = manager.store(
            user_id="priya.nair",
            key="vibration_flagged",
            value="Machine 42 vibration at 4.5 mm/s — flagged for review",
            memory_type="episodic",
            namespace="user",
            tags=["machine_42", "vibration"],
            source_tool="get_sensor_readings",
            source_params={"machine_id": 42, "metric": "vibration"},
            user_action="flagged_for_review",
        )
        assert entry.memory_type == "episodic"
        assert entry.source_tool == "get_sensor_readings"
        assert entry.user_action == "flagged_for_review"

    def test_recall_by_memory_type(self):
        """Should filter recall results by memory_type."""
        manager = MemoryManager()
        # Priya has both long_term and episodic entries
        episodic = manager.recall("priya.nair", memory_types=["episodic"])
        long_term = manager.recall("priya.nair", memory_types=["long_term"])

        assert all(e.memory_type == "episodic" for e in episodic)
        assert all(e.memory_type == "long_term" for e in long_term)
        assert len(episodic) > 0
        assert len(long_term) > 0

    def test_recall_by_query(self):
        """Should filter recall results by keyword query."""
        manager = MemoryManager()
        results = manager.recall("priya.nair", query="vibration")
        assert len(results) > 0
        assert all("vibration" in e.content.lower() for e in results)

    def test_recall_by_tags(self):
        """Should filter recall results by tags."""
        manager = MemoryManager()
        results = manager.recall("priya.nair", tags=["machine_42"])
        assert len(results) > 0
        assert all("machine_42" in e.tags for e in results)

    def test_get_episodic_timeline(self):
        """Should return episodic events in chronological order."""
        manager = MemoryManager()
        timeline = manager.get_episodic_timeline("priya.nair", topic="machine 42")
        assert len(timeline) > 0
        # Verify chronological order (oldest first)
        for i in range(len(timeline) - 1):
            assert timeline[i].timestamp <= timeline[i + 1].timestamp

    def test_get_episodic_timeline_all_are_episodic(self):
        """Timeline should only return episodic entries, not long-term."""
        manager = MemoryManager()
        timeline = manager.get_episodic_timeline("priya.nair")
        assert all(e.memory_type == "episodic" for e in timeline)

    def test_store_then_recall(self):
        """Stored memory should be retrievable via recall."""
        manager = MemoryManager()
        manager.store(
            user_id="raj.patel",
            key="line7_status",
            value="Line 7 OEE at 82% — stable this week",
            memory_type="episodic",
            tags=["line_7", "oee"],
        )
        results = manager.recall("raj.patel", query="Line 7")
        assert any("Line 7" in e.content for e in results)

    def test_team_memory_accessible(self):
        """Team-scoped memory should be accessible to team members."""
        manager = MemoryManager()
        results = manager.recall("priya.nair", tags=["thresholds"])
        assert any("threshold" in e.content.lower() for e in results)

    def test_org_memory_accessible(self):
        """Org-scoped memory should be accessible to all users."""
        manager = MemoryManager()
        results = manager.recall("sarah.chen", tags=["oee", "critical"])
        assert any("80%" in e.content for e in results)

    def test_session_tool_result_caching(self):
        """Session should cache tool results for coreference."""
        manager = MemoryManager()
        session = manager.get_or_create_session("priya.nair", "sess-1")
        session.add_tool_result(
            "get_sensor_readings",
            {"machine_id": 42, "metric": "vibration"},
            "4.5 mm/s",
        )
        assert len(session.tool_results) == 1


class TestAgentConfiguration:
    """Tests for agent MCP client configuration."""

    def test_local_mode_creates_http_clients(self):
        """When USE_PREBUILT_MCP=false, should create HTTP clients for all servers."""
        agent = ManufacturingInsightsAgent(AppConfig())
        with patch.dict(os.environ, {"USE_PREBUILT_MCP": "false"}):
            clients = agent._create_local_clients()
            # 5 servers: semantic + equipment + iot + supply_chain + analytics
            assert len(clients) == 5

    def test_config_has_all_server_urls(self):
        """Config should have URLs for all MCP servers."""
        config = AppConfig()
        assert "8005" in config.mcp_servers.semantic_layer_url
        assert "8001" in config.mcp_servers.equipment_url
        assert "8002" in config.mcp_servers.iot_telemetry_url
        assert "8003" in config.mcp_servers.supply_chain_url
        assert "8004" in config.mcp_servers.analytics_url


class TestDataProvider:
    """Tests for data provider routing between simulated and live."""

    def test_simulated_mode_returns_data(self):
        """In simulated mode, data_provider should return sample data."""
        with patch.dict(os.environ, {"DATA_MODE": "simulated"}):
            # Re-import to pick up env change
            import importlib
            import src.data.data_provider as dp
            importlib.reload(dp)

            result = dp.get_equipment_status(machine_id=42)
            assert "Machine 42" in result
            assert "Conveyor Motor" in result

    def test_simulated_sensor_readings(self):
        """Simulated mode should return sensor readings with trend."""
        with patch.dict(os.environ, {"DATA_MODE": "simulated"}):
            import importlib
            import src.data.data_provider as dp
            importlib.reload(dp)

            result = dp.get_sensor_readings(machine_id=42, metric="vibration", days=7)
            assert "machine_id" in result
            assert "vibration" in result

    def test_simulated_anomaly_detection(self):
        """Simulated mode should detect anomalies."""
        with patch.dict(os.environ, {"DATA_MODE": "simulated"}):
            import importlib
            import src.data.data_provider as dp
            importlib.reload(dp)

            result = dp.detect_anomaly(line="Line 4")
            assert "anomalies_found" in result

    def test_simulated_parts_inventory(self):
        """Simulated mode should return inventory with stock status."""
        with patch.dict(os.environ, {"DATA_MODE": "simulated"}):
            import importlib
            import src.data.data_provider as dp
            importlib.reload(dp)

            result = dp.check_parts_inventory(part_id="bearing_6205")
            assert "bearing_6205" in result
            assert "stock_status" in result

    def test_simulated_oee_trends(self):
        """Simulated mode should show Line 4 declining OEE."""
        with patch.dict(os.environ, {"DATA_MODE": "simulated"}):
            import importlib
            import src.data.data_provider as dp
            importlib.reload(dp)

            result = dp.get_oee_trends(line="Line 4")
            assert "needs_attention" in result
            assert "true" in result.lower() or "True" in result
