# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

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

# Color palette — high contrast on white background (no light/golden/yellow)
COLORS = {
    "user": "#232F3E",          # AWS dark
    "cognito": "#B71C1C",       # Dark red (identity)
    "agent": "#C43E00",         # Dark burnt orange (agent — NOT yellow/golden)
    "gateway": "#1A237E",       # Dark indigo (networking)
    "interceptor": "#1B5E20",   # Dark green (compute)
    "cedar": "#4A148C",         # Dark purple (security)
    "tool": "#004D40",          # Dark teal (services)
    "allow": "#1B5E20",         # Dark green
    "deny": "#B71C1C",          # Dark red
    "note_bg": "#E3F2FD",       # Light blue (readable on white)
    "lifeline": "#BBBBBB",      # Gray
    "header_bg": "#F5F5F5",     # Light gray
}

FONT = {"family": "sans-serif", "size": 13}


def draw_participant(ax, x, y_top, y_bottom, label, color, width=1.7):
    """Draw a UML participant box (top header + lifeline)."""
    # Top box
    box = FancyBboxPatch(
        (x - width / 2, y_top - 0.35), width, 0.7,
        boxstyle="round,pad=0.05",
        facecolor=color, edgecolor=color, alpha=0.9,
    )
    ax.add_patch(box)
    ax.text(x, y_top, label, ha="center", va="center",
            fontsize=14, fontweight="bold", color="white")

    # Bottom box (activation end)
    box_b = FancyBboxPatch(
        (x - width / 2, y_bottom - 0.3), width, 0.6,
        boxstyle="round,pad=0.05",
        facecolor=color, edgecolor=color, alpha=0.9,
    )
    ax.add_patch(box_b)
    ax.text(x, y_bottom, label, ha="center", va="center",
            fontsize=12, fontweight="bold", color="white")

    # Lifeline (dashed)
    ax.plot([x, x], [y_top - 0.3, y_bottom + 0.2],
            linestyle="--", color=COLORS["lifeline"], linewidth=0.8, zorder=0)


def draw_message(ax, x_from, x_to, y, label, color="black",
                 dashed=False, fontsize=14, offset=0.16):
    """Draw a message arrow between participants."""
    ls = "--" if dashed else "-"
    ax.annotate(
        "", xy=(x_to, y), xytext=(x_from, y),
        arrowprops=dict(
            arrowstyle="-|>",
            color=color, lw=2.2, linestyle=ls,
        ),
    )
    mid_x = (x_from + x_to) / 2
    ax.text(mid_x, y + offset, label, ha="center", va="bottom",
            fontsize=fontsize, fontweight="bold", color=color,
            style="italic" if dashed else "normal")


def draw_self_message(ax, x, y, label, color="black", fontsize=13):
    """Draw a self-call (loop back to same participant)."""
    loop_w = 0.6
    ax.annotate(
        "", xy=(x + 0.05, y - 0.25), xytext=(x + 0.05, y),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=1.8,
                        connectionstyle="arc3,rad=-0.4"),
    )
    ax.text(x + loop_w + 0.1, y - 0.12, label, ha="left", va="center",
            fontsize=fontsize, fontweight="bold", color=color)


def draw_note(ax, x, y, text, width=2.4, color=COLORS["note_bg"]):
    """Draw a UML note box."""
    lines = text.split("\n")
    height = 0.28 * len(lines) + 0.15
    box = FancyBboxPatch(
        (x - width / 2, y - height / 2), width, height,
        boxstyle="round,pad=0.05",
        facecolor=color, edgecolor="#666666", linewidth=1.0,
    )
    ax.add_patch(box)
    ax.text(x, y, text, ha="center", va="center",
            fontsize=12, fontweight="bold", family="monospace")


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
            color="#444444", linewidth=1.5)
    # "alt" label
    ax.text(x_left + 0.1, y_top - 0.08, "alt", fontsize=14,
            fontweight="bold", color="#444444", va="top")
    # Divider
    ax.plot([x_left, x_right], [y_mid, y_mid],
            linestyle="--", color="#444444", linewidth=1.0)
    # Guards
    ax.text(x_left + 0.3, y_top - 0.25, f"[{label_if}]", fontsize=14,
            color=COLORS["allow"], fontweight="bold")
    ax.text(x_left + 0.3, y_mid - 0.12, f"[{label_else}]", fontsize=14,
            color=COLORS["deny"], fontweight="bold")


# ---------------------------------------------------------------------------
# Diagram 1: End-to-End Flow (ALLOWED + DENIED)
# ---------------------------------------------------------------------------

