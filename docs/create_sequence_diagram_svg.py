# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

#!/usr/bin/env python3
"""Generate SVG sequence diagrams for AgentCore Gateway access control flow.

Produces two SVG files with very large fonts to remain readable on GitLab:
  1. sequence_diagram_access_control.svg — full UML sequence diagram
  2. sequence_diagram_personas.svg — three personas comparison

Strategy: Wide canvas (2200+) with generous spacing (same layout as original
matplotlib version) but all fonts 40-64px so they remain readable even when
GitLab scales the SVG down to ~800px page width.

Pure inline SVG — no <style>, no <defs>, no url() references.
"""

import os
import math

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


# =============================================================================
# SVG UTILITIES
# =============================================================================

def svg_header(width, height):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
<rect width="{width}" height="{height}" fill="white"/>
'''


def rrect(x, y, w, h, fill, stroke, stroke_width=3, rx=12):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'


def txt(x, y, content, size, color, bold=False, italic=False, anchor="middle", mono=False):
    weight = ' font-weight="bold"' if bold else ''
    style = ' font-style="italic"' if italic else ''
    family = "Courier New, monospace" if mono else "Segoe UI, Helvetica, Arial, sans-serif"
    content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
    return f'<text x="{x}" y="{y}" font-size="{size}" font-family="{family}"{weight}{style} fill="{color}" text-anchor="{anchor}" dominant-baseline="middle">{content}</text>'


def arrow(x1, y1, x2, y2, color="#333333", width=3.5, dashed=False):
    """Line with inline polygon arrowhead."""
    dash = ' stroke-dasharray="12,7"' if dashed else ''
    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx*dx + dy*dy)
    if length == 0:
        return ''
    ux, uy = dx / length, dy / length
    arrow_len, arrow_width = 16, 9
    bx = x2 - ux * arrow_len
    by = y2 - uy * arrow_len
    px, py = -uy * arrow_width, ux * arrow_width
    p1 = f"{x2},{y2}"
    p2 = f"{bx + px},{by + py}"
    p3 = f"{bx - px},{by - py}"
    lx2 = x2 - ux * arrow_len * 0.5
    ly2 = y2 - uy * arrow_len * 0.5
    return (f'<line x1="{x1}" y1="{y1}" x2="{lx2}" y2="{ly2}" '
            f'stroke="{color}" stroke-width="{width}"{dash}/>\n'
            f'<polygon points="{p1} {p2} {p3}" fill="{color}"/>')


def lifeline(x, y1, y2):
    return f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" stroke="#CCCCCC" stroke-width="2" stroke-dasharray="8,5"/>'


# =============================================================================
# DIAGRAM 1: SEQUENCE DIAGRAM — ACCESS CONTROL
# Wide canvas, generous spacing, very large fonts
# =============================================================================

def create_sequence_diagram_svg():
    W = 2400
    H = 5400
    elements = [svg_header(W, H)]

    # Colors
    C_USER = "#232F3E"
    C_COGNITO = "#B71C1C"
    C_AGENT = "#C43E00"
    C_GATEWAY = "#1A237E"
    C_INTERCEPTOR = "#1B5E20"
    C_CEDAR = "#4A148C"
    C_TOOL = "#004D40"
    C_ALLOW = "#1B5E20"
    C_DENY = "#B71C1C"

    # Font sizes — very large for GitLab readability after scaling
    F_TITLE = 64
    F_SUBTITLE = 40
    F_PHASE = 44
    F_MSG = 38
    F_NOTE = 36
    F_NOTE_MONO = 32
    F_PARTICIPANT = 36
    F_PARTICIPANT_SUB = 30

    # Title
    elements.append(txt(W//2, 70, "AgentCore Gateway: Fine-Grained Access Control", F_TITLE, C_USER, bold=True))
    elements.append(txt(W//2, 130, "REQUEST/RESPONSE Interceptors + Cedar Authorization", F_SUBTITLE, "#444444"))

    # Participants
    participants = [
        (200, "Ravi", "(Line Supervisor)", C_USER),
        (560, "Amazon Cognito", "(IdP)", C_COGNITO),
        (950, "Agent", "(Strands SDK)", C_AGENT),
        (1400, "AgentCore", "Gateway", C_GATEWAY),
        (1800, "Cedar Policy", "Engine", C_CEDAR),
        (2180, "MCP Tool", "(Lambda)", C_TOOL),
    ]

    header_y = 190
    header_h = 100
    lifeline_bottom = 5150

    for px, label1, label2, color in participants:
        elements.append(rrect(px - 120, header_y, 240, header_h, color, color, rx=10))
        elements.append(txt(px, header_y + 38, label1, F_PARTICIPANT, "white", bold=True))
        elements.append(txt(px, header_y + 72, label2, F_PARTICIPANT_SUB, "white"))
        elements.append(lifeline(px, header_y + header_h, lifeline_bottom))
        elements.append(rrect(px - 120, lifeline_bottom, 240, header_h, color, color, rx=10))
        elements.append(txt(px, lifeline_bottom + 38, label1, F_PARTICIPANT, "white", bold=True))
        elements.append(txt(px, lifeline_bottom + 72, label2, F_PARTICIPANT_SUB, "white"))

    # ---- AUTHENTICATION ----
    y = 380
    elements.append(txt(80, y, "Authentication", F_PHASE, "#222222", bold=True, anchor="start"))
    elements.append(f'<line x1="80" y1="{y+20}" x2="2350" y2="{y+20}" stroke="#EEEEEE" stroke-width="2"/>')

    y = 460
    elements.append(arrow(200, y, 560, y, C_USER))
    elements.append(txt(380, y - 30, "1. Login (credentials)", F_MSG, C_USER))

    y = 580
    elements.append(arrow(560, y, 200, y, C_COGNITO, dashed=True))
    elements.append(txt(380, y - 30, "2. JWT token returned", F_MSG, C_COGNITO, italic=True))

    # JWT note
    ny = y + 50
    elements.append(rrect(360, ny, 400, 170, "#E3F2FD", C_COGNITO, stroke_width=2, rx=10))
    elements.append(txt(560, ny + 35, "JWT Claims:", F_NOTE, C_COGNITO, bold=True))
    elements.append(txt(560, ny + 75, "role = line_supervisor", F_NOTE_MONO, C_COGNITO, mono=True))
    elements.append(txt(560, ny + 110, "line_scope = Line 7", F_NOTE_MONO, C_COGNITO, mono=True))
    elements.append(txt(560, ny + 145, "plant_scope = Plant 2", F_NOTE_MONO, C_COGNITO, mono=True))

    # ---- TOOL INVOCATION ----
    y = 890
    elements.append(txt(80, y, "Tool Invocation", F_PHASE, "#222222", bold=True, anchor="start"))
    elements.append(f'<line x1="80" y1="{y+20}" x2="2350" y2="{y+20}" stroke="#EEEEEE" stroke-width="2"/>')

    y = 980
    elements.append(arrow(200, y, 950, y, C_USER))
    elements.append(txt(575, y - 30, '3. "What is the OEE for Line 7?"', F_MSG, C_USER))

    y = 1100
    elements.append(rrect(720, y - 35, 460, 80, "#FFF3E0", C_AGENT, stroke_width=2, rx=10))
    elements.append(txt(950, y + 5, "4. LLM: get_oee_trends(Line 7)", F_NOTE, C_AGENT))

    y = 1240
    elements.append(arrow(950, y, 1400, y, C_AGENT))
    elements.append(txt(1175, y - 30, "5. MCP call + Bearer JWT", F_MSG, C_AGENT))

    # Activation on gateway
    elements.append(rrect(1388, y + 10, 24, 700, C_GATEWAY, C_GATEWAY, stroke_width=0, rx=4))

    # ---- ENRICHMENT ----
    y = 1370
    elements.append(txt(80, y, "Enrichment (REQUEST Interceptor)", F_PHASE, "#222222", bold=True, anchor="start"))
    elements.append(f'<line x1="80" y1="{y+20}" x2="2350" y2="{y+20}" stroke="#EEEEEE" stroke-width="2"/>')

    y = 1470
    elements.append(rrect(1150, y - 35, 500, 140, "#E8F5E9", C_INTERCEPTOR, stroke_width=2, rx=10))
    elements.append(txt(1400, y, "6. Decode JWT payload", F_NOTE, C_INTERCEPTOR, bold=True))
    elements.append(txt(1400, y + 40, "7. Extract role + line_scope", F_NOTE, C_INTERCEPTOR))
    elements.append(txt(1400, y + 78, "8. Inject user_context into args", F_NOTE, C_INTERCEPTOR))

    # ---- AUTHORIZATION ----
    y = 1710
    elements.append(txt(80, y, "Authorization (Cedar)", F_PHASE, "#222222", bold=True, anchor="start"))
    elements.append(f'<line x1="80" y1="{y+20}" x2="2350" y2="{y+20}" stroke="#EEEEEE" stroke-width="2"/>')

    y = 1810
    elements.append(arrow(1400, y, 1800, y, C_GATEWAY))
    elements.append(txt(1600, y - 30, "9. Evaluate policy", F_MSG, C_GATEWAY))

    # Activation on cedar
    elements.append(rrect(1788, y + 10, 24, 300, C_CEDAR, C_CEDAR, stroke_width=0, rx=4))

    # Cedar note
    ny = y + 60
    elements.append(rrect(1560, ny, 480, 220, "#F3E5F5", C_CEDAR, stroke_width=2, rx=10))
    elements.append(txt(1800, ny + 35, "Cedar Evaluation:", F_NOTE, C_CEDAR, bold=True))
    elements.append(txt(1800, ny + 78, "permit_all -> PERMIT", F_NOTE_MONO, C_CEDAR, mono=True))
    elements.append(txt(1800, ny + 118, "forbid_line_scope:", F_NOTE_MONO, C_CEDAR, mono=True))
    elements.append(txt(1800, ny + 155, "'Line 7' in ['Line 7']? YES", F_NOTE_MONO, C_CEDAR, mono=True))
    elements.append(txt(1800, ny + 195, "Result: ALLOW", F_NOTE, C_ALLOW, bold=True))

    # ---- ALT FRAME ----
    alt_top = 2250
    alt_mid = 3400
    alt_bottom = 4400

    elements.append(f'<rect x="80" y="{alt_top}" width="2260" height="{alt_bottom - alt_top}" fill="none" stroke="#555555" stroke-width="3" rx="10"/>')
    elements.append(txt(130, alt_top + 45, "alt", F_PHASE, "#444444", bold=True, anchor="start"))
    elements.append(f'<line x1="80" y1="{alt_mid}" x2="2340" y2="{alt_mid}" stroke="#555555" stroke-width="2.5" stroke-dasharray="12,6"/>')
    elements.append(txt(200, alt_top + 100, "[ALLOW - parameter in user scope]", F_MSG, C_ALLOW, bold=True, anchor="start"))
    elements.append(txt(200, alt_mid + 55, "[DENY - parameter outside scope]", F_MSG, C_DENY, bold=True, anchor="start"))

    # --- ALLOW PATH ---
    y = 2430
    elements.append(arrow(1800, y, 1400, y, C_ALLOW, dashed=True))
    elements.append(txt(1600, y - 30, "10a. Decision: ALLOW", F_MSG, C_ALLOW, bold=True))

    y = 2580
    elements.append(arrow(1400, y, 2180, y, C_GATEWAY))
    elements.append(txt(1790, y - 30, "11a. Execute Lambda", F_MSG, C_GATEWAY))

    # Tool activation
    elements.append(rrect(2168, y + 10, 24, 120, C_TOOL, C_TOOL, stroke_width=0, rx=4))

    y = 2730
    elements.append(arrow(2180, y, 1400, y, C_TOOL, dashed=True))
    elements.append(txt(1790, y - 30, "12a. OEE data (Line 7)", F_MSG, C_TOOL, italic=True))

    y = 2890
    elements.append(arrow(1400, y, 950, y, C_GATEWAY, dashed=True))
    elements.append(txt(1175, y - 30, "13a. Tool result", F_MSG, C_GATEWAY, italic=True))

    y = 3050
    elements.append(arrow(950, y, 200, y, C_AGENT, dashed=True))
    elements.append(txt(575, y - 30, "14a. Data summary to user", F_MSG, C_AGENT, italic=True))

    # --- DENY PATH ---
    y = 3530
    elements.append(arrow(1800, y, 1400, y, C_DENY, dashed=True))
    elements.append(txt(1600, y - 30, "10b. Decision: DENY", F_MSG, C_DENY, bold=True))

    # MCP never invoked
    elements.append(rrect(2020, y + 30, 320, 100, "#FFEBEE", C_DENY, stroke_width=3, rx=10))
    elements.append(txt(2180, y + 60, "MCP Server", F_NOTE, C_DENY, bold=True))
    elements.append(txt(2180, y + 98, "NEVER INVOKED", F_NOTE, C_DENY, bold=True))

    y = 3720
    elements.append(arrow(1400, y, 950, y, C_DENY, dashed=True))
    elements.append(txt(1175, y - 30, "11b. Access denied", F_MSG, C_DENY, italic=True))

    y = 3880
    elements.append(rrect(720, y - 35, 460, 80, "#FFEBEE", C_DENY, stroke_width=2, rx=10))
    elements.append(txt(950, y + 5, '"Line 4 not in scope: Line 7 only"', F_NOTE, C_DENY))

    y = 4050
    elements.append(arrow(950, y, 200, y, C_DENY, dashed=True))
    elements.append(txt(575, y - 30, "12b. Scope limit explained", F_MSG, C_DENY, italic=True))

    # --- RESPONSE PHASE ---
    y = 4520
    elements.append(txt(80, y, "Response", F_PHASE, "#222222", bold=True, anchor="start"))
    elements.append(f'<line x1="80" y1="{y+20}" x2="2350" y2="{y+20}" stroke="#EEEEEE" stroke-width="2"/>')

    y = 4620
    elements.append(rrect(700, y - 40, 500, 140, "#FFF3E0", C_AGENT, stroke_width=2, rx=10))
    elements.append(txt(950, y, "LLM synthesizes:", F_NOTE, C_AGENT, bold=True))
    elements.append(txt(950, y + 42, "ALLOW -> data summary", F_NOTE, C_ALLOW))
    elements.append(txt(950, y + 82, "DENY -> scope guidance", F_NOTE, C_DENY))

    y = 4850
    elements.append(arrow(950, y, 200, y, C_AGENT, dashed=True))
    elements.append(txt(575, y - 30, "Natural language response to user", F_MSG, C_AGENT, italic=True))

    # --- Legend ---
    y = 5020
    elements.append(txt(150, y, "Legend:", F_MSG, "#333333", bold=True, anchor="start"))
    elements.append(arrow(350, y, 480, y, "#333333"))
    elements.append(txt(510, y, "Call", F_NOTE, "#333333", anchor="start"))
    elements.append(arrow(660, y, 790, y, "#333333", dashed=True))
    elements.append(txt(820, y, "Return", F_NOTE, "#333333", anchor="start"))
    elements.append(rrect(1020, y - 16, 32, 32, C_ALLOW, C_ALLOW, rx=5))
    elements.append(txt(1070, y, "ALLOW", F_NOTE, C_ALLOW, anchor="start", bold=True))
    elements.append(rrect(1280, y - 16, 32, 32, C_DENY, C_DENY, rx=5))
    elements.append(txt(1330, y, "DENY", F_NOTE, C_DENY, anchor="start", bold=True))

    elements.append('</svg>')
    return '\n'.join(elements)


# =============================================================================
# DIAGRAM 2: THREE PERSONAS COMPARISON
# Wide canvas, big fonts, generous row spacing
# =============================================================================

def create_personas_diagram_svg():
    W = 2200
    H = 2400
    elements = [svg_header(W, H)]

    # Colors
    C_USER = "#232F3E"
    C_AGENT = "#C43E00"
    C_GATEWAY = "#1A237E"
    C_CEDAR = "#4A148C"
    C_ALLOW = "#1B5E20"
    C_DENY = "#B71C1C"

    # Font sizes — large
    F_TITLE = 56
    F_SUBTITLE = 34
    F_HEADER = 36
    F_NAME = 40
    F_BOX = 30
    F_BADGE = 34

    # Title
    elements.append(txt(W//2, 65, "Same Agent, Same Interface - Different Data Access", F_TITLE, C_USER, bold=True))
    elements.append(txt(W//2, 125, "AgentCore Gateway enforces Cedar policies at parameter level", F_SUBTITLE, "#555555"))

    # Column headers
    cols = [
        (200, "User Query"),
        (560, "Strands Agent"),
        (940, "AgentCore GW"),
        (1340, "Cedar Policy"),
        (1740, "Outcome"),
    ]

    for cx, label in cols:
        elements.append(txt(cx, 200, label, F_HEADER, "#333333", bold=True))

    # Personas
    personas = [
        {
            "name": "Priya (Plant Manager)",
            "query_l1": "Anomalies across",
            "query_l2": "all lines?",
            "cedar_l1": "Full Access",
            "cedar_l2": "(all plants/lines)",
            "result": "ALLOW",
            "resp_l1": "All 12 lines shown,",
            "resp_l2": "by severity",
        },
        {
            "name": "Ravi (Line Supervisor)",
            "query_l1": "Show Line 4",
            "query_l2": "equipment",
            "cedar_l1": "Line 7,",
            "cedar_l2": "Plant 2 only",
            "result": "DENY",
            "resp_l1": "Line 4 blocked.",
            "resp_l2": "Suggests Line 7.",
        },
        {
            "name": "Ankit (Maintenance Tech)",
            "query_l1": "Machine 72",
            "query_l2": "vibration?",
            "cedar_l1": "Machines 41-45",
            "cedar_l2": "only",
            "result": "DENY",
            "resp_l1": "Machine 72 blocked.",
            "resp_l2": "Suggests Machine 42.",
        },
    ]

    box_w = 300
    box_h = 130
    row_height = 650
    start_y = 280

    for idx, persona in enumerate(personas):
        row_y = start_y + idx * row_height
        is_allow = persona["result"] == "ALLOW"
        result_color = C_ALLOW if is_allow else C_DENY
        result_bg = "#E8F5E9" if is_allow else "#FFEBEE"

        # Persona name
        elements.append(txt(W//2, row_y, persona["name"], F_NAME, C_USER, bold=True))

        # AgentCore region highlight
        elements.append(rrect(720, row_y + 40, 780, box_h + 40, "#EDE7F6", C_GATEWAY, stroke_width=2, rx=12))
        elements.append(txt(1110, row_y + 58, "Amazon Bedrock AgentCore", 24, C_GATEWAY, italic=True))

        by = row_y + 115  # box center y

        # Step boxes
        steps = [
            (200, persona["query_l1"], persona["query_l2"], "#E3F2FD", "#1565C0"),
            (560, "LLM selects", "MCP tool", "#FFF3E0", C_AGENT),
            (940, "Interceptor +", "JWT check", "#E8EAF6", C_GATEWAY),
            (1340, persona["cedar_l1"], persona["cedar_l2"], "#F3E5F5", C_CEDAR),
            (1740, persona["resp_l1"], persona["resp_l2"], result_bg, result_color),
        ]

        for sx, l1, l2, sfill, sstroke in steps:
            elements.append(rrect(sx - box_w//2, by - box_h//2, box_w, box_h, sfill, sstroke, stroke_width=3, rx=10))
            elements.append(txt(sx, by - 20, l1, F_BOX, "#222222"))
            elements.append(txt(sx, by + 20, l2, F_BOX, "#222222"))

        # Arrows between boxes
        arrow_xs = [200, 560, 940, 1340, 1740]
        for i in range(len(arrow_xs) - 1):
            x1 = arrow_xs[i] + box_w // 2 + 8
            x2 = arrow_xs[i + 1] - box_w // 2 - 8
            color = result_color if i >= 3 else "#333333"
            elements.append(arrow(x1, by, x2, by, color, width=3))

        # Decision badge
        badge_x = (1340 + 1740) // 2
        elements.append(rrect(badge_x - 65, by - 55, 130, 44, result_color, result_color, rx=16))
        elements.append(txt(badge_x, by - 32, persona["result"], F_BADGE, "white", bold=True))

        # Separator
        if idx < len(personas) - 1:
            sep_y = row_y + row_height - 80
            elements.append(f'<line x1="100" y1="{sep_y}" x2="2100" y2="{sep_y}" stroke="#DDDDDD" stroke-width="2"/>')

    elements.append('</svg>')
    return '\n'.join(elements)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    svg1 = create_sequence_diagram_svg()
    path1 = os.path.join(OUTPUT_DIR, "sequence_diagram_access_control.svg")
    with open(path1, 'w', encoding='utf-8') as f:
        f.write(svg1)
    print(f"Saved: {path1}")

    svg2 = create_personas_diagram_svg()
    path2 = os.path.join(OUTPUT_DIR, "sequence_diagram_personas.svg")
    with open(path2, 'w', encoding='utf-8') as f:
        f.write(svg2)
    print(f"Saved: {path2}")

    print("\nDone! Wide canvas + very large fonts for GitLab readability.")
