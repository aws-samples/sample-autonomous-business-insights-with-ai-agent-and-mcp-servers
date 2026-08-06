---
title: "AgentCore Memory"
weight: 65
---

# AgentCore Memory — Short-Term, Long-Term & Episodic Persistence

In this module, you'll explore the three memory constructs in AgentCore — short-term, long-term, and episodic — and understand when each activates from the end user's perspective.

## Why Does an Agent Need Memory?

Without memory, every conversation starts from zero:

```
Session 1: "What's Machine 42's vibration?"  → "4.5 mm/s"
Session 2: "Has it gotten worse?"            → "What do you mean by 'it'?"
```

With memory:

```
Session 1: "What's Machine 42's vibration?"  → "4.5 mm/s" [stored]
Session 2: "Has it gotten worse?"            → "Yes, up from 3.8 mm/s last week (+18%)"
```

## The Three Memory Constructs

```
┌─────────────────────────────────────────────────────────────────────┐
│  AgentCore Memory Model                                              │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  SHORT-TERM MEMORY (Session)                                    │ │
│  │  Scope: Single conversation session                             │ │
│  │  Lifetime: Destroyed when session ends                          │ │
│  │  Storage: In-memory (microVM RAM)                               │ │
│  │                                                                  │ │
│  │  Contains:                                                       │ │
│  │  • Turn-by-turn conversation history                             │ │
│  │  • Tool call results from this session                           │ │
│  │  • Coreference context ("it" = Machine 42)                       │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  LONG-TERM MEMORY (Persistent)                                  │ │
│  │  Scope: User / Team / Organization                              │ │
│  │  Lifetime: TTL-based (90 days user, 180 team, 365 org)          │ │
│  │  Storage: S3 (persists across sessions)                         │ │
│  │                                                                  │ │
│  │  Contains:                                                       │ │
│  │  • Baselines: "Machine 42 vibration normal = 3.2 mm/s"          │ │
│  │  • Preferences: "Sarah prefers severity-ranked lists"            │ │
│  │  • Thresholds (team): "Vibration warning = 4.0 mm/s"            │ │
│  │  • Standards (org): "OEE critical threshold = 80%"              │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  EPISODIC MEMORY (Events)                                       │ │
│  │  Scope: User-specific past interactions                         │ │
│  │  Lifetime: TTL-based (90 days)                                  │ │
│  │  Storage: S3 (timestamped entries)                              │ │
│  │                                                                  │ │
│  │  Contains:                                                       │ │
│  │  • Past insights: "July 15 — flagged Machine 42 vibration 3.8"  │ │
│  │  • Decisions made: "Scheduled bearing replacement for Aug 1"     │ │
│  │  • Queries asked: "Last week asked about Line 4 coolant"         │ │
│  │  • Outcomes: "After coolant flush, Line 9 throughput recovered"  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## When Each Memory Type Activates — User Scenarios

### Scenario 1: Short-Term Memory — Follow-Up Within a Session

**User: Priya (Maintenance Technician)**

```
Priya: "What's the vibration on Machine 42?"
Agent: "Current vibration: 4.5 mm/s (WARNING — above 4.0 threshold)"
       → SHORT-TERM stores: {machine_id: 42, metric: vibration, value: 4.5}

Priya: "What about temperature?"
Agent: "Machine 42 temperature: 77°C (12°C above baseline)"
       → SHORT-TERM resolves "what about" = same machine, different metric
       → No need to re-specify Machine 42

Priya: "Is that related?"
Agent: "Likely yes — elevated vibration often causes bearing friction,
        which raises motor temperature. Both trending up together suggests
        bearing degradation."
       → SHORT-TERM correlates two tool results from this session
```

**What activates:** Short-term memory holds the conversation context. "That" and "is that related" are resolved because the agent remembers what was just discussed.

### Scenario 2: Long-Term Memory — Baselines & Preferences

**User: Sarah (Plant Manager)**

```
Session on Monday:
Sarah: "Which lines need attention this week?"
Agent: Returns severity-ranked list (Lines 4, 9, 7)
       → LONG-TERM stores preference: "Sarah prefers severity-ranked output"

Session on Friday:
Sarah: "Weekly update?"
Agent: Returns severity-ranked list (learned preference)
       with comparison to Monday's values (baselines from long-term)
       → LONG-TERM recalled: Sarah likes ranked lists
       → LONG-TERM recalled: Monday's OEE values for comparison
