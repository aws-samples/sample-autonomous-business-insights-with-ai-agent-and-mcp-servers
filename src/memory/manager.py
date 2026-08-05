# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Memory management for session and cross-session context.

In production, AgentCore Memory provides three memory constructs:
- Short-term memory: Turn-by-turn context within a single session
- Long-term memory: Persisted facts (baselines, preferences, thresholds)
- Episodic memory: Timestamped events and past interactions

Memory is organized into namespaces:
- User-scoped: Private to each user (baselines, episodes, preferences)
- Team-scoped: Shared within a team (thresholds, standards)
- Organization-scoped: Shared globally (global policies)

Memory retrieval always passes through Policy: even if an insight exists in
long-term memory, it will not be surfaced to a user who does not have access
to the underlying data.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """A single memory entry with metadata."""

    content: str
    timestamp: str
    scope: str  # "user", "team", "organization"
    memory_type: str = "long_term"  # "long_term", "episodic", "preference"
    tags: list[str] = field(default_factory=list)
    source_tool: str | None = None
    source_params: dict[str, Any] | None = None
    user_action: str | None = None
    ttl_days: int = 90


@dataclass
class SessionMemory:
    """Short-term memory for a single user session.

    Captures turn-by-turn context so follow-up questions are understood
    without repeating context. Scoped to the session and isolated within
    the user's microVM in AgentCore Runtime.

    Lifetime: Destroyed when session ends (microVM shutdown).
    """

    user_id: str
    session_id: str
    entries: list[dict[str, Any]] = field(default_factory=list)
    preferences: dict[str, Any] = field(default_factory=dict)
    tool_results: dict[str, Any] = field(default_factory=dict)

    def add_interaction(self, query: str, response_summary: str) -> None:
        """Record a query-response pair in session memory."""
        self.entries.append({
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "response_summary": response_summary,
        })

    def add_tool_result(self, tool_name: str, params: dict, result: str) -> None:
        """Cache a tool call result for this session (enables coreference)."""
        key = f"{tool_name}:{hash(str(sorted(params.items())))}"
        self.tool_results[key] = {
            "tool": tool_name,
            "params": params,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }

    def get_recent_context(self, n: int = 3) -> list[dict[str, Any]]:
        """Retrieve the N most recent interactions for context."""
        return self.entries[-n:] if self.entries else []

    def get_context_window(self, max_turns: int = 10) -> list[dict[str, Any]]:
        """Return recent turns for the system prompt (coreference resolution)."""
        return self.entries[-max_turns:] if self.entries else []


