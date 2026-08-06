================================================================================
  DEMO: Autonomous Business Insights with AI Agent and MCP Servers
  Powered by Amazon Bedrock AgentCore + Strands Agents SDK + MCP
================================================================================

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  👩‍💼 USER: Sarah Chen | Role: Plant Manager | Scope: Full Access (all lines)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Query: "Which assembly lines need attention this week?"

Here are your **top 2 lines needing attention this week**, Sarah:

---

### 🔴 #1 — Line 4 (Plant 1) · *Immediate Action*
- **OEE: 74.7%** — Availability has dropped **-6.9 pts over 4 weeks** (94% → 87.1%), the steepest decline across all lines
- **Scrap rate: 3.5%** — spiked +1.7 pts week-over-week, nearly **3× the fleet average**, with a clear escalating trend (1.2% → 1.4% → 1.8% → 3.5%)
- **Root cause signal:** Simultaneous availability loss + accelerating scrap strongly suggests a degrading machine or tooling issue — not a one-off event
- **Action:** Escalate to Supervisor Anita Sharma; recommend equipment inspection + maintenance review on Line 4

---

### 🟡 #2 — Line 9 (Plant 3) · *Monitor Closely*
- **OEE: 73.3%** — Lowest OEE in the fleet this week; availability trending down **-4.5 pts over 4 weeks** (92% → 87.5%)
- **Scrap rate: 1.2%** — stable, so quality isn't the issue; the drag is purely availability/downtime
- **Root cause signal:** Gradual availability erosion points to a slow-developing mechanical or maintenance backlog issue
- **Action:** Flag to Supervisor Michael Torres; review maintenance schedule and check for overdue PMs on Line 9

---

> **No active IoT sensor anomalies** were detected fleet-wide as of now — the Line 4 scrap spike and availability declines are the primary risk vectors this week. Want me to drill deeper into either line?


────────────────────────────────────────────────────────────────────────────────

  Query: "What is the relationship between Line 4 and Line 9?"

**Short answer: Potentially yes — they share infrastructure, but no active anomalies are currently detected.**

Here's what the data shows:

### 🔗 Shared Infrastructure: Coolant Loop A
Both Line 4 and Line 9 are fed by the **same primary coolant loop**, making them structurally linked. If one line is experiencing thermal issues, the other is at risk.

| Parameter | Value | Status |
|---|---|---|
| Flow Rate | 108 / 120 L/min (90%) | ✅ Normal |
| Inlet Temp | 18.5°C | ✅ Normal |
| Outlet Temp | 24.2°C | ✅ Normal |
| Last Filter Change | 2026-04-12 (~46 days ago) | ⚠️ Worth checking |

### Active Anomalies
- **Line 4:** None detected
- **Line 9:** None detected

### Bottom Line
No active sensor anomalies on either line right now. However, **Coolant Loop A is the common failure point** — if the issues you're seeing are thermal in nature, they are almost certainly related. The loop filter hasn't been changed in ~46 days; depending on your PM schedule, that may warrant inspection. What kind of issues were you observing?


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  👨‍🔧 USER: Raj Patel | Role: Line Supervisor | Scope: Line 7 ONLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Query: "What is the status of Line 4?" (OUTSIDE his scope)

I'm sorry, Raj, but **Line 4 is outside your authorized scope**. Your current access permissions are limited to:

- **Plant:** Plant 2
- **Line:** Line 7
- **Equipment:** Machine 71, Machine 72, Machine 73, Machine 74, Machine 75

To get information about Line 4, you would need to contact a supervisor or manager with the appropriate permissions for that line.

Would you like me to pull up the current status for **Line 7** instead? I'm happy to help with anything within your authorized scope!


────────────────────────────────────────────────────────────────────────────────

  Query: "What is the OEE trend for Line 7?" (within scope)

Here's the **Line 7 OEE trend** over the last 4 weeks:

| Week | Availability | Performance | Quality | **OEE** |
|------|-------------|-------------|---------|---------|
| W-4  | 89.5%       | 85.7%       | 98.8%   | **75.4%** |
| W-3  | 90.2%       | 90.9%       | 96.7%   | **78.0%** |
| W-2  | 90.2%       | 90.1%       | 96.9%   | **77.2%** |
| W-1  | 90.9%       | 89.7%       | 97.0%   | **83.2%** |

**📈 Positive trajectory** — OEE improved from **75.4% → 83.2%** (+7.8 pts over 4 weeks).

- **Availability** is steadily climbing (+1.4 pts), now at **90.9%** ✅
- **Performance** recovered from a W-4 dip (85.7%) and stabilized around **89-91%**
- **Quality** remains consistently strong at **96-99%** ✅

No attention flags raised. Line 7 is trending in the right direction!


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  👩‍🔬 USER: Priya Nair | Role: Technician | Scope: Machine 41-45 only
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Query: "Has vibration on Machine 42 gotten worse since last week?"

**Yes — vibration on Machine 42 has worsened and crossed the warning threshold.**

| | Value |
|---|---|
| **Last week (noted)** | 3.8 mm/s |
| **Current** | 4.37 mm/s |
| **Change** | +0.57 mm/s (+15%) |
| **7-day avg** | 3.4 mm/s |
| **7-day max** | 4.44 mm/s |
| **Baseline** | 2.5 mm/s |
| **Warning threshold** | 4.0 mm/s ⚠️ |
| **Critical threshold** | 6.0 mm/s |

