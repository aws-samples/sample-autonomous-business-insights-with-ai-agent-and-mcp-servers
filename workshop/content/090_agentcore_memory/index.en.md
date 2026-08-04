+++
title = "AgentCore Memory"
weight = 90
+++

# AgentCore Memory — Session & Cross-Session Persistence

In this module, you'll explore how AgentCore Memory enables natural follow-up conversations and personalized responses by persisting context within and across sessions.

## Why Does an Agent Need Memory?

Without memory, every conversation starts from zero:

```
Session 1: "What's Machine 42's vibration?"  → "4.5 mm/s"
Session 2: "Has it gotten worse?"            → "What do you mean by 'it'?"
```

With memory:

```
Session 1: "What's Machine 42's vibration?"  → "4.5 mm/s" [stored: baseline=4.5]
Session 2: "Has it gotten worse?"            → "Yes, up from 3.8 mm/s last week (+18%)"
```

Memory gives the agent conversational continuity and the ability to surface historical context.

## Memory Architecture

AgentCore Memory operates at three levels:

```
┌─────────────────────────────────────────────────────────────┐
│  AgentCore Memory                                            │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Short-Term (Session)                                 │   │
│  │  • Turn-by-turn conversation context                  │   │
│  │  • Tool call results from this session                │   │
│  │  • Lives in microVM memory (destroyed on session end) │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Long-Term (User)                                     │   │
│  │  • Baselines: "Machine 42 vibration: 3.8 mm/s"       │   │
│  │  • Preferences: "Sarah prefers severity-ranked lists" │   │
│  │  • Past insights: "Last week Line 4 OEE was 87%"     │   │
│  │  • Persisted to S3 (survives session end)             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Team/Org (Shared)                                    │   │
│  │  • Thresholds: "Temperature warning at 72°C"         │   │
│  │  • Standards: "OEE below 80% = critical"             │   │
│  │  • Shared by all users in the team/org namespace      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Step 1: Explore the Memory Manager

Open `src/memory/manager.py`:

```python
class SessionMemory:
    """Short-term: tracks conversation context within one session."""

    def __init__(self):
        self.turns: list[dict] = []
        self.tool_results: dict[str, Any] = {}

    def add_turn(self, role: str, content: str):
        self.turns.append({"role": role, "content": content})

    def get_context_window(self, max_turns: int = 10) -> list[dict]:
        """Return recent turns for the system prompt."""
        return self.turns[-max_turns:]


class MemoryManager:
    """Long-term: persists insights across sessions."""

    def __init__(self, user_id: str, storage_path: str = None):
        self.user_id = user_id
        self.memories: list[MemoryEntry] = []

    def store(self, key: str, value: str, metadata: dict = None):
        """Persist a fact for future sessions."""
        self.memories.append(MemoryEntry(
            key=key,
            value=value,
            timestamp=datetime.now(),
            metadata=metadata or {},
        ))

    def recall(self, query: str, max_results: int = 5) -> list[MemoryEntry]:
        """Retrieve relevant memories for a query."""
        # Semantic similarity matching against stored memories
        return self._search(query, max_results)
```

## Step 2: See Memory in Action

Start the CLI as Priya:

```bash
python -m src.main
```

Select **3 (Priya Nair)** and ask:

```
> What's the current vibration reading on Machine 42?
```

The agent calls `get_sensor_readings(machine_id=42, metric="vibration")` and returns the current value (e.g., 4.5 mm/s). This gets stored in short-term memory.

Now ask a follow-up:

```
> Is that normal?
```

The agent uses **session memory** to know "that" = 4.5 mm/s on Machine 42, and recalls the **long-term memory** baseline of 3.8 mm/s from last week's inspection. It responds: "No, it's up 18% from the 3.8 mm/s baseline recorded last week."

## Step 3: Understand How Memory Augments the Prompt

Memory entries are injected into the system prompt before each LLM call:

```python
def build_prompt(user: UserIdentity, memory_manager: MemoryManager, query: str):
    # Recall relevant memories for this query
    relevant_memories = memory_manager.recall(query)

    memory_context = ""
    if relevant_memories:
        memory_context = "Relevant context from previous sessions:\n"
        for mem in relevant_memories:
            memory_context += f"  - [{mem.timestamp}] {mem.key}: {mem.value}\n"

    return SYSTEM_PROMPT.format(
        user_name=user.username,
        user_role=user.role,
        user_scope=user.line_scope,
        memory_context=memory_context,
    )