```

**What activates:** Long-term memory persists across sessions. The agent learns Sarah's output preference once and applies it in every future session.

### Scenario 3: Episodic Memory — Past Events & Outcomes

**User: Priya (Maintenance Technician)**

```
3 weeks ago:
Priya: "Machine 42 vibration seems high at 3.8 mm/s"
Agent: "Noted. 3.8 is below WARNING threshold (4.0) but trending up."
       → EPISODIC stores: {date: July 2, event: "vibration 3.8, pre-warning"}

1 week ago:
Priya: "Schedule a bearing inspection for Machine 42"
Agent: "Inspection scheduled with Priya Nair for July 16."
       → EPISODIC stores: {date: July 9, event: "inspection scheduled"}

Today:
Priya: "Has Machine 42's vibration gotten worse?"
Agent: "Yes. Timeline:
        - July 2: 3.8 mm/s (you flagged it early)
        - July 9: 4.1 mm/s (inspection scheduled)
        - Today: 4.5 mm/s (+18% from your initial reading)
        Recommendation: Expedite bearing replacement."
       → EPISODIC recalled: the full history of interactions about this machine
```

**What activates:** Episodic memory remembers *what happened when*. It provides a timeline of past interactions, not just static facts.

### Scenario 4: Team Memory — Shared Thresholds

**User: Any maintenance technician**

```
Priya: "Is 4.5 mm/s vibration dangerous?"
Agent: "4.5 mm/s exceeds the team-defined WARNING threshold (4.0 mm/s)
        but is below CRITICAL (6.0 mm/s). Action recommended within 48 hours."
       → LONG-TERM (team namespace): thresholds shared across all technicians

New technician (Arun, just joined):
Arun: "What's the vibration limit for these machines?"
Agent: "Your team's thresholds:
        - Normal: < 3.5 mm/s
        - Warning: 4.0 mm/s (investigate within 48h)
        - Critical: 6.0 mm/s (stop machine immediately)"
       → Same LONG-TERM team memory, accessible to all maintenance_technicians
```

**What activates:** Team-scoped long-term memory. Thresholds set by one team member are available to all team members.

### Scenario 5: Episodic + Long-Term — Trend Comparison

**User: Sarah (Plant Manager)**

```
Sarah: "How does this week compare to last month?"
Agent: "Comparison (Line 4):
        - 4 weeks ago: OEE 84.5% (your baseline reading)
        - 3 weeks ago: 79.8% (you asked about coolant impact)
        - 2 weeks ago: 76.4% (bearing order placed)
        - This week:   72.2% (continued decline)

        Context from your past sessions:
        - You identified the coolant loop correlation on June 2
        - Bearing parts were ordered June 5 (14-day lead time — overdue)
        - Supply chain shows: bearings arrived yesterday, not yet installed"
       → EPISODIC: recalled past session queries and decisions
       → LONG-TERM: baseline OEE values persisted across weeks
```

## Step 1: Explore the Memory Manager Code

Open `src/memory/manager.py`:

```python
class SessionMemory:
    """SHORT-TERM: tracks conversation context within one session."""

    def __init__(self):
        self.turns: list[dict] = []
        self.tool_results: dict[str, Any] = {}

    def add_turn(self, role: str, content: str):
        self.turns.append({"role": role, "content": content})

    def get_context_window(self, max_turns: int = 10) -> list[dict]:
        """Return recent turns for coreference resolution."""
        return self.turns[-max_turns:]


class MemoryManager:
    """LONG-TERM + EPISODIC: persists across sessions."""

    def __init__(self, user_id: str):
        self.user_id = user_id

    def store(self, key: str, value: str, memory_type: str = "episodic",
              namespace: str = "user"):
        """Persist a fact or event.

        memory_type: "baseline" (long-term fact) or "episodic" (timestamped event)
        namespace: "user", "team", or "org"
        """
        entry = MemoryEntry(
            key=key,
            value=value,
            memory_type=memory_type,
            namespace=f"{namespace}/{self.user_id}",
            timestamp=datetime.now(),
        )
        self._persist(entry)

    def recall(self, query: str, memory_types: list[str] = None,
               max_results: int = 5) -> list[MemoryEntry]:
        """Retrieve relevant memories — semantic similarity matching."""
        return self._search(query, memory_types, max_results)

    def get_user_preferences(self) -> dict:
        """Retrieve stored user preferences (long-term)."""
        return self._get_by_type("preference")

    def get_episodic_timeline(self, topic: str, days: int = 30) -> list[MemoryEntry]:
        """Get chronological events related to a topic."""
        return self._search_episodic(topic, days)
