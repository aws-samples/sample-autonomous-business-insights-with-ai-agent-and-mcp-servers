# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

#!/usr/bin/env python3
"""Generate a clean sequence diagram PNG: Line Supervisor DENIED access to Line 4."""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# --- Configuration ---
fig, ax = plt.subplots(1, 1, figsize=(14, 16))
ax.set_xlim(0, 14)
ax.set_ylim(0, 20)
ax.axis("off")
fig.patch.set_facecolor("white")

# Colors
C_HEADER = "#232F3E"       # AWS dark
C_ALLOW = "#1B8A4B"        # green
C_DENY = "#D13212"         # red
C_GATEWAY = "#FF9900"      # AWS orange
C_AGENT = "#527FFF"        # blue
C_POLICY = "#8C4FFF"       # purple
C_MCP = "#7D8998"          # gray
C_USER = "#2E73B8"         # user blue
C_BG_DENY = "#FDECEA"      # light red background
C_BG_NOTE = "#FFF3CD"      # light yellow for notes

# --- Title ---
ax.text(7, 19.5, "Scenario: DENIED — Line Supervisor Queries Line 4 (Out of Scope)",
        ha="center", va="center", fontsize=14, fontweight="bold", color=C_HEADER)

# --- Participants (columns) ---
participants = [
    (1.5, "Line Supervisor\n(Browser/CLI)", C_USER),
    (4.5, "Agent\n(Strands + Bedrock)", C_AGENT),
    (7.5, "Gateway\n(AgentCore)", C_GATEWAY),
    (10.5, "Policy Engine\n(Cedar)", C_POLICY),
    (13.0, "MCP Server\n(Equipment)", C_MCP),
]

for x, label, color in participants:
    # Header box
    box = FancyBboxPatch((x - 0.9, 18.4), 1.8, 0.9,
                         boxstyle="round,pad=0.1", facecolor=color,
                         edgecolor=color, alpha=0.15)
    ax.add_patch(box)
    ax.text(x, 18.85, label, ha="center", va="center", fontsize=8.5,
            fontweight="bold", color=color)
    # Lifeline
    ax.plot([x, x], [18.4, 1.0], color=color, linewidth=0.8,
            linestyle="--", alpha=0.4)


def draw_arrow(x1, x2, y, label, color="black", style="-|>", fontsize=7.5, dashed=False):
    """Draw a labeled arrow between two x positions at height y."""
    ls = "--" if dashed else "-"
    ax.annotate("", xy=(x2, y), xytext=(x1, y),
                arrowprops=dict(arrowstyle=style, color=color,
                                lw=1.2, linestyle=ls))
    mid_x = (x1 + x2) / 2
    ax.text(mid_x, y + 0.2, label, ha="center", va="bottom",
            fontsize=fontsize, color=color, style="italic" if dashed else "normal")


def draw_note(x, y, text, width=2.8, color=C_BG_NOTE, text_color="black", fontsize=7):
    """Draw a note box."""
    box = FancyBboxPatch((x - width / 2, y - 0.35), width, 0.7,
                         boxstyle="round,pad=0.08", facecolor=color,
                         edgecolor="#CCCCCC", linewidth=0.8)
    ax.add_patch(box)
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize,
            color=text_color, wrap=True)


# --- Sequence Steps ---
y = 17.8

# Step 1: Line Supervisor → Agent
draw_arrow(1.5, 4.5, y, '"Show me equipment status for Line 4"', C_USER)
y -= 1.0

# Step 2: Agent reasons
draw_note(4.5, y, "LLM reasons: need\nget_equipment_status(line='Line 4')", 3.0, "#E8F0FE", C_AGENT)
y -= 1.0

# Step 3: Agent → Gateway
draw_arrow(4.5, 7.5, y, 'tools/call: get_equipment_status(line="Line 4")', C_AGENT)
y -= 0.9

# Step 4: Gateway validates JWT
draw_note(7.5, y, "Validate JWT ✓\nRole: line_supervisor\nScope: Line 7 only", 3.0, "#FFF3E0", C_GATEWAY)
y -= 1.0

# Step 5: REQUEST Interceptor
draw_note(7.5, y, "REQUEST Interceptor:\nDecode JWT → inject user_context\nline_scope: ['Line 7']", 3.2, "#FFF3E0", C_GATEWAY)
y -= 1.1

# Step 6: Gateway → Policy Engine
draw_arrow(7.5, 10.5, y, "evaluate(role=line_supervisor, line='Line 4')", C_GATEWAY)
y -= 1.0

# Step 7: Cedar evaluation
draw_note(10.5, y,
          "Cedar evaluation:\n"
          "permit_all → PERMIT ✓\n"
          "forbid_line_scope:\n"
          "  'Line 4' in ['Line 7']? NO\n"
          "  → FORBID MATCHES",
          3.4, "#F3E8FF", C_POLICY, fontsize=6.8)
y -= 1.4

# Step 8: Policy → Gateway: DENY
draw_arrow(10.5, 7.5, y, "DENY (forbid overrides permit)", C_DENY)
y -= 1.0

# Step 9: MCP NEVER CALLED highlight
box_x = 12.0
box = FancyBboxPatch((box_x - 1.2, y - 0.4), 2.4, 0.8,
                     boxstyle="round,pad=0.1", facecolor=C_BG_DENY,
                     edgecolor=C_DENY, linewidth=1.5)
ax.add_patch(box)
ax.text(box_x, y, "MCP SERVER\nNEVER CALLED", ha="center", va="center",
        fontsize=7.5, fontweight="bold", color=C_DENY)
# X mark over MCP lifeline
ax.plot([12.7, 13.3], [y + 0.2, y - 0.2], color=C_DENY, linewidth=2.5)
ax.plot([12.7, 13.3], [y - 0.2, y + 0.2], color=C_DENY, linewidth=2.5)
y -= 1.1

# Step 10: Gateway → Agent: deny response
draw_arrow(7.5, 4.5, y, '"[Policy] Access denied. Line 4 not authorized. Scope: Line 7"', C_DENY)
y -= 1.0

# Step 11: Agent reads deny, adjusts
draw_note(4.5, y, "LLM reads deny message,\nadjusts response gracefully", 3.0, "#E8F0FE", C_AGENT)
y -= 1.0

# Step 12: Agent → Line Supervisor
draw_arrow(4.5, 1.5, y, '"I don\'t have access to Line 4. My scope is Line 7.\nWould you like Line 7 equipment status instead?"', C_AGENT, fontsize=6.8)
y -= 1.2

# --- Footer: Key Insight ---
footer_box = FancyBboxPatch((1.0, y - 0.5), 12.0, 0.9,
                            boxstyle="round,pad=0.1", facecolor="#F0F7FF",
                            edgecolor=C_HEADER, linewidth=1.0)
ax.add_patch(footer_box)
ax.text(7, y, "Key: Policy enforcement is parameter-level — the Line Supervisor CAN call get_equipment_status, "
              "just not with line=\"Line 4\". The MCP server is never contacted for denied requests.",
        ha="center", va="center", fontsize=7.5, color=C_HEADER, style="italic")

# --- Save ---
output_path = "/Users/hisuds/Suds/Official/Kiro/sample-autonomous-business-insights-with-ai-agent-and-mcp-servers/docs/sequence_diagram_deny_line_supervisor.png"
plt.tight_layout(pad=0.5)
plt.savefig(output_path, dpi=200, bbox_inches="tight", facecolor="white")
plt.close()
print(f"✅ Saved: {output_path}")