**Key takeaway:** Machine 42 has **breached the 4.0 mm/s warning threshold** and is trending upward (+79.9% over 7 days from the period low). All recent readings (last 24h) are consistently in the **4.17–4.44 mm/s** range — this is no longer a one-off spike.

**Recommended next steps:**
1. **Schedule inspection soon** — bearing wear or imbalance are likely culprits given the steady climb from baseline (2.5 → 3.8 → 4.37 mm/s).
2. **Check parts inventory** for relevant bearings/components before scheduling.
3. **Monitor closely** — at current trajectory, critical threshold (6.0 mm/s) could be reached if left unaddressed.


────────────────────────────────────────────────────────────────────────────────

  Query: "Are replacement bearings in stock?"

Here's the bearing stock status for Machine 42:

| Part | Part ID | On Hand | Reorder Point | Status |
|---|---|---|---|---|
| Deep Groove Ball Bearing 6205 | `bearing_6205` | 12 units | 20 units | ⚠️ **LOW** |

**Key Point:** Bearings are currently available (12 units on hand), but stock is **below the reorder threshold of 20 units** — so replenishment should be initiated. Supplier is **SKF Industrial** with a **14-day lead time** if you need to flag a reorder.

Given Machine 42's elevated vibration trend (3.8 mm/s last week, approaching the 4.0 mm/s warning threshold), it may be worth ensuring a reorder is placed proactively. Would you like me to check supplier lead times or look into anything else?


================================================================================
  END OF DEMO
================================================================================


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🧠 DEMO: Episodic Memory — Cross-Session Timeline Recall
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  User: Priya Nair | Role: Maintenance Technician | Scope: Machine 41-45

────────────────────────────────────────────────────────────────────────────────

  SESSION 1 (July 2):
  Query: "Machine 42 vibration seems high"

Current vibration for Machine 42: **3.8 mm/s**

| Metric | Value | Status |
|--------|-------|--------|
| Current | 3.8 mm/s | ⚠️ Elevated (baseline: 2.5 mm/s) |
| Warning threshold | 4.0 mm/s | Not yet crossed |
| Critical threshold | 6.0 mm/s | — |

The reading is elevated (+52% above baseline) but still below the warning threshold.
I've noted this for monitoring.

  → EPISODIC MEMORY STORED: "Vibration at 3.8 mm/s — flagged for monitoring"
     Action: flagged_for_monitoring

────────────────────────────────────────────────────────────────────────────────

  SESSION 2 (July 9):
  Query: "Schedule a bearing inspection for Machine 42"

✅ Bearing inspection scheduled for Machine 42:
- **Technician:** Priya Nair
- **Date:** July 16, 2026
- **Reason:** Elevated vibration trend (3.8 mm/s, +52% above baseline)
- **Parts check:** Bearings (bearing_6205) in stock — 12 units available

  → EPISODIC MEMORY STORED: "Scheduled bearing inspection for July 16"
     Action: scheduled_maintenance

────────────────────────────────────────────────────────────────────────────────

  SESSION 3 (July 23 — NEW SESSION, different day):
  Query: "Has Machine 42's vibration gotten worse?"

**Yes — significantly. Here's the full timeline from your past interactions:**

| Date | Reading | Event | Your Action |
|------|---------|-------|-------------|
| Baseline | 2.5 mm/s | Normal operating range | — |
| July 2 | 3.8 mm/s | Elevated, pre-warning | You flagged for monitoring |
| July 9 | — | — | You scheduled inspection |
| July 16 | 4.1 mm/s | Inspection: early bearing wear | Inspection completed |
| **Today** | **4.5 mm/s** | **Above WARNING threshold** | ⚠️ Action needed |

**Progression:** 2.5 → 3.8 → 4.1 → 4.5 mm/s over 3 weeks (+80% from baseline)

**Recommendation:** The bearing wear identified on July 16 is progressing.
At current rate, critical threshold (6.0 mm/s) could be reached in ~3 weeks.
Recommend expediting bearing replacement. Bearings in stock (12 units, bearing_6205).

  → MEMORY USED: Episodic timeline (4 past events recalled)
  → MEMORY USED: Long-term baseline (2.5 mm/s)
  → MEMORY USED: Team threshold (warning: 4.0, critical: 6.0)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  END EPISODIC MEMORY DEMO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  💰 DEMO: Cost Management — Budget Exceeded Scenario
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  User: Priya Nair | Role: Maintenance Technician
  Daily Token Limit: 30,000 | Current Usage: 29,400

────────────────────────────────────────────────────────────────────────────────

  Query: "What's the temperature trend on Machine 43?"

  [BUDGET] Daily token budget exceeded for 'Priya Nair'.
  Used: 29,400 / Limit: 30,000 tokens.
  Budget resets at midnight UTC.

I'm unable to process additional queries right now — your daily usage budget
has been reached.

**Current usage:** 29,400 / 30,000 tokens (98%)

**Options:**
1. Wait until midnight UTC for the daily reset
2. Contact your admin to increase your limit or reset your counter
3. Ask fewer, more targeted questions tomorrow to stay within budget

Your previous queries and results from today's session are still available
in memory for reference.

  → CEDAR POLICY: forbid_budget_exceeded MATCHED → DENY
  → DynamoDB: {user: priya.nair, date: 2026-08-05, count: 29400, limit: 30000}
  → No tool call executed. Zero additional tokens consumed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  END COST MANAGEMENT DEMO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