```

## Step 2: How Memory Augments the System Prompt

Before each LLM call, relevant memories are injected:

```python
def build_prompt(user, memory_manager, session_memory, query):
    # 1. Recall long-term baselines relevant to this query
    baselines = memory_manager.recall(query, memory_types=["baseline"])

    # 2. Recall episodic events relevant to this query
    episodes = memory_manager.get_episodic_timeline(query, days=30)

    # 3. Get user preferences
    preferences = memory_manager.get_user_preferences()

    # 4. Get short-term session context
    recent_turns = session_memory.get_context_window(max_turns=5)

    # 5. Get team-scoped thresholds
    team_context = memory_manager.recall(query, namespace="team")

    return SYSTEM_PROMPT.format(
        user_name=user.username,
        user_role=user.role,
        session_context=format_turns(recent_turns),
        baselines=format_memories(baselines),
        episodic_context=format_timeline(episodes),
        preferences=format_preferences(preferences),
        team_context=format_memories(team_context),
    )
```

The LLM sees all relevant memory as structured context — enabling it to reference past events, apply preferences, and compare to baselines.

## Step 3: Test Short-Term Memory

Start the CLI as Priya:

```bash
python -m src.main
```

Select **3 (Priya Nair)** and test coreference resolution:

```
> What's the vibration on Machine 42?
> Is that above normal?
> Show me the trend over 7 days
> Should I schedule maintenance?
```

Each follow-up uses short-term memory to maintain context. "That" refers to the vibration value. "The trend" refers to Machine 42's vibration.

## Step 4: Test Episodic Memory (Cross-Session)

In the Streamlit UI (`streamlit run src/demo_ui.py`), as Priya:

**Session 1:**
```
> Machine 42 vibration is at 4.5 mm/s, flagging for review
```
Agent acknowledges. Episodic entry stored.

**Close tab. Open new tab (new session).**

**Session 2:**
```
> What did I flag last time about Machine 42?
```
Agent recalls the episodic entry: "You flagged Machine 42 vibration at 4.5 mm/s in your previous session."

## Step 4b: Episodic Memory — Code Usage

Here's how the agent uses `store()` and `get_episodic_timeline()` in practice:

```python
# After a tool call, store the event as episodic memory
from src.memory.manager import MemoryManager

memory = MemoryManager()

# Store an episodic event (what happened + when + user action)
memory.store(
    user_id="priya.nair",
    key="vibration_flagged",
    value="Machine 42 vibration at 4.5 mm/s — flagged for review",
    memory_type="episodic",
    namespace="user",
    tags=["machine_42", "vibration", "flagged"],
    source_tool="get_sensor_readings",
    source_params={"machine_id": 42, "metric": "vibration"},
    user_action="flagged_for_review",
)

# Later (different session) — retrieve the timeline
timeline = memory.get_episodic_timeline(
    user_id="priya.nair",
    topic="machine 42",
    days=30,
)

for event in timeline:
    print(f"  [{event.timestamp}] {event.content}")
    if event.user_action:
        print(f"    Action: {event.user_action}")
```

**Output:**
```
  [2026-07-02T14:30:00] Vibration reading on Machine 42: 3.8 mm/s — elevated but within warning threshold
    Action: flagged_for_monitoring
  [2026-07-09T11:00:00] Scheduled bearing inspection for Machine 42
    Action: scheduled_maintenance
  [2026-07-16T15:00:00] Inspection result: Bearing shows early wear pattern. Vibration at 4.1 mm/s
    Action: inspection_completed
  [2026-07-23T14:30:00] Machine 42 vibration at 4.5 mm/s — flagged for review
    Action: flagged_for_review
