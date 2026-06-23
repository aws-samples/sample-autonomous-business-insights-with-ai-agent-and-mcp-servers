#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Generate UML sequence diagrams for the AgentCore Gateway access control flow.

Produces two diagrams:
  1. ALLOWED flow — user queries within their authorized scope
  2. DENIED flow — user queries outside their authorized scope

Output: docs/sequence_diagram_access_control.png

Usage:
    python docs/create_sequence_diagram.py
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Color palette (AWS-inspired)
COLORS = {
    "user": "#232F3E",          # AWS dark
    "cognito": "#DD344C",       # Red (identity)
    "agent": "#FF9900",         # AWS orange
    "gateway": "#3B48CC",       # Blue (networking)
    "interceptor": "#1B660F",   # Green (compute)
    "cedar": "#8C4FFF",         # Purple (security)
    "tool": "#067D68",          # Teal (services)
    "allow": "#1B660F",         # Green
    "deny": "#D13212",          # Red
    "note_bg": "#FFFDE7",       # Light yellow
    "lifeline": "#CCCCCC",      # Gray
    "header_bg": "#F5F5F5",     # Light gray
}

FONT = {"family": "sans-serif", "size": 11}


def draw_participant(ax, x, y_top, y_bottom, label, color, width=1.4):
    """Draw a UML participant box (top header + lifeline)."""
    # Top box
    box = FancyBboxPatch(
        (x - width / 2, y_top - 0.3), width, 0.6,
        boxstyle="round,pad=0.05",
        facecolor=color, edgecolor=color, alpha=0.9,
    )
    ax.add_patch(box)
    ax.text(x, y_top, label, ha="center", va="center",
            fontsize=10.5, fontweight="bold", color="white")

    # Bottom box (activation end)
    box_b = FancyBboxPatch(
        (x - width / 2, y_bottom - 0.2), width, 0.4,
        boxstyle="round,pad=0.05",
        facecolor=color, edgecolor=color, alpha=0.9,
    )
    ax.add_patch(box_b)
    ax.text(x, y_bottom, label, ha="center", va="center",
            fontsize=9, color="white")

    # Lifeline (dashed)
    ax.plot([x, x], [y_top - 0.3, y_bottom + 0.2],
            linestyle="--", color=COLORS["lifeline"], linewidth=0.8, zorder=0)


def draw_message(ax, x_from, x_to, y, label, color="black",
                 dashed=False, fontsize=10, offset=0.12):
    """Draw a message arrow between participants."""
    ls = "--" if dashed else "-"
    ax.annotate(
        "", xy=(x_to, y), xytext=(x_from, y),
        arrowprops=dict(
            arrowstyle="->",
            color=color, lw=1.2, linestyle=ls,
        ),
    )
    mid_x = (x_from + x_to) / 2
    ax.text(mid_x, y + offset, label, ha="center", va="bottom",
            fontsize=fontsize, color=color, style="italic" if dashed else "normal")


def draw_self_message(ax, x, y, label, color="black", fontsize=9.5):
    """Draw a self-call (loop back to same participant)."""
    loop_w = 0.6
    ax.annotate(
        "", xy=(x + 0.05, y - 0.25), xytext=(x + 0.05, y),
        arrowprops=dict(arrowstyle="->", color=color, lw=1.0,
                        connectionstyle="arc3,rad=-0.4"),
    )
    ax.text(x + loop_w + 0.1, y - 0.12, label, ha="left", va="center",
            fontsize=fontsize, color=color)


def draw_note(ax, x, y, text, width=2.2, color=COLORS["note_bg"]):
    """Draw a UML note box."""
    lines = text.split("\n")
    height = 0.25 * len(lines) + 0.1
    box = FancyBboxPatch(
        (x - width / 2, y - height / 2), width, height,
        boxstyle="round,pad=0.05",
        facecolor=color, edgecolor="#999999", linewidth=0.8,
    )
    ax.add_patch(box)
    ax.text(x, y, text, ha="center", va="center",
            fontsize=9, family="monospace")


def draw_activation(ax, x, y_start, y_end, color, width=0.15):
    """Draw an activation bar on a lifeline."""
    rect = plt.Rectangle(
        (x - width / 2, y_end), width, y_start - y_end,
        facecolor=color, alpha=0.3, edgecolor=color, linewidth=0.8,
    )
    ax.add_patch(rect)