```

The LLM sees relevant memories as part of its system prompt, allowing it to reference past data points.

## Step 4: Test Cross-Session Persistence

In the Streamlit UI (`streamlit run src/demo_ui.py`), as Priya:

**Session 1:**
```
> Machine 42 vibration seems high. What was it last time?
```

Agent responds with current reading and historical data. The system stores: "Machine 42 vibration: 4.5 mm/s (2026-07-23)"

**Close the browser tab. Open a new tab (new session).**

**Session 2:**
```
> Has Machine 42's vibration gotten worse?
```

The agent retrieves long-term memory from Session 1, plus any stored baselines, and provides a trend comparison — even though this is a brand new session.

## Step 5: Memory and Access Control

Memory respects policy boundaries:

```
┌────────────────────────────────────────────────────────────┐
│  Memory Policy Integration                                  │
│                                                             │
│  User-scoped memory: Only accessible by that user           │
│  • Priya's memories about Machine 42 are ONLY Priya's      │
│  • Raj cannot access Priya's stored baselines              │
│                                                             │
│  Team-scoped memory: Accessible by team members             │
│  • Shared thresholds (e.g., "vibration warning = 4.0")     │
│  • All maintenance_technicians see these                    │
│                                                             │
│  Org-scoped memory: Accessible by all                       │
│  • Global standards (e.g., "OEE critical < 80%")           │
│                                                             │
│  IMPORTANT: Memory derived from denied data is NOT stored   │
│  • If Raj tries to access Line 4 data → DENY               │
│  • No memory entry created for that failed attempt          │
└────────────────────────────────────────────────────────────┘
```

## Step 6: Explore Memory Storage

In production, long-term memory persists to S3:

```
s3://agentcore-memory-bucket/
├── user-memory/
│   ├── sarah.chen/
│   │   ├── 2026-07-22_line4_oee.json
│   │   └── 2026-07-23_anomaly_summary.json
│   ├── raj.patel/
│   │   └── 2026-07-23_line7_status.json
│   └── priya.nair/
│       └── 2026-07-23_machine42_vibration.json
├── team-memory/
│   ├── maintenance_technicians/
│   │   └── thresholds.json
│   └── line_supervisors/
│       └── standards.json
└── org-memory/
    └── global_standards.json
```

Each memory entry:

```json
{
  "key": "machine_42_vibration_baseline",
  "value": "4.5 mm/s",
  "timestamp": "2026-07-23T14:30:00Z",
  "source_tool": "get_sensor_readings",
  "source_params": {"machine_id": 42, "metric": "vibration"},
  "ttl_days": 90,
  "namespace": "user/priya.nair"
}
```

## Step 7: Configure Memory TTL

Memory entries have a time-to-live to prevent stale data from influencing decisions:

| Namespace | Default TTL | Rationale |
|-----------|-------------|-----------|
| User | 90 days | Personal baselines and preferences |
| Team | 180 days | Shared standards evolve slowly |
| Org | 365 days | Global policies persist |
| Session | End of session | Turn-by-turn context only |

In the CloudFormation template, the memory bucket has a lifecycle rule:

```yaml
LifecycleConfiguration:
  Rules:
    - Id: ExpireUserMemory
      Status: Enabled
      Prefix: user-memory/
      ExpirationInDays: 90
```

## Key Takeaways

1. **Two layers** — Short-term (in-session) + long-term (cross-session)
2. **Enables follow-ups** — "Has it gotten worse?" works without restating context
3. **Policy-respects** — Memory is user-scoped; can't access other users' memories
4. **Prompt injection** — Relevant memories are injected into the system prompt
5. **TTL-based expiry** — Stale data auto-expires, keeping memory fresh
6. **Three namespaces** — User, team, org for different sharing levels

## Next Steps

Your agent remembers. In the next module, you'll validate the complete system with **AgentCore Evaluations** — systematic testing of policy decisions and agent behavior.
