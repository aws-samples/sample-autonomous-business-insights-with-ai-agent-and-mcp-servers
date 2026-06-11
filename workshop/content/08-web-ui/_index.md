---
title: "Module 8: Web UI Demo"
chapter: true
weight: 80
---

# Module 8: Streamlit Web UI

In this module, you'll use the Streamlit chat interface to demonstrate all three user personas and see the full system in action.

## Launch the UI

```bash
streamlit run src/demo_ui.py
```

Open **http://localhost:8501** in your browser.

## The Interface

The sidebar provides:
- **Data Mode toggle** — switch between simulated and live without restarting
- **User persona selector** — Sarah (Plant Manager), Raj (Line Supervisor), Priya (Technician)
- **Access scope display** — shows what each user can see
- **Sample queries** — click to auto-send common questions

## Demo Walkthrough

### Scenario 1: Sarah Chen (Full Access, Multi-Source Query)

1. Select **Sarah Chen** in the sidebar
2. Click: *"Which assembly lines need attention this week?"*
3. Observe: Agent calls Semantic Layer → IoT anomaly detection → OEE trends → Equipment status
4. Result: Severity-ranked list with root-cause correlation

### Scenario 2: Raj Patel (Policy Enforcement)

1. Switch to **Raj Patel**
2. Type: *"What is the status of Line 4?"*
3. Observe: Gateway **blocks** the query (Line 4 outside Raj's scope)
4. Result: Agent explains the restriction, offers to query Line 7
5. Click: *"What's the current status of Line 7?"*
6. Result: Full status report for his authorized line

### Scenario 3: Priya Nair (Memory-Augmented)

1. Switch to **Priya Nair**
2. Click: *"Has the vibration on Machine 42 gotten worse since last week?"*
3. Observe: Memory surfaces last week's baseline (3.8 mm/s), IoT returns current (5.4 mm/s)
4. Result: Week-over-week comparison with maintenance recommendation

## Key Observations

| Feature | How It's Demonstrated |
|---------|----------------------|
| Multi-source synthesis | Sarah's query correlates IoT + Analytics + Equipment |
| Policy enforcement | Raj's out-of-scope query is blocked at the Gateway |
| Memory context | Priya's follow-up uses last week's baseline without repeating it |
| Semantic Layer | Every query starts with `discover_data_sources` |
| Configuration, not code | Same agent, same MCP servers — different views per user |