def draw_alt_frame(ax, x_left, x_right, y_top, y_mid, y_bottom, label_if, label_else):
    """Draw a UML alt (if/else) frame."""
    # Outer frame
    ax.plot([x_left, x_right, x_right, x_left, x_left],
            [y_top, y_top, y_bottom, y_bottom, y_top],
            color="#666666", linewidth=1.2)
    # "alt" label
    ax.text(x_left + 0.1, y_top - 0.08, "alt", fontsize=10,
            fontweight="bold", color="#666666", va="top")
    # Divider
    ax.plot([x_left, x_right], [y_mid, y_mid],
            linestyle="--", color="#666666", linewidth=0.8)
    # Guards
    ax.text(x_left + 0.3, y_top - 0.25, f"[{label_if}]", fontsize=9.5,
            color=COLORS["allow"], fontweight="bold")
    ax.text(x_left + 0.3, y_mid - 0.12, f"[{label_else}]", fontsize=9.5,
            color=COLORS["deny"], fontweight="bold")


# ---------------------------------------------------------------------------
# Diagram 1: End-to-End Flow (ALLOWED + DENIED)
# ---------------------------------------------------------------------------

def create_main_sequence_diagram():
    """Create the primary sequence diagram showing the full access control flow."""
    fig, ax = plt.subplots(1, 1, figsize=(16, 14))
    ax.set_xlim(-0.5, 14)
    ax.set_ylim(-14.5, 1.5)
    ax.axis("off")

    # Title
    ax.text(7, 1.2, "AgentCore Gateway: Fine-Grained Access Control — Sequence Diagram",
            ha="center", va="center", fontsize=16, fontweight="bold", color=COLORS["user"])
    ax.text(7, 0.85, "GW Policy + Custom REQUEST/RESPONSE Interceptors + Cedar Authorization",
            ha="center", va="center", fontsize=12, color="#555555")

    # Participants
    participants = [
        (1.0, "User\n(Browser/CLI)", COLORS["user"]),
        (3.5, "Amazon\nCognito", COLORS["cognito"]),
        (5.8, "Agent\n(Strands SDK)", COLORS["agent"]),
        (8.2, "AgentCore\nGateway", COLORS["gateway"]),
        (10.2, "REQUEST\nInterceptor", COLORS["interceptor"]),
        (11.8, "Cedar Policy\nEngine", COLORS["cedar"]),
        (13.5, "MCP Tool\n(Lambda)", COLORS["tool"]),
    ]

    y_top = 0.4
    y_bottom = -14.0

    for x, label, color in participants:
        draw_participant(ax, x, y_top, y_bottom, label, color)

    # --- Authentication Phase ---
    y = -0.5
    ax.text(0.0, y, "Authentication", fontsize=11, fontweight="bold",
            color="#333333", va="center")
    ax.axhline(y=y - 0.15, xmin=0.03, xmax=0.97, color="#EEEEEE", linewidth=0.5)

    y = -0.9
    draw_message(ax, 1.0, 3.5, y, "1. Login (username + password)", COLORS["user"])

    y = -1.4
    draw_message(ax, 3.5, 1.0, y, "2. JWT {role, line_scope, plant_scope, equipment_scope}",
                 COLORS["cognito"], dashed=True)
    draw_note(ax, 3.5, y - 0.4,
              "JWT Claims:\n  custom:role = line_supervisor\n  custom:line_scope = Line 7\n  custom:plant_scope = Plant 2",
              width=3.0)

    # --- Query Phase ---
    y = -2.5
    ax.text(0.0, y, "Tool Invocation", fontsize=11, fontweight="bold",
            color="#333333", va="center")
    ax.axhline(y=y - 0.15, xmin=0.03, xmax=0.97, color="#EEEEEE", linewidth=0.5)

    y = -2.9
    draw_message(ax, 1.0, 5.8, y, '3. "What\'s the OEE for Line 7?"', COLORS["user"])

    y = -3.4
    draw_self_message(ax, 5.8, y, "4. LLM reasons:\n     need get_oee_trends(line='Line 7')",
                      COLORS["agent"])

    y = -4.0
    draw_message(ax, 5.8, 8.2, y, '5. MCP call: get_oee_trends(line="Line 7")\n    + Authorization: Bearer <JWT>',
                 COLORS["agent"])

    # Activation on gateway
    draw_activation(ax, 8.2, -4.0, -7.0, COLORS["gateway"])

    # --- Interceptor Phase ---
    y = -4.7
    ax.text(0.0, y, "Enrichment", fontsize=11, fontweight="bold",
            color="#333333", va="center")
    ax.axhline(y=y - 0.15, xmin=0.03, xmax=0.97, color="#EEEEEE", linewidth=0.5)

    y = -5.1
    draw_message(ax, 8.2, 10.2, y, "6. Invoke REQUEST Interceptor", COLORS["gateway"])
    draw_activation(ax, 10.2, -5.1, -6.0, COLORS["interceptor"])

    y = -5.5
    draw_self_message(ax, 10.2, y,
                      "7. Decode JWT payload\n     Extract: role, line_scope\n     Inject user_context into args",
                      COLORS["interceptor"])

    y = -6.2
    draw_message(ax, 10.2, 8.2, y, '8. Enriched request:\n    args.user_context = {role, scope}',
                 COLORS["interceptor"], dashed=True)

    # --- Policy Phase ---
    y = -6.7
    ax.text(0.0, y, "Authorization", fontsize=11, fontweight="bold",
            color="#333333", va="center")
    ax.axhline(y=y - 0.15, xmin=0.03, xmax=0.97, color="#EEEEEE", linewidth=0.5)

    y = -7.1
    draw_message(ax, 8.2, 11.8, y,
                 '9. Evaluate: principal=Raj, action=get_oee_trends,\n    context.input.line="Line 7"',
                 COLORS["gateway"])
    draw_activation(ax, 11.8, -7.1, -8.2, COLORS["cedar"])

    y = -7.7
    draw_note(ax, 11.8, y,
              "Cedar Evaluation:\n  permit_all → PERMIT\n  forbid_line_scope:\n    'Line 7' in ['Line 7']? YES\n    → No forbid match\n  Result: ALLOW",
              width=3.0, color="#E8F5E9")

    # --- ALT Frame ---
    alt_top = -8.5
    alt_mid = -10.5
    alt_bottom = -13.0
    draw_alt_frame(ax, 0.5, 14.0, alt_top, alt_mid, alt_bottom,
                   "ALLOW — parameter in user scope", "DENY — parameter outside scope")

    # ALLOW path
    y = -8.9
    draw_message(ax, 11.8, 8.2, y, "10a. Decision: ALLOW", COLORS["allow"], dashed=True)

    y = -9.3
    draw_message(ax, 8.2, 13.5, y, "11a. Execute Lambda tool target", COLORS["gateway"])
    draw_activation(ax, 13.5, -9.3, -9.8, COLORS["tool"])

    y = -9.9
    draw_message(ax, 13.5, 8.2, y, "12a. OEE data (Line 7, 4 weeks)", COLORS["tool"], dashed=True)

    y = -10.3
    draw_message(ax, 8.2, 5.8, y, "13a. Tool result → Agent", COLORS["gateway"], dashed=True)

    # DENY path
    y = -10.9
    draw_message(ax, 11.8, 8.2, y, '10b. Decision: DENY\n    "Line 4 not in scope [Line 7]"',
                 COLORS["deny"], dashed=True)

    y = -11.5
    draw_note(ax, 13.5, y, "MCP Server\nNEVER\nINVOKED", width=1.6, color="#FFEBEE")

    y = -11.9
    draw_message(ax, 8.2, 5.8, y,
                 '11b. Error: "[Policy] Access denied. Scope: Line 7 only"',
                 COLORS["deny"], dashed=True)

    # --- Response Phase ---
    y = -12.5
    draw_self_message(ax, 5.8, y,
                      "LLM synthesizes:\n  ALLOW → data summary\n  DENY → explains scope + suggests alternative",
                      COLORS["agent"])

    y = -13.3
    draw_message(ax, 5.8, 1.0, y, "14. Natural language response to user",
                 COLORS["agent"], dashed=True)

    # Legend
    legend_y = -14.3
    legend_items = [
        (1.0, "Solid arrow = synchronous call", "-"),
        (5.0, "Dashed arrow = response/return", "--"),
        (9.5, "Green box = ALLOW path", None),
        (12.0, "Red box = DENY path", None),
    ]
    for lx, ltxt, ls in legend_items:
        if ls:
            ax.annotate("", xy=(lx + 0.8, legend_y), xytext=(lx, legend_y),
                        arrowprops=dict(arrowstyle="->", color="black", lw=1,
                                        linestyle=ls))
            ax.text(lx + 1.0, legend_y, ltxt, fontsize=9, va="center")
        elif "Green" in ltxt:
            ax.add_patch(plt.Rectangle((lx, legend_y - 0.08), 0.3, 0.16,
                                       facecolor=COLORS["allow"], alpha=0.3))
            ax.text(lx + 0.4, legend_y, ltxt, fontsize=9, va="center")
        else:
            ax.add_patch(plt.Rectangle((lx, legend_y - 0.08), 0.3, 0.16,
                                       facecolor=COLORS["deny"], alpha=0.3))
            ax.text(lx + 0.4, legend_y, ltxt, fontsize=9, va="center")

    plt.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Diagram 2: Three Personas Comparison