class MemoryManager:
    """Manages short-term, long-term, and episodic memory.

    Three memory constructs:
    - Short-term (SessionMemory): Within-session context, destroyed on end
    - Long-term: Persistent facts — baselines, preferences, thresholds
    - Episodic: Timestamped events — what happened, when, what was decided

    Three namespaces:
    - User: Private to each user
    - Team: Shared within a team
    - Organization: Global

    In production, AgentCore Memory automatically extracts and stores
    preferences, recurring query patterns, and session summaries.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, SessionMemory] = {}
        self._long_term: dict[str, list[MemoryEntry]] = {}
        self._initialize_demo_memory()

    def _initialize_demo_memory(self) -> None:
        """Pre-populate long-term and episodic memory for demo scenarios."""
        # Sarah's preferences (long-term, user-scoped)
        self._long_term["sarah.chen"] = [
            MemoryEntry(
                content="User prefers severity-ranked output with root-cause context",
                timestamp="2026-05-28T08:00:00",
                scope="user",
                memory_type="preference",
                tags=["preference", "output_format"],
                ttl_days=365,
            ),
            MemoryEntry(
                content="Frequently queries assembly line status before Monday 10 AM reviews",
                timestamp="2026-05-28T08:00:00",
                scope="user",
                memory_type="long_term",
                tags=["pattern", "recurring"],
            ),
            MemoryEntry(
                content="Line 4 OEE was 87% — noted as declining from 94% four weeks prior",
                timestamp="2026-07-15T09:30:00",
                scope="user",
                memory_type="episodic",
                tags=["line_4", "oee", "declining"],
                source_tool="get_oee_trends",
                source_params={"line": "Line 4"},
                user_action="noted_for_review",
            ),
            MemoryEntry(
                content="Identified coolant loop A correlation between Line 4 and Line 9",
                timestamp="2026-07-16T10:15:00",
                scope="user",
                memory_type="episodic",
                tags=["line_4", "line_9", "coolant", "correlation"],
                source_tool="get_shared_infrastructure",
                source_params={"line": "Line 4"},
                user_action="identified_root_cause",
            ),
        ]

        # Priya's history with Machine 42 (episodic + baseline)
        self._long_term["priya.nair"] = [
            MemoryEntry(
                content="Machine 42 vibration baseline: 2.5 mm/s (normal operating range)",
                timestamp="2026-03-01T10:00:00",
                scope="user",
                memory_type="long_term",
                tags=["machine_42", "vibration", "baseline", "normal"],
                source_tool="get_sensor_readings",
                source_params={"machine_id": 42, "metric": "vibration"},
            ),
            MemoryEntry(
                content=(
                    "Vibration reading on Machine 42: 3.8 mm/s — "
                    "elevated but within warning threshold (4.0 mm/s). "
                    "Flagged for monitoring."
                ),
                timestamp="2026-07-02T14:30:00",
                scope="user",
                memory_type="episodic",
                tags=["machine_42", "vibration", "elevated"],
                source_tool="get_sensor_readings",
                source_params={"machine_id": 42, "metric": "vibration"},
                user_action="flagged_for_monitoring",
            ),
            MemoryEntry(
                content="Scheduled bearing inspection for Machine 42 with Priya Nair",
                timestamp="2026-07-09T11:00:00",
                scope="user",
                memory_type="episodic",
                tags=["machine_42", "bearing", "inspection", "scheduled"],
                user_action="scheduled_maintenance",
            ),
            MemoryEntry(
                content=(
                    "Inspection result: Bearing shows early wear pattern. "
                    "Vibration at 4.1 mm/s (crossed warning threshold). "
                    "Recommended replacement within 2 weeks."
                ),
                timestamp="2026-07-16T15:00:00",
                scope="user",
                memory_type="episodic",
                tags=["machine_42", "bearing", "inspection", "wear"],
                source_tool="get_maintenance_history",
                source_params={"machine_id": 42},
                user_action="inspection_completed",
            ),
        ]

        # Team-scoped memory for maintenance team (long-term)
        self._long_term["team:maintenance"] = [
            MemoryEntry(
                content=(
                    "Standard anomaly thresholds - Temperature: warning at 72°C, "
                    "critical at 80°C. Vibration: warning at 4.0 mm/s, critical at 6.0 mm/s."
                ),
                timestamp="2026-01-15T09:00:00",
                scope="team",
                memory_type="long_term",
                tags=["thresholds", "standard"],
                ttl_days=365,
            ),
            MemoryEntry(
                content=(
                    "Bearing replacement SOP: If vibration exceeds 4.0 mm/s for >7 days, "
                    "schedule replacement. If >5.0 mm/s, stop machine immediately."
                ),
                timestamp="2026-02-01T09:00:00",
                scope="team",
                memory_type="long_term",
                tags=["bearing", "sop", "replacement"],
                ttl_days=365,
            ),
        ]

        # Organization-scoped memory (long-term)
        self._long_term["org:global"] = [
            MemoryEntry(
                content="OEE below 80% is classified as critical and requires management escalation",
                timestamp="2026-01-01T00:00:00",
                scope="organization",
                memory_type="long_term",
                tags=["oee", "critical", "threshold", "escalation"],
                ttl_days=365,
            ),
        ]

    def get_or_create_session(self, user_id: str, session_id: str) -> SessionMemory:
        """Get existing session or create a new one."""
        key = f"{user_id}:{session_id}"
        if key not in self._sessions:
            self._sessions[key] = SessionMemory(user_id=user_id, session_id=session_id)
            logger.info("Created new session memory for user '%s'", user_id)
        return self._sessions[key]

    def store(
        self,
        user_id: str,
        key: str,
        value: str,
        memory_type: str = "episodic",
        namespace: str = "user",
        tags: list[str] | None = None,
        source_tool: str | None = None,
        source_params: dict[str, Any] | None = None,
        user_action: str | None = None,
        ttl_days: int = 90,
    ) -> MemoryEntry:
        """Store a new memory entry (long-term or episodic).

        Args:
            user_id: The user storing this memory
            key: Short identifier for the memory
            value: The memory content
            memory_type: "long_term" (persistent fact), "episodic" (timestamped event),
                         or "preference" (user preference)
            namespace: "user" (private), "team", or "organization"
            tags: Searchable tags for retrieval
            source_tool: Which MCP tool generated this data
            source_params: Parameters passed to the tool
            user_action: What the user did (flagged, scheduled, noted)
            ttl_days: Time-to-live in days

        Returns:
            The created MemoryEntry
        """
        entry = MemoryEntry(
            content=value,
            timestamp=datetime.now().isoformat(),
            scope=namespace,
            memory_type=memory_type,
            tags=tags or [key],
            source_tool=source_tool,
            source_params=source_params,
            user_action=user_action,
            ttl_days=ttl_days,
        )

        # Determine storage key
        if namespace == "user":
            storage_key = user_id
        elif namespace == "team":
            storage_key = f"team:{self._get_user_team(user_id)}"
        else:
            storage_key = "org:global"

        if storage_key not in self._long_term:
            self._long_term[storage_key] = []
        self._long_term[storage_key].append(entry)

        logger.info(
            "Stored %s memory for '%s': %s",
            memory_type, user_id, key,
        )
        return entry

    def recall(
        self,
        user_id: str,
        query: str | None = None,
        memory_types: list[str] | None = None,
        tags: list[str] | None = None,
        max_results: int = 5,
    ) -> list[MemoryEntry]:
        """Retrieve relevant memories for a user.

        Searches across user-scoped, team-scoped, and org-scoped memories.
        Filters by memory_type and tags if provided.
        Uses keyword matching (production would use semantic similarity).

        Args:
            user_id: The user requesting memories
            query: Optional search query (keyword match against content)
            memory_types: Filter to specific types ("long_term", "episodic", "preference")
            tags: Filter to entries with matching tags
            max_results: Maximum entries to return

        Returns:
            Matching MemoryEntry list, sorted by timestamp (newest first)
        """
        all_entries = []

        # Gather from all accessible namespaces
        user_memories = self._long_term.get(user_id, [])
        team_key = f"team:{self._get_user_team(user_id)}"
        team_memories = self._long_term.get(team_key, [])
        org_memories = self._long_term.get("org:global", [])

        all_entries.extend(user_memories)
        all_entries.extend(team_memories)
        all_entries.extend(org_memories)

        # Filter by memory_type
        if memory_types:
            all_entries = [e for e in all_entries if e.memory_type in memory_types]

        # Filter by tags
        if tags:
            all_entries = [e for e in all_entries if any(t in e.tags for t in tags)]

        # Filter by query (keyword matching — production uses semantic similarity)
        if query:
            query_lower = query.lower()
            query_terms = query_lower.split()
            all_entries = [
                e for e in all_entries
                if any(term in e.content.lower() for term in query_terms)
            ]

        # Filter expired entries
        all_entries = [e for e in all_entries if not self._is_expired(e)]

        # Sort by timestamp (newest first) and limit
        all_entries.sort(key=lambda e: e.timestamp, reverse=True)
        return all_entries[:max_results]

    def get_episodic_timeline(
        self,
        user_id: str,
        topic: str | None = None,
        days: int = 30,
        max_results: int = 10,
    ) -> list[MemoryEntry]:
        """Get chronological episodic events for a user.

        Returns timestamped events related to a topic, sorted oldest first
        (chronological order for timeline presentation).

        Args:
            user_id: The user
            topic: Optional topic keyword to filter events
            days: Look back this many days
            max_results: Maximum events to return

        Returns:
            Episodic entries in chronological order (oldest first)
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        user_memories = self._long_term.get(user_id, [])

        episodes = [
            e for e in user_memories
            if e.memory_type == "episodic" and e.timestamp >= cutoff
        ]

        # Filter by topic if provided
        if topic:
            topic_lower = topic.lower()
            topic_terms = topic_lower.split()
            episodes = [
                e for e in episodes
                if any(term in e.content.lower() for term in topic_terms)
                or any(term in tag for term in topic_terms for tag in e.tags)
            ]

        # Sort chronologically (oldest first for timeline)
        episodes.sort(key=lambda e: e.timestamp)
        return episodes[:max_results]

    def get_long_term_context(self, user_id: str, tags: list[str] | None = None) -> list[MemoryEntry]:
        """Retrieve relevant long-term memory entries for a user.

        Includes user-scoped, team-scoped, and org-scoped memories.
        Filters out episodic entries (use get_episodic_timeline for those).
        """
        entries = []

        # User-scoped memories (long-term only, not episodic)
        user_memories = self._long_term.get(user_id, [])
        long_term_only = [m for m in user_memories if m.memory_type in ("long_term", "preference")]
        if tags:
            entries.extend(m for m in long_term_only if any(t in m.tags for t in tags))
        else:
            entries.extend(long_term_only)

        # Team-scoped memories
        team_key = f"team:{self._get_user_team(user_id)}"
        team_memories = self._long_term.get(team_key, [])
        entries.extend(team_memories)

        # Org-scoped memories
        org_memories = self._long_term.get("org:global", [])
        entries.extend(org_memories)

        return entries

    def get_user_preferences(self, user_id: str) -> dict[str, str]:
        """Extract user preferences from long-term memory."""
        preferences = {}
        user_memories = self._long_term.get(user_id, [])
        for memory in user_memories:
            if memory.memory_type == "preference" or "preference" in memory.tags:
                preferences["output_format"] = memory.content
        return preferences

    def _get_user_team(self, user_id: str) -> str:
        """Map user to their team namespace (simplified)."""
        team_map = {
            "sarah.chen": "plant_managers",
            "raj.patel": "line_supervisors",
            "priya.nair": "maintenance",
        }
        return team_map.get(user_id, "maintenance")

    def _is_expired(self, entry: MemoryEntry) -> bool:
        """Check if a memory entry has exceeded its TTL."""
        try:
            created = datetime.fromisoformat(entry.timestamp)
            expiry = created + timedelta(days=entry.ttl_days)
            return datetime.now() > expiry
        except (ValueError, TypeError):
            return False