```

This timeline gives the agent full context to answer "Has it gotten worse?" — it can trace the progression from 3.8 → 4.1 → 4.5 mm/s over 3 weeks, with the actions taken at each step.

### When to Use Each Memory API

| API | Use When | Example |
|-----|----------|---------|
| `session.add_interaction()` | Every turn within a conversation | Track Q&A for follow-ups |
| `session.add_tool_result()` | After each tool call | Cache results for coreference ("that" = last value) |
| `memory.store(memory_type="long_term")` | Agent learns a stable fact | "Machine 42 normal baseline = 2.5 mm/s" |
| `memory.store(memory_type="episodic")` | Something happened worth remembering | "User flagged vibration at 4.5" |
| `memory.store(memory_type="preference")` | Agent learns user preference | "Sarah prefers ranked lists" |
| `memory.recall(query=...)` | Before answering, find relevant context | Search all memory by keyword |
| `memory.recall(memory_types=["episodic"])` | Need event history specifically | "What happened with Machine 42?" |
| `memory.get_episodic_timeline(topic=...)` | Need chronological event sequence | "Show me the progression" |
| `memory.get_long_term_context(tags=...)` | Need baselines or thresholds | "What's the normal vibration?" |
| `memory.get_user_preferences()` | Before formatting output | "Does Sarah want ranked or detailed?" |

## Step 5: Memory and Access Control

Memory respects policy boundaries:

| Memory Namespace | Who Can Access | Example |
|-----------------|----------------|---------|
| User (private) | Only that user | Priya's Machine 42 baselines |
| Team | All team members | Maintenance team thresholds |
| Org | Everyone in org | Global OEE standards |

**Critical rule:** Memory derived from denied data is NOT stored. If Raj tries to access Line 4 data and gets denied, no memory entry is created for that attempt.

## Step 6: Memory Storage Structure

In production, memories persist to S3:

```
s3://agentcore-memory-bucket/
├── user-memory/
│   └── priya.nair/
│       ├── baselines/
│       │   └── machine_42_vibration.json       ← LONG-TERM
│       ├── episodes/
│       │   ├── 2026-07-02_flagged_vibration.json  ← EPISODIC
│       │   ├── 2026-07-09_scheduled_inspection.json
│       │   └── 2026-07-23_vibration_worsened.json
│       └── preferences/
│           └── output_format.json              ← LONG-TERM
├── team-memory/
│   └── maintenance_technicians/
│       └── thresholds.json                     ← LONG-TERM (team)
└── org-memory/
    └── global_standards.json                   ← LONG-TERM (org)
```

Each episodic entry:

```json
{
  "key": "machine_42_vibration_flagged",
  "value": "Vibration at 4.5 mm/s — flagged for review. Above WARNING threshold.",
  "memory_type": "episodic",
  "timestamp": "2026-07-23T14:30:00Z",
  "source_tool": "get_sensor_readings",
  "source_params": {"machine_id": 42, "metric": "vibration"},
  "user_action": "flagged_for_review",
  "ttl_days": 90,
  "namespace": "user/priya.nair"
}
```

## Step 7: Memory TTL Configuration

| Memory Type | Namespace | Default TTL | Rationale |
|-------------|-----------|-------------|-----------|
| Short-term | Session | End of session | Turn context only |
| Baseline (long-term) | User | 90 days | Equipment baselines drift |
| Episodic | User | 90 days | Historical actions and events |
| Preference | User | 365 days | Rarely changes |
| Threshold (long-term) | Team | 180 days | Standards evolve slowly |
| Standard (long-term) | Org | 365 days | Global policies persist |

## Summary: Which Memory Fires When?

| User Says | Memory Used | Why |
|-----------|-------------|-----|
| "What about temperature?" (same session) | **Short-term** | Resolves "what about" = same machine |
| "Has it gotten worse?" (new session) | **Episodic** | Recalls past reading for comparison |
| "Is 4.5 dangerous?" | **Long-term (team)** | Team thresholds define danger levels |
| "Weekly update?" | **Long-term (user)** | Knows Sarah prefers ranked lists |
| "How does this compare to last month?" | **Episodic + Long-term** | Timeline of events + baselines |
| "What did I flag last time?" | **Episodic** | Past actions and decisions |

## Key Takeaways

1. **Short-term** — Within-session coreference and multi-turn context (destroyed on session end)
2. **Long-term** — Persistent facts: baselines, preferences, thresholds (TTL-based expiry)
3. **Episodic** — Timestamped events: what happened, when, what was decided (enables timelines)
4. **Three namespaces** — User (private), team (shared group), org (everyone)
5. **Policy-respecting** — Cannot store or recall data from denied scope
6. **Prompt injection** — All relevant memories injected before each LLM call

## Next Steps

Your agent remembers context across conversations. In the next module, you'll validate the complete system with **AgentCore Evaluations** — 7 metrics that measure policy compliance, tool accuracy, and response quality.