# ---------------------------------------------------------------------------

def create_personas_diagram():
    """Create a comparison diagram showing same query, three different outcomes.

    Layout: Three rows (one per persona), each with a horizontal left-to-right flow.
    AgentCore Gateway components are highlighted with a distinct background region.
    """
    fig, axes = plt.subplots(3, 1, figsize=(18, 12))

    personas = [
        {
            "name": "Sarah Chen",
            "role": "Plant Manager",
            "query": "Anomalies across all lines?",
            "scope": "Full Access\n(all plants/lines)",
            "result": "ALLOW",
            "detail": "Sees all 12 lines,\nprioritized by severity",
        },
        {
            "name": "Raj Patel",
            "role": "Line Supervisor",
            "query": "Show Line 4 equipment",
            "scope": "Line 7,\nPlant 2 only",
            "result": "DENY",
            "detail": "Line 4 outside scope.\nSuggests Line 7 instead.",
        },
        {
            "name": "Priya Nair",
            "role": "Maintenance Tech",
            "query": "Machine 72 vibration?",
            "scope": "Machines 41-45\nonly",
            "result": "DENY",
            "detail": "Machine 72 not assigned.\nSuggests Machine 42.",
        },
    ]

    # Horizontal positions for each step (left-to-right flow)
    x_positions = {
        "user": 1.5,
        "agent": 4.5,
        "gateway": 8.0,
        "cedar": 11.5,
        "tool": 14.5,
        "response": 17.5,
    }
    # Captions aligned at top of each row
    captions = ["User Query", "Strands Agent", "AgentCore\nGateway", "Cedar Policy\nEngine", "MCP Tool\n(Lambda)", "Agent Response"]
    caption_xs = [x_positions["user"], x_positions["agent"], x_positions["gateway"],
                  x_positions["cedar"], x_positions["tool"], x_positions["response"]]

    box_w = 2.4
    box_h = 1.4
    y_center = 0.0  # vertical center of each row's flow

    for idx, (ax, persona) in enumerate(zip(axes, personas)):
        ax.set_xlim(-0.5, 19.5)
        ax.set_ylim(-2.0, 2.5)
        ax.axis("off")

        # --- AgentCore Gateway highlight region (behind Gateway + Cedar) ---
        ac_x_start = x_positions["gateway"] - box_w / 2 - 0.4
        ac_x_end = x_positions["cedar"] + box_w / 2 + 0.4
        ac_region = FancyBboxPatch(
            (ac_x_start, y_center - box_h / 2 - 0.5),
            ac_x_end - ac_x_start,
            box_h + 1.0,
            boxstyle="round,pad=0.15",
            facecolor="#EDE7F6", edgecolor=COLORS["gateway"], linewidth=2.0,
            linestyle="-", alpha=0.5,
        )
        ax.add_patch(ac_region)
        # AgentCore label above the region
        ax.text(
            (x_positions["gateway"] + x_positions["cedar"]) / 2,
            y_center + box_h / 2 + 0.65,
            "Amazon Bedrock AgentCore",
            ha="center", va="bottom", fontsize=12, fontweight="bold",
            color=COLORS["gateway"], alpha=0.9,
        )

        # --- Persona label (left side) ---
        ax.text(-0.2, y_center + 0.3, persona["name"], ha="left", va="center",
                fontsize=13, fontweight="bold", color=COLORS["user"])
        ax.text(-0.2, y_center - 0.2, persona["role"], ha="left", va="center",
                fontsize=11, color="#555555")

        # --- Step captions (only on first row to avoid repetition) ---
        if idx == 0:
            for cap, cx in zip(captions, caption_xs):
                ax.text(cx, y_center + box_h / 2 + 1.2, cap, ha="center", va="bottom",
                        fontsize=11, fontweight="bold", color="#333333")

        # --- Step boxes (horizontal flow) ---
        # 1. User Query
        _draw_hbox(ax, x_positions["user"], y_center, box_w, box_h,
                   f'"{persona["query"]}"', facecolor="#E3F2FD", edgecolor="#1565C0")

        # 2. Agent processes
        _draw_hbox(ax, x_positions["agent"], y_center, box_w, box_h,
                   "LLM reasons →\nselects MCP tool", facecolor="#FFF3E0", edgecolor=COLORS["agent"])

        # 3. Gateway (interceptor)
        _draw_hbox(ax, x_positions["gateway"], y_center, box_w, box_h,
                   "REQUEST Interceptor\n+ JWT extraction", facecolor="#E8EAF6", edgecolor=COLORS["gateway"])

        # 4. Cedar evaluation
        _draw_hbox(ax, x_positions["cedar"], y_center, box_w, box_h,
                   f"Cedar scope:\n{persona['scope']}", facecolor="#F3E5F5", edgecolor=COLORS["cedar"])

        # 5. Tool execution (color depends on result)
        if persona["result"] == "ALLOW":
            _draw_hbox(ax, x_positions["tool"], y_center, box_w, box_h,
                       "Lambda executes\n✓ Returns data",
                       facecolor="#E8F5E9", edgecolor=COLORS["allow"], linewidth=2)
        else:
            _draw_hbox(ax, x_positions["tool"], y_center, box_w, box_h,
                       "Lambda NOT\ninvoked ✗",
                       facecolor="#FFEBEE", edgecolor=COLORS["deny"], linewidth=2)

        # 6. Agent response
        if persona["result"] == "ALLOW":
            _draw_hbox(ax, x_positions["response"], y_center, box_w, box_h,
                       persona["detail"],
                       facecolor="#E8F5E9", edgecolor=COLORS["allow"])
        else:
            _draw_hbox(ax, x_positions["response"], y_center, box_w, box_h,
                       persona["detail"],
                       facecolor="#FFEBEE", edgecolor=COLORS["deny"])

        # --- Arrows between steps ---
        arrow_pairs = [
            ("user", "agent"),
            ("agent", "gateway"),
            ("gateway", "cedar"),
            ("cedar", "tool"),
            ("tool", "response"),
        ]
        for src_key, dst_key in arrow_pairs:
            x_from = x_positions[src_key] + box_w / 2 + 0.05
            x_to = x_positions[dst_key] - box_w / 2 - 0.05
            # Color the arrow to/from tool based on decision
            if dst_key == "tool" or src_key == "tool":
                arr_color = COLORS["allow"] if persona["result"] == "ALLOW" else COLORS["deny"]
            else:
                arr_color = "#333333"
            ax.annotate(
                "", xy=(x_to, y_center), xytext=(x_from, y_center),
                arrowprops=dict(arrowstyle="-|>", color=arr_color, lw=1.8,
                                shrinkA=2, shrinkB=2),
            )

        # --- Decision badge (small label on the cedar→tool arrow) ---
        badge_x = (x_positions["cedar"] + x_positions["tool"]) / 2
        badge_color = COLORS["allow"] if persona["result"] == "ALLOW" else COLORS["deny"]
        ax.text(badge_x, y_center + 0.35, persona["result"], ha="center", va="bottom",
                fontsize=12, fontweight="bold", color="white",
                bbox=dict(boxstyle="round,pad=0.2", facecolor=badge_color, alpha=0.9))

        # Separator line between rows (except last)
        if idx < len(personas) - 1:
            ax.axhline(y=-1.8, xmin=0.02, xmax=0.98, color="#DDDDDD", linewidth=1)

    fig.suptitle(
        "Same Agent, Same Interface — Different Data Access\n"
        "AgentCore Gateway enforces Cedar policies at the parameter level",
        fontsize=16, fontweight="bold", y=0.99,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    return fig


def _draw_hbox(ax, x_center, y_center, width, height, text,
               facecolor="#FFFFFF", edgecolor="#333333", linewidth=1.2):
    """Draw a rounded box centered at (x_center, y_center) with text inside."""
    box = FancyBboxPatch(
        (x_center - width / 2, y_center - height / 2), width, height,
        boxstyle="round,pad=0.1",
        facecolor=facecolor, edgecolor=edgecolor, linewidth=linewidth,
    )
    ax.add_patch(box)
    ax.text(x_center, y_center, text, ha="center", va="center",
            fontsize=10.5, color="#222222", linespacing=1.3)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os

    output_dir = os.path.dirname(os.path.abspath(__file__))

    # Diagram 1: Main sequence diagram
    fig1 = create_main_sequence_diagram()
    path1 = os.path.join(output_dir, "sequence_diagram_access_control.png")
    fig1.savefig(path1, dpi=200, bbox_inches="tight", facecolor="white")
    print(f"Saved: {path1}")
    plt.close(fig1)

    # Diagram 2: Three personas comparison
    fig2 = create_personas_diagram()
    path2 = os.path.join(output_dir, "sequence_diagram_personas.png")
    fig2.savefig(path2, dpi=200, bbox_inches="tight", facecolor="white")
    print(f"Saved: {path2}")
    plt.close(fig2)

    print("\nDone! Two diagrams generated for blog post.")
