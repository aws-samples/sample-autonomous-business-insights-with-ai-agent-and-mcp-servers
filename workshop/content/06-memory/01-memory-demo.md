---
title: "Memory in Action"
weight: 61
---

# Memory-Augmented Queries

## The Problem Without Memory

Without memory, every conversation starts from scratch:
- Priya asks "Show me vibration on Machine 42" → gets current reading
- Priya asks "Compare to last week" → agent has no idea what "last week" means

## Two Levels of Memory

### Short-term Memory (Session)

Maintains turn-by-turn context within a single session:
- "Show vibration on Machine 42" → remembers machine_id=42
- "Compare to last week" → understood as Machine 42, vibration, 7 days ago

### Long-term Memory (Cross-Session)

Persists selected insights across sessions, organized by namespace:
- **User-scoped**: Priya's preferred units, her assigned equipment list
- **Team-scoped**: Maintenance team's standard anomaly thresholds
- **Organization-scoped**: Equipment catalog, site codes

## Demo: Week-over-Week Comparison

Priya's long-term memory contains a baseline from last week:

```
"Last week's vibration reading on Machine 42: 3.8 mm/s
(elevated but within warning threshold of 4.0 mm/s)"
```

When she asks now:

```bash
python -c "
from src.config import AppConfig
from src.identity.models import PRIYA_NAIR
from src.agent.agent import ManufacturingInsightsAgent

agent = ManufacturingInsightsAgent(AppConfig())
response = agent.query(PRIYA_NAIR, 'Has the vibration on Machine 42 gotten worse since last week?')
print(response)
"
```

The agent:
1. Finds Priya's memory baseline (3.8 mm/s from last week)
2. Calls `get_sensor_readings(machine_id=42, metric="vibration")`
3. Gets current reading (~5.4 mm/s)
4. Compares: +42% increase, now above warning threshold
5. Recommends maintenance action

All without Priya specifying the timeframe or baseline value.

## How Memory is Injected

The system prompt includes memory context dynamically:

```python
## Memory Context
- [2026-05-26T14:30:00] Last week's vibration on Machine 42: 3.8 mm/s
- [2026-01-15T09:00:00] Standard thresholds - Vibration: warning at 4.0 mm/s
```

The agent sees this context and uses it for comparison.

{{% notice tip %}}
**In production**, AgentCore Memory automatically extracts and stores preferences, recurring patterns, and session summaries. Memory retrieval passes through Policy — even cached memories are access-controlled.
{{% /notice %}}
