#!/usr/bin/env python3
"""Generate a high-readability PNG diagram: AgentCore Component Interactions.

Shows the full request lifecycle through:
  USER → AGENT → GATEWAY (Interceptor → Cedar → Lambda/Deny) → AGENT → Response

Optimised for clear readability at screen and print resolution.
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# --- Larger canvas for readability ---
fig, ax = plt.subplots(1, 1, figsize=(22, 28))
ax.set_xlim(0, 22)
ax.set_ylim(0, 34)
ax.axis("off")
fig.patch.set_facecolor("white")

# --- Colors ---
C_HEADER = "#232F3E"
C_USER = "#2E73B8"
C_AGENT = "#527FFF"
C_GATEWAY = "#FF9900"
C_INTERCEPT = "#E07D00"
C_CEDAR = "#8C4FFF"
C_LAMBDA = "#1B8A4B"
C_DENY = "#D13212"
C_RESPONSE = "#00796B"
C_BG_GW = "#FFF8F0"


def draw_box(x, y, w, h, label, color, fontsize=14, sublabel=None, sublabel_size=11):
    """Draw a rounded box with label."""
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15",
                         facecolor=color, edgecolor=color, alpha=0.12)
    ax.add_patch(box)
    border = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15",
                            facecolor="none", edgecolor=color, linewidth=2.0)
    ax.add_patch(border)
    text_y = y + h / 2 + (0.25 if sublabel else 0)
    ax.text(x + w / 2, text_y, label, ha="center", va="center",
            fontsize=fontsize, fontweight="bold", color=color)
    if sublabel:
        ax.text(x + w / 2, y + h / 2 - 0.45, sublabel, ha="center", va="center",
                fontsize=sublabel_size, color=color, alpha=0.85)


def draw_arrow(x1, y1, x2, y2, label="", color="black", fontsize=11, curved=False, offset_y=0.35):
    """Draw arrow with optional label."""
    if curved:
        arrow = FancyArrowPatch((x1, y1), (x2, y2),
                                arrowstyle="-|>", mutation_scale=15,
                                color=color, linewidth=1.8,
                                connectionstyle="arc3,rad=0.2")
    else:
        arrow = FancyArrowPatch((x1, y1), (x2, y2),
                                arrowstyle="-|>", mutation_scale=15,
                                color=color, linewidth=1.8)
    ax.add_patch(arrow)
    if label:
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        ax.text(mid_x, mid_y + offset_y, label, ha="center", va="bottom",
                fontsize=fontsize, color=color, style="italic")


# === Title ===
ax.text(11, 33, "AgentCore Component Interactions", ha="center", va="center",
        fontsize=22, fontweight="bold", color=C_HEADER)
ax.text(11, 32.2, "Full Request Lifecycle: Authentication → Enrichment → Authorization → Execution → Response",
        ha="center", va="center", fontsize=13, color="#555555")

# === Step 1: USER → Identity ===
draw_box(1, 29.8, 4.5, 1.6, "USER", C_USER, fontsize=16, sublabel="Authenticates via IdP")
draw_box(8, 29.8, 5.5, 1.6, "Cognito / IdP", C_USER, fontsize=16, sublabel="Issues JWT with scope claims")
draw_arrow(5.5, 30.6, 8.0, 30.6, "Login", C_USER, fontsize=12)

# JWT annotation
ax.text(15.5, 30.6, "JWT: { role, line_scope,\n         equipment_scope, plant_scope }",
        ha="left", va="center", fontsize=11, color=C_USER,
        family="monospace",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#EBF5FB", edgecolor=C_USER, linewidth=1.0))

# === Step 2: AGENT ===
draw_box(2.5, 26.5, 17.0, 2.0, "AGENT (Strands + Amazon Bedrock Claude)", C_AGENT, fontsize=16,
         sublabel="System prompt includes: identity + scope + memory context. LLM decides which tools to call.",
         sublabel_size=12)
draw_arrow(11.0, 29.8, 11.0, 28.5, "JWT passed to agent session", C_USER, fontsize=11)

# === Step 3: GATEWAY (big container) ===
gw_y = 5.5
gw_h = 19.5
gw_box = FancyBboxPatch((1.5, gw_y), 19.0, gw_h, boxstyle="round,pad=0.3",
                         facecolor=C_BG_GW, edgecolor=C_GATEWAY, linewidth=2.5)
ax.add_patch(gw_box)
ax.text(11.0, gw_y + gw_h - 0.7, "AgentCore GATEWAY", ha="center", va="center",
        fontsize=18, fontweight="bold", color=C_GATEWAY)
ax.text(11.0, gw_y + gw_h - 1.5, "Single entry point — every tool call flows through here",
        ha="center", va="center", fontsize=12, color=C_GATEWAY, alpha=0.7)

# Arrow: Agent → Gateway
draw_arrow(11.0, 26.5, 11.0, gw_y + gw_h, "tools/call (MCP JSON-RPC)", C_AGENT, fontsize=12)

# --- Inside Gateway ---

# Step 3a: JWT Validation
draw_box(3.0, 22.0, 7.0, 1.4, "1. Validate JWT Signature", C_GATEWAY, fontsize=13,
         sublabel="Cognito JWKS verification", sublabel_size=11)

# Step 3b: REQUEST Interceptor
draw_box(3.0, 19.5, 7.0, 1.8, "2. REQUEST Interceptor (Lambda)", C_INTERCEPT, fontsize=13,
         sublabel="Decode JWT claims → inject user_context\ninto tool arguments + set x-user-role header",
         sublabel_size=10)

# Step 3c: Cedar Policy Engine
draw_box(3.0, 15.0, 16.0, 3.5, "3. CEDAR Policy Engine", C_CEDAR, fontsize=16)
# Cedar details
cedar_text = (
    "permit_all → PERMIT (baseline)\n"
    "forbid_line_scope → check line param vs user scope\n"
    "forbid_equipment_scope → check machine_id vs user scope\n"
    "forbid_plant_scope → check plant param vs user scope\n\n"
    "Rule: forbid > permit > deny-by-default"
)
ax.text(11.0, 16.4, cedar_text, ha="center", va="center", fontsize=10,
        color=C_CEDAR, family="monospace", linespacing=1.5)

# Arrows within gateway
draw_arrow(6.5, 22.0, 6.5, 21.4, "", C_GATEWAY)
draw_arrow(6.5, 19.5, 6.5, 18.7, "", C_INTERCEPT)

# Step 3d: Decision fork
# ALLOW path (left)
draw_box(2.5, 10.5, 7.5, 2.0, "ALLOW", C_LAMBDA, fontsize=16,
         sublabel="Invoke Lambda Tool Target\nExecute tool logic, return data", sublabel_size=11)
draw_arrow(7.0, 15.0, 6.25, 12.5, "PERMIT", C_LAMBDA, fontsize=12)

# DENY path (right)
draw_box(12.0, 10.5, 7.5, 2.0, "DENY", C_DENY, fontsize=16,
         sublabel='"[Policy] Access denied.\nNot authorized for Line 4"', sublabel_size=11)
draw_arrow(14.0, 15.0, 15.75, 12.5, "FORBID", C_DENY, fontsize=12)

# Step 3e: RESPONSE Interceptor
draw_box(3.0, 7.0, 16.0, 1.6, "4. RESPONSE Interceptor (Lambda)", C_RESPONSE, fontsize=14,
         sublabel="tools/list → filter by role  |  tool results → pass through", sublabel_size=11)
draw_arrow(6.25, 10.5, 8.0, 8.6, "", C_LAMBDA)
draw_arrow(15.75, 10.5, 14.0, 8.6, "", C_DENY)

# === Step 4: Back to AGENT ===
draw_box(3.0, 2.5, 16.0, 2.5, "AGENT Receives Result", C_AGENT, fontsize=16)
allow_text = 'ALLOW → synthesizes data into human-readable response'
deny_text = 'DENY  → explains scope limit, suggests alternative within scope'
ax.text(11.0, 4.0, allow_text, ha="center", va="center", fontsize=12, color=C_LAMBDA)
ax.text(11.0, 3.2, deny_text, ha="center", va="center", fontsize=12, color=C_DENY)

draw_arrow(11.0, 7.0, 11.0, 5.0, "", C_HEADER)

# === Step 5: Key Principles Footer ===
ax.text(11.0, 1.8, "Design Principles", ha="center", va="center",
        fontsize=14, fontweight="bold", color=C_HEADER)

principles = [
    ("LLM decides WHAT", "Cedar decides IF"),
    ("Fail-secure", "No permit = DENY"),
    ("Parameter-level access", "Same tool, different params\n= different decision"),
    ("MCP servers auth-unaware", "Zero access control\nin Lambdas"),
]

for i, (principle, detail) in enumerate(principles):
    x_pos = 2.0 + (i * 5.2)
    ax.text(x_pos, 1.0, f"▸ {principle}", ha="left", va="center",
            fontsize=11, fontweight="bold", color=C_HEADER)
    ax.text(x_pos, 0.3, f"  {detail}", ha="left", va="center",
            fontsize=9.5, color="#555555")

# === Save at high DPI ===
output_path = "/Users/hisuds/Suds/Official/Kiro/sample-autonomous-business-insights-with-ai-agent-and-mcp-servers/docs/agentcore_component_interactions.png"
plt.tight_layout(pad=1.0)
plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print(f"✅ Saved: {output_path}")
