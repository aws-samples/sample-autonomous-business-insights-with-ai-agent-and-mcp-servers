# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Memory management for session and cross-session context.

In production, AgentCore Memory provides:
- Short-term memory: Turn-by-turn context within a single session
- Long-term memory: Persisted insights across sessions (user-scoped,
  team-scoped, organization-scoped)

Memory retrieval always passes through Policy: even if an insight exists in
long-term memory, it will not be surfaced to a user who does not have access
to the underlying data.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """A single memory entry with metadata."""

    content: str
    timestamp: str
    scope: str  # "user", "team", "organization"
    tags: list[str] = field(default_factory=list)


@dataclass
class SessionMemory:
    """Short-term memory for a single user session.

    Captures turn-by-turn context so follow-up questions are understood
    without repeating context. Scoped to the session and isolated within
    the user's microVM in AgentCore Runtime.
    """

    user_id: str
    session_id: str
    entries: list[dict[str, Any]] = field(default_factory=list)
    preferences: dict[str, Any] = field(default_factory=dict)

    def add_interaction(self, query: str, response_summary: str) -> None:
        """Record a query-response pair in session memory."""
        self.entries.append({
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "response_summary": response_summary,
        })

    def get_recent_context(self, n: int = 3) -> list[dict[str, Any]]:
        """Retrieve the N most recent interactions for context."""
        return self.entries[-n:] if self.entries else []


class MemoryManager:
    """Manages both short-term and long-term memory.

    In production, AgentCore Memory automatically extracts and stores
    preferences, recurring query patterns, and session summaries.
    Memory is organized into namespaces: user-scoped, team-scoped,
    and organization-scoped.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionMemory] = {}
        self._long_term: dict[str, list[MemoryEntry]] = {}
        self._initialize_demo_memory()

    def _initialize_demo_memory(self) -> None:
        """Pre-populate long-term memory for demo scenarios."""
        # Sarah's preferences (from repeated usage patterns)
        self._long_term["sarah.chen"] = [
            MemoryEntry(
                content="User prefers severity-ranked output with root-cause context",
                timestamp="2026-05-28T08:00:00",
                scope="user",
                tags=["preference", "output_format"],
            ),
            MemoryEntry(
                content="Frequently queries assembly line status before Monday 10 AM reviews",
                timestamp="2026-05-28T08:00:00",
                scope="user",
                tags=["pattern", "recurring"],
            ),
        ]

        # Priya's history with Machine 42
        self._long_term["priya.nair"] = [
            MemoryEntry(
                content=(
                    "Last week's vibration reading on Machine 42: 3.8 mm/s "
                    "(elevated but within warning threshold of 4.0 mm/s). "
                    "Technician noted slight increase from baseline 2.5 mm/s."
                ),
                timestamp="2026-05-26T14:30:00",
                scope="user",
                tags=["machine_42", "vibration", "baseline"],
            ),
        ]

        # Team-scoped memory for maintenance team
        self._long_term["team:maintenance"] = [
            MemoryEntry(
                content=(
                    "Standard anomaly thresholds - Temperature: warning at 72°C, "
                    "critical at 80°C. Vibration: warning at 4.0 mm/s, critical at 6.0 mm/s."
                ),
                timestamp="2026-01-15T09:00:00",
                scope="team",
                tags=["thresholds", "standard"],
            ),
        ]

    def get_or_create_session(self, user_id: str, session_id: str) -> SessionMemory:
        """Get existing session or create a new one."""
        key = f"{user_id}:{session_id}"
        if key not in self._sessions:
            self._sessions[key] = SessionMemory(user_id=user_id, session_id=session_id)
            logger.info("Created new session memory for user '%s'", user_id)
        return self._sessions[key]

    def get_long_term_context(self, user_id: str, tags: list[str] | None = None) -> list[MemoryEntry]:
        """Retrieve relevant long-term memory entries for a user.

        Includes user-scoped and team-scoped memories accessible to the user.
        """
        entries = []

        # User-scoped memories
        user_memories = self._long_term.get(user_id, [])
        if tags:
            entries.extend(m for m in user_memories if any(t in m.tags for t in tags))
        else:
            entries.extend(user_memories)

        # Team-scoped memories (simplified - in production this uses namespace rules)
        team_memories = self._long_term.get("team:maintenance", [])
        entries.extend(team_memories)

        return entries

    def get_user_preferences(self, user_id: str) -> dict[str, str]:
        """Extract user preferences from long-term memory."""
        preferences = {}
        user_memories = self._long_term.get(user_id, [])
        for memory in user_memories:
            if "preference" in memory.tags:
                preferences["output_format"] = memory.content
        return preferences
