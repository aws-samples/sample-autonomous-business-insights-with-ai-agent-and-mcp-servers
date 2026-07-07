#!/usr/bin/env python3
"""Generate SVG sequence diagrams for AgentCore Gateway access control flow.

Produces two SVG files optimized for GitLab README rendering:
  1. sequence_diagram_access_control.svg — full UML sequence diagram
  2. sequence_diagram_personas.svg — three personas comparison

Design for GitLab: viewBox kept narrow (1400-1600px wide) so when GitLab scales
to page width (~800px), text remains large and readable. All fonts >= 28px
in source so they render ~14px+ on screen.

Pure SVG with inline styles only — no <style>, no <defs>, no url() references.
"""

import os
import math

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


# =============================================================================
# SHARED SVG UTILITIES
# =============================================================================

def svg_header(width, height):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
<rect width="{width}" height="{height}" fill="white"/>
'''


def rrect(x, y, w, h, fill, stroke, stroke_width=2, rx=10):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'


def txt(x, y, content, size, color, bold=False, italic=False, anchor="middle", mono=False):
    weight = ' font-weight="bold"' if bold else ''
    style = ' font-style="italic"' if italic else ''
    family = "Courier New, monospace" if mono else "Segoe UI, Helvetica, Arial, sans-serif"
    content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
    return f'<text x="{x}" y="{y}" font-size="{size}" font-family="{family}"{weight}{style} fill="{color}" text-anchor="{anchor}" dominant-baseline="middle">{content}</text>'


def arrow(x1, y1, x2, y2, color="#333333", width=3, dashed=False):
    """Draw a line with an arrowhead polygon at the end."""
    dash = ' stroke-dasharray="10,6"' if dashed else ''
    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx*dx + dy*dy)
    if length == 0:
        return ''
    ux = dx / length
    uy = dy / length
    arrow_len = 14
    arrow_width = 7
    bx = x2 - ux * arrow_len
    by = y2 - uy * arrow_len
    px = -uy * arrow_width
    py = ux * arrow_width
    p1 = f"{x2},{y2}"
    p2 = f"{bx + px},{by + py}"
    p3 = f"{bx - px},{by - py}"
    lx2 = x2 - ux * arrow_len * 0.5
    ly2 = y2 - uy * arrow_len * 0.5

    return (f'<line x1="{x1}" y1="{y1}" x2="{lx2}" y2="{ly2}" '
            f'stroke="{color}" stroke-width="{width}"{dash}/>\n'
            f'<polygon points="{p1} {p2} {p3}" fill="{color}"/>')


def lifeline(x, y1, y2, color="#CCCCCC"):
    return f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" stroke="{color}" stroke-width="2" stroke-dasharray="8,5"/>'


def sep_line(y, x1=50, x2=1350):
    return f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="#EEEEEE" stroke-width="1.5"/>'


# =============================================================================
# DIAGRAM 1: SEQUENCE DIAGRAM — ACCESS CONTROL
# Narrower layout (1400 wide) with bigger fonts for GitLab readability
# =============================================================================

def create_sequence_diagram_svg():
    W = 1400
    H = 4200
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

    # Font sizes — large for GitLab scaling
    F_TITLE = 52
    F_SUBTITLE = 30
    F_PHASE = 32
    F_MSG = 28
    F_NOTE = 26
    F_PARTICIPANT = 28
    F_PARTICIPANT_SUB = 24

    # Title
    elements.append(txt(W//2, 60, "AgentCore Gateway: Access Control", F_TITLE, C_USER, bold=True))
    elements.append(txt(W//2, 110, "REQUEST/RESPONSE Interceptors + Cedar Authorization", F_SUBTITLE, "#444444"))

    # Participants — 5 columns (merged Interceptor into Gateway conceptually for narrower layout)
    participants = [
        (120, "User", "(Ravi)", C_USER),
        (360, "Cognito", "(IdP)", C_COGNITO),
        (600, "Agent", "(Strands)", C_AGENT),
        (880, "Gateway", "(AgentCore)", C_GATEWAY),
        (1150, "Cedar", "(Policy)", C_CEDAR),
    ]

    header_y = 160
    header_h = 85
    lifeline_bottom = 3980

    for px, label1, label2, color in participants:
        elements.append(rrect(px - 80, header_y, 160, header_h, color, color, rx=8))
        elements.append(txt(px, header_y + 30, label1, F_PARTICIPANT, "white", bold=True))
        elements.append(txt(px, header_y + 60, label2, F_PARTICIPANT_SUB, "white"))
        elements.append(lifeline(px, header_y + header_h, lifeline_bottom))
        elements.append(rrect(px - 80, lifeline_bottom, 160, header_h, color, color, rx=8))
        elements.append(txt(px, lifeline_bottom + 30, label1, F_PARTICIPANT, "white", bold=True))
        elements.append(txt(px, lifeline_bottom + 60, label2, F_PARTICIPANT_SUB, "white"))

    # ---- AUTHENTICATION ----
    y = 310
    elements.append(txt(60, y, "Authentication", F_PHASE, "#222222", bold=True, anchor="start"))
    elements.append(sep_line(y + 15))

    y = 380
    elements.append(arrow(120, y, 360, y, C_USER))
    elements.append(txt(240, y - 25, "1. Login", F_MSG, C_USER))

    y = 470
    elements.append(arrow(360, y, 120, y, C_COGNITO, dashed=True))
    elements.append(txt(240, y - 25, "2. JWT token", F_MSG, C_COGNITO, italic=True))

    # JWT note
    ny = y + 40
    elements.append(rrect(220, ny, 280, 130, "#E3F2FD", C_COGNITO, stroke_width=2, rx=8))
    elements.append(txt(360, ny + 30, "JWT Claims:", F_NOTE, C_COGNITO, bold=True))
    elements.append(txt(360, ny + 62, "role: line_supervisor", 24, C_COGNITO, mono=True))
    elements.append(txt(360, ny + 92, "line_scope: Line 7", 24, C_COGNITO, mono=True))
    elements.append(txt(360, ny + 118, "plant_scope: Plant 2", 24, C_COGNITO, mono=True))

    # ---- TOOL INVOCATION ----
    y = 700
    elements.append(txt(60, y, "Tool Invocation", F_PHASE, "#222222", bold=True, anchor="start"))
    elements.append(sep_line(y + 15))

    y = 780
    elements.append(arrow(120, y, 600, y, C_USER))
    elements.append(txt(360, y - 25, '3. "OEE for Line 7?"', F_MSG, C_USER))

    y = 870
    elements.append(rrect(430, y - 30, 340, 65, "#FFF3E0", C_AGENT, stroke_width=2, rx=8))
    elements.append(txt(600, y, "4. LLM: get_oee_trends", F_NOTE, C_AGENT))

    y = 980
    elements.append(arrow(600, y, 880, y, C_AGENT))
    elements.append(txt(740, y - 25, "5. MCP call + JWT", F_MSG, C_AGENT))

    # Activation on gateway
    elements.append(rrect(870, y + 5, 20, 600, C_GATEWAY, C_GATEWAY, stroke_width=0, rx=3))

    # ---- ENRICHMENT ----
    y = 1080
    elements.append(txt(60, y, "Enrichment", F_PHASE, "#222222", bold=True, anchor="start"))
    elements.append(sep_line(y + 15))

    y = 1160
    elements.append(rrect(680, y - 30, 400, 110, "#E8F5E9", C_INTERCEPTOR, stroke_width=2, rx=8))
    elements.append(txt(880, y, "6-7. REQUEST Interceptor:", F_NOTE, C_INTERCEPTOR, bold=True))
    elements.append(txt(880, y + 35, "Decode JWT, extract scope", 24, C_INTERCEPTOR))
    elements.append(txt(880, y + 65, "Inject user_context into args", 24, C_INTERCEPTOR))

    # ---- AUTHORIZATION ----
    y = 1350
    elements.append(txt(60, y, "Authorization", F_PHASE, "#222222", bold=True, anchor="start"))
    elements.append(sep_line(y + 15))

    y = 1430
    elements.append(arrow(880, y, 1150, y, C_GATEWAY))
    elements.append(txt(1015, y - 25, "8. Evaluate", F_MSG, C_GATEWAY))

    # Activation on cedar
    elements.append(rrect(1140, y + 5, 20, 250, C_CEDAR, C_CEDAR, stroke_width=0, rx=3))

    # Cedar note
    ny = y + 50
    elements.append(rrect(950, ny, 400, 180, "#F3E5F5", C_CEDAR, stroke_width=2, rx=8))
    elements.append(txt(1150, ny + 30, "Cedar Evaluation:", F_NOTE, C_CEDAR, bold=True))
    elements.append(txt(1150, ny + 65, "permit_all -> PERMIT", 24, C_CEDAR, mono=True))
    elements.append(txt(1150, ny + 95, "forbid_line_scope:", 24, C_CEDAR, mono=True))
    elements.append(txt(1150, ny + 125, "'Line 7' in scope? YES", 24, C_CEDAR, mono=True))
    elements.append(txt(1150, ny + 155, "Result: ALLOW", F_NOTE, C_ALLOW, bold=True))

    # ---- ALT FRAME ----
    alt_top = 1780
    alt_mid = 2650
    alt_bottom = 3350

    elements.append(f'<rect x="50" y="{alt_top}" width="1300" height="{alt_bottom - alt_top}" fill="none" stroke="#555555" stroke-width="3" rx="8"/>')
    elements.append(txt(90, alt_top + 40, "alt", 34, "#444444", bold=True, anchor="start"))
    elements.append(f'<line x1="50" y1="{alt_mid}" x2="1350" y2="{alt_mid}" stroke="#555555" stroke-width="2" stroke-dasharray="10,5"/>')
    elements.append(txt(150, alt_top + 85, "[ALLOW - in scope]", F_MSG, C_ALLOW, bold=True, anchor="start"))
    elements.append(txt(150, alt_mid + 45, "[DENY - out of scope]", F_MSG, C_DENY, bold=True, anchor="start"))

    # --- ALLOW PATH ---
    y = 1900
    elements.append(arrow(1150, y, 880, y, C_ALLOW, dashed=True))
    elements.append(txt(1015, y - 25, "9a. ALLOW", F_MSG, C_ALLOW, bold=True))

    y = 2000
    elements.append(rrect(680, y - 30, 400, 70, "#E8F5E9", C_ALLOW, stroke_width=2, rx=8))
    elements.append(txt(880, y + 5, "10a. Execute Lambda tool", F_NOTE, C_ALLOW))

    y = 2130
    elements.append(rrect(680, y - 30, 400, 70, "#E8F5E9", C_TOOL, stroke_width=2, rx=8))
    elements.append(txt(880, y + 5, "11a. Return OEE data", F_NOTE, C_TOOL))

    y = 2260
    elements.append(arrow(880, y, 600, y, C_GATEWAY, dashed=True))
    elements.append(txt(740, y - 25, "12a. Tool result", F_MSG, C_GATEWAY, italic=True))

    y = 2380
    elements.append(arrow(600, y, 120, y, C_AGENT, dashed=True))
    elements.append(txt(360, y - 25, "13a. Data summary", F_MSG, C_AGENT, italic=True))

    # --- DENY PATH ---
    y = 2750
    elements.append(arrow(1150, y, 880, y, C_DENY, dashed=True))
    elements.append(txt(1015, y - 25, "9b. DENY", F_MSG, C_DENY, bold=True))

    y = 2860
    elements.append(rrect(680, y - 30, 400, 80, "#FFEBEE", C_DENY, stroke_width=2, rx=8))
    elements.append(txt(880, y, "MCP Server NEVER", F_NOTE, C_DENY, bold=True))
    elements.append(txt(880, y + 32, "INVOKED", F_NOTE, C_DENY, bold=True))

    y = 3010
    elements.append(arrow(880, y, 600, y, C_DENY, dashed=True))
    elements.append(txt(740, y - 25, "10b. Access denied", F_MSG, C_DENY, italic=True))

    y = 3130
    elements.append(arrow(600, y, 120, y, C_DENY, dashed=True))
    elements.append(txt(360, y - 25, "11b. Scope limit explained", F_MSG, C_DENY, italic=True))

    # --- RESPONSE PHASE ---
    y = 3460
    elements.append(txt(60, y, "Response", F_PHASE, "#222222", bold=True, anchor="start"))
    elements.append(sep_line(y + 15))

    y = 3550
    elements.append(rrect(430, y - 35, 340, 100, "#FFF3E0", C_AGENT, stroke_width=2, rx=8))
    elements.append(txt(600, y - 5, "LLM synthesizes:", F_NOTE, C_AGENT, bold=True))
    elements.append(txt(600, y + 30, "ALLOW -> data summary", 24, C_AGENT))
    elements.append(txt(600, y + 58, "DENY -> scope guidance", 24, C_AGENT))

    y = 3720
    elements.append(arrow(600, y, 120, y, C_AGENT, dashed=True))
    elements.append(txt(360, y - 25, "14. Response to user", F_MSG, C_AGENT, italic=True))

    # --- Legend ---
    y = 3850
    elements.append(txt(100, y, "Legend:", F_MSG, "#333333", bold=True, anchor="start"))
    elements.append(arrow(250, y, 360, y, "#333333"))
    elements.append(txt(380, y, "Call", F_NOTE, "#333333", anchor="start"))
    elements.append(arrow(500, y, 610, y, "#333333", dashed=True))
    elements.append(txt(630, y, "Return", F_NOTE, "#333333", anchor="start"))
    elements.append(rrect(780, y - 14, 28, 28, C_ALLOW, C_ALLOW, rx=4))
    elements.append(txt(820, y, "ALLOW", F_NOTE, C_ALLOW, anchor="start"))
    elements.append(rrect(960, y - 14, 28, 28, C_DENY, C_DENY, rx=4))
    elements.append(txt(1000, y, "DENY", F_NOTE, C_DENY, anchor="start"))

    elements.append('</svg>')
    return '\n'.join(elements)


# =============================================================================
# DIAGRAM 2: THREE PERSONAS COMPARISON
# Narrower (1400 wide) with large fonts
# =============================================================================

def create_personas_diagram_svg():
    W = 1400
    H = 1800
    elements = [svg_header(W, H)]

    # Colors
    C_USER = "#232F3E"
    C_AGENT = "#C43E00"
    C_GATEWAY = "#1A237E"
    C_CEDAR = "#4A148C"
    C_ALLOW = "#1B5E20"
    C_DENY = "#B71C1C"

    # Font sizes
    F_TITLE = 44
    F_SUBTITLE = 28
    F_HEADER = 28
    F_NAME = 32
    F_BOX = 24
    F_BADGE = 26

    # Title
    elements.append(txt(W//2, 55, "Same Agent, Same Interface", F_TITLE, C_USER, bold=True))
    elements.append(txt(W//2, 100, "Different Data Access", F_TITLE, C_USER, bold=True))
    elements.append(txt(W//2, 145, "AgentCore Gateway enforces Cedar policies at parameter level", F_SUBTITLE, "#555555"))

    # Column headers
    cols = [
        (160, "Query"),
        (400, "Agent"),
        (640, "Gateway"),
        (880, "Cedar"),
        (1120, "Result"),
    ]

    for cx, label in cols:
        elements.append(txt(cx, 210, label, F_HEADER, "#333333", bold=True))

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

    box_w = 200
    box_h = 110
    row_height = 480
    start_y = 270

    for idx, persona in enumerate(personas):
        row_y = start_y + idx * row_height
        is_allow = persona["result"] == "ALLOW"
        result_color = C_ALLOW if is_allow else C_DENY
        result_bg = "#E8F5E9" if is_allow else "#FFEBEE"

        # Persona name
        elements.append(txt(W//2, row_y, persona["name"], F_NAME, C_USER, bold=True))

        # AgentCore region highlight
        elements.append(rrect(510, row_y + 30, 500, box_h + 20, "#EDE7F6", C_GATEWAY, stroke_width=1.5, rx=10))
        elements.append(txt(760, row_y + 45, "AgentCore", 20, C_GATEWAY, italic=True))

        by = row_y + 85  # box center y

        # Boxes
        steps = [
            (160, persona["query_l1"], persona["query_l2"], "#E3F2FD", "#1565C0"),
            (400, "LLM selects", "MCP tool", "#FFF3E0", C_AGENT),
            (640, "Interceptor", "+ JWT check", "#E8EAF6", C_GATEWAY),
            (880, persona["cedar_l1"], persona["cedar_l2"], "#F3E5F5", C_CEDAR),
            (1120, persona["resp_l1"], persona["resp_l2"], result_bg, result_color),
        ]

        for sx, l1, l2, sfill, sstroke in steps:
            elements.append(rrect(sx - box_w//2, by - box_h//2, box_w, box_h, sfill, sstroke, stroke_width=2.5, rx=8))
            elements.append(txt(sx, by - 16, l1, F_BOX, "#222222"))
            elements.append(txt(sx, by + 16, l2, F_BOX, "#222222"))

        # Arrows
        arrow_xs = [160, 400, 640, 880, 1120]
        for i in range(len(arrow_xs) - 1):
            x1 = arrow_xs[i] + box_w // 2 + 5
            x2 = arrow_xs[i + 1] - box_w // 2 - 5
            color = result_color if i >= 3 else "#333333"
            elements.append(arrow(x1, by, x2, by, color, width=2.5))

        # Decision badge
        badge_x = (880 + 1120) // 2
        elements.append(rrect(badge_x - 55, by - 50, 110, 36, result_color, result_color, rx=14))
        elements.append(txt(badge_x, by - 31, persona["result"], F_BADGE, "white", bold=True))

        # Separator
        if idx < len(personas) - 1:
            sep_y = row_y + row_height - 60
            elements.append(f'<line x1="80" y1="{sep_y}" x2="1320" y2="{sep_y}" stroke="#DDDDDD" stroke-width="2"/>')

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

    print("\nDone! Optimized for GitLab README display — narrower viewBox, larger fonts.")