def create_main_sequence_diagram():
    """Create the primary sequence diagram showing the full access control flow."""
    fig, ax = plt.subplots(1, 1, figsize=(28, 26))
    ax.set_xlim(-0.5, 20.0)
    ax.set_ylim(-21.5, 2.0)
    ax.axis("off")

    # Title
    ax.text(10.0, 1.6, "AgentCore Gateway: Fine-Grained Access Control — Sequence Diagram",
            ha="center", va="center", fontsize=22, fontweight="bold", color=COLORS["user"])
    ax.text(10.0, 1.1, "GW Policy + Custom REQUEST/RESPONSE Interceptors + Cedar Authorization",
            ha="center", va="center", fontsize=15, fontweight="bold", color="#333333")

    # Participants — spread wider to avoid label collisions
    participants = [
        (1.0, "Ravi\n(Line Supervisor)", COLORS["user"]),
        (4.0, "Amazon\nCognito", COLORS["cognito"]),
        (7.0, "Agent\n(Strands SDK)", COLORS["agent"]),
        (10.0, "AgentCore\nGateway", COLORS["gateway"]),
        (12.8, "REQUEST\nInterceptor", COLORS["interceptor"]),
        (15.5, "Cedar Policy\nEngine", COLORS["cedar"]),
        (18.5, "MCP Tool\n(Lambda)", COLORS["tool"]),
    ]

    y_top = 0.6
    y_bottom = -19.2

    for x, label, color in participants:
        draw_participant(ax, x, y_top, y_bottom, label, color)

    # --- Authentication Phase ---
    y = -0.3
    ax.text(0.0, y, "Authentication", fontsize=15, fontweight="bold",
            color="#222222", va="center")
    ax.axhline(y=y - 0.15, xmin=0.03, xmax=0.97, color="#EEEEEE", linewidth=0.5)

    y = -0.8
    draw_message(ax, 1.0, 4.0, y, "1. Login (credentials)", COLORS["user"])

    y = -1.5
    draw_message(ax, 4.0, 1.0, y, "2. JWT {role, line_scope, plant_scope}",
                 COLORS["cognito"], dashed=True)
    draw_note(ax, 4.0, y - 0.5,
              "JWT Claims:\n  role = line_supervisor\n  line_scope = Line 7\n  plant_scope = Plant 2",
              width=2.8)

    # --- Query Phase ---
    y = -2.8
    ax.text(0.0, y, "Tool Invocation", fontsize=15, fontweight="bold",
            color="#222222", va="center")
    ax.axhline(y=y - 0.15, xmin=0.03, xmax=0.97, color="#EEEEEE", linewidth=0.5)

    y = -3.3
    draw_message(ax, 1.0, 7.0, y, '3. "What\'s the OEE for Line 7?"', COLORS["user"])

    y = -3.9
    draw_self_message(ax, 7.0, y, "4. LLM reasons: need get_oee_trends(line='Line 7')",
                      COLORS["agent"])

    y = -5.1
    draw_message(ax, 7.0, 10.0, y, '5. MCP call: get_oee_trends(line="Line 7")  +  Authorization: Bearer <JWT>',
                 COLORS["agent"], fontsize=12)

    # Activation on gateway
    draw_activation(ax, 10.0, -5.1, -7.8, COLORS["gateway"])

    # --- Interceptor Phase ---
    y = -5.4
    ax.text(0.0, y, "Enrichment", fontsize=15, fontweight="bold",
            color="#222222", va="center")
    ax.axhline(y=y - 0.15, xmin=0.03, xmax=0.97, color="#EEEEEE", linewidth=0.5)

    y = -5.9
    draw_message(ax, 10.0, 12.8, y, "6. Invoke REQUEST Interceptor", COLORS["gateway"])
    draw_activation(ax, 12.8, -5.9, -6.9, COLORS["interceptor"])

    y = -6.4
    draw_self_message(ax, 12.8, y,
                      "7. Decode JWT payload\n     Extract: role, line_scope\n     Inject user_context",
                      COLORS["interceptor"])

    y = -7.2
    draw_message(ax, 12.8, 10.0, y, '8. Enriched request:\n    user_context = {role, scope}',
                 COLORS["interceptor"], dashed=True, fontsize=13)

    # --- Policy Phase ---
    y = -7.8
    ax.text(0.0, y, "Authorization", fontsize=15, fontweight="bold",
            color="#222222", va="center")
    ax.axhline(y=y - 0.15, xmin=0.03, xmax=0.97, color="#EEEEEE", linewidth=0.5)

    y = -8.3
    draw_message(ax, 10.0, 15.5, y,
                 '9. Evaluate: role=line_supervisor,\n    action=get_oee_trends, line="Line 7"',
                 COLORS["gateway"], fontsize=13)
    draw_activation(ax, 15.5, -8.3, -9.5, COLORS["cedar"])

    y = -9.0
    draw_note(ax, 15.5, y,
              "Cedar Evaluation:\n  permit_all → PERMIT\n  forbid_line_scope:\n    'Line 7' in ['Line 7']? YES\n    → No forbid match\n  Result: ALLOW",
              width=3.0, color="#E8F5E9")

    # --- ALT Frame ---
    alt_top = -9.8
    alt_mid = -12.2
    alt_bottom = -15.8
    draw_alt_frame(ax, 0.5, 19.5, alt_top, alt_mid, alt_bottom,
                   "ALLOW — parameter in user scope", "DENY — parameter outside scope")

    # ALLOW path
    y = -10.2
    draw_message(ax, 15.5, 10.0, y, "10a. Decision: ALLOW", COLORS["allow"], dashed=True)

    y = -10.7
    draw_message(ax, 10.0, 18.5, y, "11a. Execute Lambda tool target", COLORS["gateway"])
    draw_activation(ax, 18.5, -10.7, -11.2, COLORS["tool"])

    y = -11.3
    draw_message(ax, 18.5, 10.0, y, "12a. OEE data (Line 7, 4 weeks)", COLORS["tool"], dashed=True)

    y = -11.8
    draw_message(ax, 10.0, 7.0, y, "13a. Tool result → Agent", COLORS["gateway"], dashed=True)

    # DENY path
    y = -12.8
    draw_message(ax, 15.5, 10.0, y, '10b. Decision: DENY\n    "Line 4 not in scope"',
                 COLORS["deny"], dashed=True, fontsize=13)

    y = -13.7
    draw_note(ax, 18.5, y, "MCP Server\nNEVER\nINVOKED", width=1.6, color="#FFEBEE")

    y = -14.5
    draw_message(ax, 10.0, 7.0, y,
                 '11b. Error: "[Policy] Access denied.\n       Scope: Line 7 only"',
                 COLORS["deny"], dashed=True, fontsize=13)

    # --- Response Phase ---
    y = -16.2
    draw_self_message(ax, 7.0, y,
                      "LLM synthesizes:\n  ALLOW → data summary\n  DENY → explains scope",
                      COLORS["agent"])

    y = -17.1
    draw_message(ax, 7.0, 1.0, y, "14. Natural language response to user",
                 COLORS["agent"], dashed=True)

    # Legend — placed well below the bottom participant boxes (y_bottom = -19.2)
    legend_y = -20.5
    legend_items = [
        (1.0, "Solid arrow = synchronous call", "-"),
        (5.5, "Dashed arrow = response/return", "--"),
        (10.0, "Green box = ALLOW path", None),
        (13.0, "Red box = DENY path", None),
    ]
    for lx, ltxt, ls in legend_items:
        if ls:
            ax.annotate("", xy=(lx + 0.8, legend_y), xytext=(lx, legend_y),
                        arrowprops=dict(arrowstyle="->", color="black", lw=1.5,
                                        linestyle=ls))
            ax.text(lx + 1.0, legend_y, ltxt, fontsize=13, fontweight="bold", va="center")
        elif "Green" in ltxt:
            ax.add_patch(plt.Rectangle((lx, legend_y - 0.08), 0.3, 0.16,
                                       facecolor=COLORS["allow"], alpha=0.3))
            ax.text(lx + 0.4, legend_y, ltxt, fontsize=13, fontweight="bold", va="center")
        else:
            ax.add_patch(plt.Rectangle((lx, legend_y - 0.08), 0.3, 0.16,
                                       facecolor=COLORS["deny"], alpha=0.3))
            ax.text(lx + 0.4, legend_y, ltxt, fontsize=13, fontweight="bold", va="center")

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
    fig, axes = plt.subplots(3, 1, figsize=(20, 15))

    personas = [
        {
            "name": "Priya\n(Plant Manager)",
            "role": "plant_manager",
            "query": "Anomalies across all lines?",
            "scope": "Full Access\n(all plants/lines)",
            "result": "ALLOW",
            "detail": "Sees all 12 lines,\nprioritized by severity",
        },
        {
            "name": "Ravi\n(Line Supervisor)",
            "role": "line_supervisor",
            "query": "Show Line 4 equipment",
            "scope": "Line 7,\nPlant 2 only",
            "result": "DENY",
            "detail": "Line 4 outside scope.\nSuggests Line 7 instead.",
        },
        {
            "name": "Ankit\n(Maintenance Tech)",
            "role": "maintenance_tech",
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
        ax.set_xlim(-0.5, 20.5)
        ax.set_ylim(-2.2, 3.2)
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
            ha="center", va="bottom", fontsize=13, fontweight="bold",
            color=COLORS["gateway"], alpha=0.9,
        )

        # --- Persona label (above the row, left-aligned) ---
        ax.text(x_positions["user"] - box_w / 2, y_center + box_h / 2 + 0.45,
                persona["name"].replace("\n", "  "),
                ha="left", va="bottom",
                fontsize=14, fontweight="bold", color=COLORS["user"])

        # --- Step captions (only on first row to avoid repetition) ---
        if idx == 0:
            for cap, cx in zip(captions, caption_xs):
                ax.text(cx, y_center + box_h / 2 + 1.6, cap, ha="center", va="bottom",
                        fontsize=12.5, fontweight="bold", color="#333333")

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
                fontsize=13, fontweight="bold", color="white",
                bbox=dict(boxstyle="round,pad=0.2", facecolor=badge_color, alpha=0.9))

        # Separator line between rows (except last)
        if idx < len(personas) - 1:
            ax.axhline(y=-1.8, xmin=0.02, xmax=0.98, color="#DDDDDD", linewidth=1)

    fig.suptitle(
        "Same Agent, Same Interface — Different Data Access\n"
        "AgentCore Gateway enforces Cedar policies at the parameter level",
        fontsize=17, fontweight="bold", y=0.99,
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
            fontsize=11.5, color="#222222", linespacing=1.3)


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
