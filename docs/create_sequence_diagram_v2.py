#!/usr/bin/env python3
"""Generate improved UML sequence diagrams with LARGER fonts for readability.

Compared to the original:
- Canvas: 40x38 inches @ 200 DPI (8000x7600 px) vs original 28x26
- All fonts scaled up ~1.8x (messages: 24pt, notes: 22pt, participants: 26pt)
- Proportionally scaled spacing to prevent any overlaps
- Same content, colors, and logical flow

Output:
  docs/sequence_diagram_access_control.png
  docs/sequence_diagram_personas.png
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# Color palette
COLORS = {
    "user": "#232F3E",
    "cognito": "#B71C1C",
    "agent": "#C43E00",
    "gateway": "#1A237E",
    "interceptor": "#1B5E20",
    "cedar": "#4A148C",
    "tool": "#004D40",
    "allow": "#1B5E20",
    "deny": "#B71C1C",
    "note_bg": "#E3F2FD",
    "lifeline": "#BBBBBB",
}

# Font sizes — all significantly larger than original
F_TITLE = 36
F_SUBTITLE = 24
F_PARTICIPANT = 24
F_PARTICIPANT_BOTTOM = 20
F_MESSAGE = 22
F_NOTE = 20
F_MONO = 18
F_PHASE = 24
F_LEGEND = 22
F_ALT_GUARD = 22


def draw_participant(ax, x, y_top, y_bottom, label, color, width=2.2):
    """Draw a UML participant box + lifeline."""
    box = FancyBboxPatch(
        (x - width / 2, y_top - 0.45), width, 0.9,
        boxstyle="round,pad=0.05",
        facecolor=color, edgecolor=color, alpha=0.9,
    )
    ax.add_patch(box)
    ax.text(x, y_top, label, ha="center", va="center",
            fontsize=F_PARTICIPANT, fontweight="bold", color="white")

    box_b = FancyBboxPatch(
        (x - width / 2, y_bottom - 0.35), width, 0.7,
        boxstyle="round,pad=0.05",
        facecolor=color, edgecolor=color, alpha=0.9,
    )
    ax.add_patch(box_b)
    ax.text(x, y_bottom, label, ha="center", va="center",
            fontsize=F_PARTICIPANT_BOTTOM, fontweight="bold", color="white")

    ax.plot([x, x], [y_top - 0.4, y_bottom + 0.3],
            linestyle="--", color=COLORS["lifeline"], linewidth=1.0, zorder=0)


def draw_message(ax, x_from, x_to, y, label, color="black",
                 dashed=False, fontsize=None, offset=0.22):
    """Draw a message arrow."""
    if fontsize is None:
        fontsize = F_MESSAGE
    ls = "--" if dashed else "-"
    ax.annotate(
        "", xy=(x_to, y), xytext=(x_from, y),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=2.5, linestyle=ls),
    )
    mid_x = (x_from + x_to) / 2
    ax.text(mid_x, y + offset, label, ha="center", va="bottom",
            fontsize=fontsize, fontweight="bold", color=color,
            style="italic" if dashed else "normal")


def draw_self_message(ax, x, y, label, color="black"):
    """Draw a self-call."""
    ax.annotate(
        "", xy=(x + 0.05, y - 0.3), xytext=(x + 0.05, y),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=2.0,
                        connectionstyle="arc3,rad=-0.4"),
    )
    ax.text(x + 0.8, y - 0.15, label, ha="left", va="center",
            fontsize=F_NOTE, fontweight="bold", color=color)


def draw_note(ax, x, y, text, width=3.2, color=COLORS["note_bg"], fontsize=None):
    """Draw a UML note box."""
    if fontsize is None:
        fontsize = F_MONO
    lines = text.split("\n")
    height = 0.35 * len(lines) + 0.2
    box = FancyBboxPatch(
        (x - width / 2, y - height / 2), width, height,
        boxstyle="round,pad=0.05",
        facecolor=color, edgecolor="#666666", linewidth=1.2,
    )
    ax.add_patch(box)
    ax.text(x, y, text, ha="center", va="center",
            fontsize=fontsize, fontweight="bold", family="monospace")


def draw_activation(ax, x, y_start, y_end, color, width=0.18):
    """Draw an activation bar."""
    rect = plt.Rectangle(
        (x - width / 2, y_end), width, y_start - y_end,
        facecolor=color, alpha=0.3, edgecolor=color, linewidth=1.0,
    )
    ax.add_patch(rect)


def draw_alt_frame(ax, x_left, x_right, y_top, y_mid, y_bottom, label_if, label_else):
    """Draw a UML alt frame."""
    ax.plot([x_left, x_right, x_right, x_left, x_left],
            [y_top, y_top, y_bottom, y_bottom, y_top],
            color="#444444", linewidth=2.0)
    ax.text(x_left + 0.15, y_top - 0.1, "alt", fontsize=F_PHASE,
            fontweight="bold", color="#444444", va="top")
    ax.plot([x_left, x_right], [y_mid, y_mid],
            linestyle="--", color="#444444", linewidth=1.2)
    ax.text(x_left + 0.4, y_top - 0.35, f"[{label_if}]", fontsize=F_ALT_GUARD,
            color=COLORS["allow"], fontweight="bold")
    ax.text(x_left + 0.4, y_mid - 0.15, f"[{label_else}]", fontsize=F_ALT_GUARD,
            color=COLORS["deny"], fontweight="bold")


# ===========================================================================
# DIAGRAM 1: Main Sequence Diagram
# ===========================================================================

def create_main_sequence_diagram():
    fig, ax = plt.subplots(1, 1, figsize=(40, 38))
    ax.set_xlim(-0.5, 22.0)
    ax.set_ylim(-26.0, 2.5)
    ax.axis("off")

    # Title
    ax.text(11.0, 2.0, "AgentCore Gateway: Fine-Grained Access Control — Sequence Diagram",
            ha="center", va="center", fontsize=F_TITLE, fontweight="bold", color=COLORS["user"])
    ax.text(11.0, 1.3, "GW Policy + Custom REQUEST/RESPONSE Interceptors + Cedar Authorization",
            ha="center", va="center", fontsize=F_SUBTITLE, fontweight="bold", color="#333333")

    # Participants — wider spacing
    participants = [
        (1.0, "Ravi\n(Line Supervisor)", COLORS["user"]),
        (4.5, "Amazon\nCognito", COLORS["cognito"]),
        (8.0, "Agent\n(Strands SDK)", COLORS["agent"]),
        (11.5, "AgentCore\nGateway", COLORS["gateway"]),
        (14.8, "REQUEST\nInterceptor", COLORS["interceptor"]),
        (18.0, "Cedar Policy\nEngine", COLORS["cedar"]),
        (21.0, "MCP Tool\n(Lambda)", COLORS["tool"]),
    ]

    y_top = 0.7
    y_bottom = -23.5

    for x, label, color in participants:
        draw_participant(ax, x, y_top, y_bottom, label, color)

    # --- Authentication Phase ---
    y = -0.4
    ax.text(0.0, y, "Authentication", fontsize=F_PHASE, fontweight="bold", color="#222222", va="center")
    ax.axhline(y=y - 0.2, xmin=0.02, xmax=0.97, color="#EEEEEE", linewidth=0.5)

    y = -1.0
    draw_message(ax, 1.0, 4.5, y, "1. Login (credentials)", COLORS["user"])

    y = -1.9
    draw_message(ax, 4.5, 1.0, y, "2. JWT {role, line_scope, plant_scope}", COLORS["cognito"], dashed=True)
    draw_note(ax, 4.5, y - 0.7,
              "JWT Claims:\n  role = line_supervisor\n  line_scope = Line 7\n  plant_scope = Plant 2",
              width=3.5)

    # --- Query Phase ---
    y = -3.5
    ax.text(0.0, y, "Tool Invocation", fontsize=F_PHASE, fontweight="bold", color="#222222", va="center")
    ax.axhline(y=y - 0.2, xmin=0.02, xmax=0.97, color="#EEEEEE", linewidth=0.5)

    y = -4.2
    draw_message(ax, 1.0, 8.0, y, '3. "What\'s the OEE for Line 7?"', COLORS["user"])

    y = -5.0
    draw_self_message(ax, 8.0, y, "4. LLM reasons: need get_oee_trends(line='Line 7')", COLORS["agent"])

    y = -6.4
    draw_message(ax, 8.0, 11.5, y, '5. MCP call: get_oee_trends(line="Line 7") + Bearer <JWT>',
                 COLORS["agent"], fontsize=F_NOTE)

    # Activation on gateway
    draw_activation(ax, 11.5, -6.4, -9.5, COLORS["gateway"])

    # --- Interceptor Phase ---
    y = -6.9
    ax.text(0.0, y, "Enrichment", fontsize=F_PHASE, fontweight="bold", color="#222222", va="center")
    ax.axhline(y=y - 0.2, xmin=0.02, xmax=0.97, color="#EEEEEE", linewidth=0.5)

    y = -7.6
    draw_message(ax, 11.5, 14.8, y, "6. Invoke REQUEST Interceptor", COLORS["gateway"])
    draw_activation(ax, 14.8, -7.6, -8.9, COLORS["interceptor"])

    y = -8.3
    draw_self_message(ax, 14.8, y,
                      "7. Decode JWT payload\n     Extract: role, line_scope\n     Inject user_context",
                      COLORS["interceptor"])

    y = -9.2
    draw_message(ax, 14.8, 11.5, y, '8. Enriched request: user_context = {role, scope}',
                 COLORS["interceptor"], dashed=True)

    # --- Policy Phase ---
    y = -9.8
    ax.text(0.0, y, "Authorization", fontsize=F_PHASE, fontweight="bold", color="#222222", va="center")
    ax.axhline(y=y - 0.2, xmin=0.02, xmax=0.97, color="#EEEEEE", linewidth=0.5)

    y = -10.5
    draw_message(ax, 11.5, 18.0, y,
                 '9. Evaluate: role=line_supervisor, action=get_oee_trends, line="Line 7"',
                 COLORS["gateway"], fontsize=F_NOTE)
    draw_activation(ax, 18.0, -10.5, -11.9, COLORS["cedar"])

    y = -11.3
    draw_note(ax, 18.0, y,
              "Cedar Evaluation:\n  permit_all → PERMIT\n  forbid_line_scope:\n    'Line 7' in ['Line 7']? YES\n    → No forbid match\n  Result: ALLOW",
              width=3.8, color="#E8F5E9")

    # --- ALT Frame ---
    alt_top = -12.3
    alt_mid = -15.5
    alt_bottom = -20.0
    draw_alt_frame(ax, 0.5, 21.5, alt_top, alt_mid, alt_bottom,
                   "ALLOW — parameter in user scope", "DENY — parameter outside scope")

    # ALLOW path
    y = -12.8
    draw_message(ax, 18.0, 11.5, y, "10a. Decision: ALLOW", COLORS["allow"], dashed=True)

    y = -13.5
    draw_message(ax, 11.5, 21.0, y, "11a. Execute Lambda tool target", COLORS["gateway"])
    draw_activation(ax, 21.0, -13.5, -14.1, COLORS["tool"])

    y = -14.3
    draw_message(ax, 21.0, 11.5, y, "12a. OEE data (Line 7, 4 weeks)", COLORS["tool"], dashed=True)

    y = -15.0
    draw_message(ax, 11.5, 8.0, y, "13a. Tool result → Agent", COLORS["gateway"], dashed=True)

    # DENY path
    y = -16.2
    draw_message(ax, 18.0, 11.5, y, '10b. Decision: DENY — "Line 4 not in scope"',
                 COLORS["deny"], dashed=True, fontsize=F_NOTE)

    y = -17.2
    draw_note(ax, 21.0, y, "MCP Server\nNEVER\nINVOKED", width=2.0, color="#FFEBEE")

    y = -18.3
    draw_message(ax, 11.5, 8.0, y,
                 '11b. Error: "[Policy] Access denied. Scope: Line 7 only"',
                 COLORS["deny"], dashed=True, fontsize=F_NOTE)

    # --- Response Phase ---
    y = -20.5
    draw_self_message(ax, 8.0, y,
                      "LLM synthesizes:\n  ALLOW → data summary\n  DENY → explains scope",
                      COLORS["agent"])

    y = -21.6
    draw_message(ax, 8.0, 1.0, y, "14. Natural language response to user",
                 COLORS["agent"], dashed=True)

    # Legend
    legend_y = -24.5
    legend_items = [
        (1.0, "Solid arrow = synchronous call", "-"),
        (6.5, "Dashed arrow = response/return", "--"),
        (12.0, "Green = ALLOW path", None),
        (15.5, "Red = DENY path", None),
    ]
    for lx, ltxt, ls in legend_items:
        if ls:
            ax.annotate("", xy=(lx + 1.0, legend_y), xytext=(lx, legend_y),
                        arrowprops=dict(arrowstyle="->", color="black", lw=1.8, linestyle=ls))
            ax.text(lx + 1.2, legend_y, ltxt, fontsize=F_LEGEND, fontweight="bold", va="center")
        elif "Green" in ltxt:
            ax.add_patch(plt.Rectangle((lx, legend_y - 0.1), 0.4, 0.2,
                                       facecolor=COLORS["allow"], alpha=0.3))
            ax.text(lx + 0.55, legend_y, ltxt, fontsize=F_LEGEND, fontweight="bold", va="center")
        else:
            ax.add_patch(plt.Rectangle((lx, legend_y - 0.1), 0.4, 0.2,
                                       facecolor=COLORS["deny"], alpha=0.3))
            ax.text(lx + 0.55, legend_y, ltxt, fontsize=F_LEGEND, fontweight="bold", va="center")

    plt.tight_layout()
    return fig


# ===========================================================================
# DIAGRAM 2: Three Personas
# ===========================================================================

def create_personas_diagram():
    fig, axes = plt.subplots(3, 1, figsize=(28, 22))

    personas = [
        {
            "name": "Priya (Plant Manager)",
            "role": "plant_manager",
            "query": "Anomalies across all lines?",
            "scope": "Full Access\n(all plants/lines)",
            "result": "ALLOW",
            "detail": "Sees all 12 lines,\nprioritized by severity",
        },
        {
            "name": "Ravi (Line Supervisor)",
            "role": "line_supervisor",
            "query": "Show Line 4 equipment",
            "scope": "Line 7,\nPlant 2 only",
            "result": "DENY",
            "detail": "Line 4 outside scope.\nSuggests Line 7 instead.",
        },
        {
            "name": "Ankit (Maintenance Tech)",
            "role": "maintenance_tech",
            "query": "Machine 72 vibration?",
            "scope": "Machines 41-45\nonly",
            "result": "DENY",
            "detail": "Machine 72 not assigned.\nSuggests Machine 42.",
        },
    ]

    x_positions = {
        "user": 1.5,
        "agent": 5.0,
        "gateway": 9.0,
        "cedar": 13.0,
        "tool": 16.5,
        "response": 20.0,
    }
    captions = ["User Query", "Strands Agent", "AgentCore\nGateway", "Cedar Policy\nEngine", "MCP Tool\n(Lambda)", "Agent Response"]
    caption_xs = [x_positions["user"], x_positions["agent"], x_positions["gateway"],
                  x_positions["cedar"], x_positions["tool"], x_positions["response"]]

    box_w = 3.0
    box_h = 1.8
    y_center = 0.0

    for idx, (ax, persona) in enumerate(zip(axes, personas)):
        ax.set_xlim(-0.5, 22.5)
        ax.set_ylim(-2.8, 3.8)
        ax.axis("off")

        # AgentCore region
        ac_x_start = x_positions["gateway"] - box_w / 2 - 0.5
        ac_x_end = x_positions["cedar"] + box_w / 2 + 0.5
        ac_region = FancyBboxPatch(
            (ac_x_start, y_center - box_h / 2 - 0.6),
            ac_x_end - ac_x_start, box_h + 1.2,
            boxstyle="round,pad=0.15",
            facecolor="#EDE7F6", edgecolor=COLORS["gateway"], linewidth=2.0,
            linestyle="-", alpha=0.5,
        )
        ax.add_patch(ac_region)
        ax.text(
            (x_positions["gateway"] + x_positions["cedar"]) / 2,
            y_center + box_h / 2 + 0.8,
            "Amazon Bedrock AgentCore",
            ha="center", va="bottom", fontsize=18, fontweight="bold",
            color=COLORS["gateway"], alpha=0.9,
        )

        # Persona label
        ax.text(x_positions["user"] - box_w / 2, y_center + box_h / 2 + 0.6,
                persona["name"].replace("\n", "  "),
                ha="left", va="bottom",
                fontsize=22, fontweight="bold", color=COLORS["user"])

        # Column captions (first row only)
        if idx == 0:
            for cap, cx in zip(captions, caption_xs):
                ax.text(cx, y_center + box_h / 2 + 2.0, cap, ha="center", va="bottom",
                        fontsize=18, fontweight="bold", color="#333333")

        # Step boxes
        box_data = [
            ("user", f'"{persona["query"]}"', "#E3F2FD", "#1565C0"),
            ("agent", "LLM reasons →\nselects MCP tool", "#FFF3E0", COLORS["agent"]),
            ("gateway", "REQUEST Interceptor\n+ JWT extraction", "#E8EAF6", COLORS["gateway"]),
            ("cedar", f"Cedar scope:\n{persona['scope']}", "#F3E5F5", COLORS["cedar"]),
        ]

        if persona["result"] == "ALLOW":
            box_data.append(("tool", "Lambda executes\n✓ Returns data", "#E8F5E9", COLORS["allow"]))
            box_data.append(("response", persona["detail"], "#E8F5E9", COLORS["allow"]))
        else:
            box_data.append(("tool", "Lambda NOT\ninvoked ✗", "#FFEBEE", COLORS["deny"]))
            box_data.append(("response", persona["detail"], "#FFEBEE", COLORS["deny"]))

        for key, text, fcolor, ecolor in box_data:
            cx = x_positions[key]
            box = FancyBboxPatch(
                (cx - box_w / 2, y_center - box_h / 2), box_w, box_h,
                boxstyle="round,pad=0.1",
                facecolor=fcolor, edgecolor=ecolor, linewidth=1.5,
            )
            ax.add_patch(box)
            ax.text(cx, y_center, text, ha="center", va="center",
                    fontsize=16, color="#222222", linespacing=1.3)

        # Arrows
        keys = ["user", "agent", "gateway", "cedar", "tool", "response"]
        for i in range(len(keys) - 1):
            x_from = x_positions[keys[i]] + box_w / 2 + 0.05
            x_to = x_positions[keys[i + 1]] - box_w / 2 - 0.05
            if keys[i + 1] in ("tool", "response") or keys[i] == "tool":
                arr_color = COLORS["allow"] if persona["result"] == "ALLOW" else COLORS["deny"]
            else:
                arr_color = "#333333"
            ax.annotate(
                "", xy=(x_to, y_center), xytext=(x_from, y_center),
                arrowprops=dict(arrowstyle="-|>", color=arr_color, lw=2.0,
                                shrinkA=2, shrinkB=2),
            )

        # Decision badge
        badge_x = (x_positions["cedar"] + x_positions["tool"]) / 2
        badge_color = COLORS["allow"] if persona["result"] == "ALLOW" else COLORS["deny"]
        ax.text(badge_x, y_center + 0.45, persona["result"], ha="center", va="bottom",
                fontsize=18, fontweight="bold", color="white",
                bbox=dict(boxstyle="round,pad=0.25", facecolor=badge_color, alpha=0.9))

        # Separator
        if idx < len(personas) - 1:
            ax.axhline(y=-2.3, xmin=0.02, xmax=0.98, color="#DDDDDD", linewidth=1)

    fig.suptitle(
        "Same Agent, Same Interface — Different Data Access\n"
        "AgentCore Gateway enforces Cedar policies at the parameter level",
        fontsize=26, fontweight="bold", y=0.99,
    )
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    return fig


# ===========================================================================
# Main
# ===========================================================================

if __name__ == "__main__":
    # Diagram 1
    fig1 = create_main_sequence_diagram()
    path1 = os.path.join(OUTPUT_DIR, "sequence_diagram_access_control.png")
    fig1.savefig(path1, dpi=200, bbox_inches="tight", facecolor="white")
    print(f"Saved: {path1}")
    plt.close(fig1)

    # Diagram 2
    fig2 = create_personas_diagram()
    path2 = os.path.join(OUTPUT_DIR, "sequence_diagram_personas.png")
    fig2.savefig(path2, dpi=200, bbox_inches="tight", facecolor="white")
    print(f"Saved: {path2}")
    plt.close(fig2)

    print(f"\nFont sizes: Title={F_TITLE}pt, Messages={F_MESSAGE}pt, Notes={F_NOTE}pt, Participants={F_PARTICIPANT}pt")
    print("Canvas: 40x38 in (sequence), 28x22 in (personas) @ 200 DPI")
