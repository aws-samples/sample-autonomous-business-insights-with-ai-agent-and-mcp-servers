#!/usr/bin/env python3
"""Generate SVG sequence diagrams for AgentCore Gateway access control flow.

Produces two SVG files with large readable fonts (all >= 20px):
  1. sequence_diagram_access_control.svg — full UML sequence diagram
  2. sequence_diagram_personas.svg — three personas comparison

No matplotlib — pure SVG string construction for crisp vector output.
"""

import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


# =============================================================================
# SHARED SVG UTILITIES
# =============================================================================

def svg_header(width, height):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
<defs>
  <marker id="arrow-black" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
    <polygon points="0 0, 10 3.5, 0 7" fill="#333333"/>
  </marker>
  <marker id="arrow-user" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
    <polygon points="0 0, 10 3.5, 0 7" fill="#232F3E"/>
  </marker>
  <marker id="arrow-cognito" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
    <polygon points="0 0, 10 3.5, 0 7" fill="#B71C1C"/>
  </marker>
  <marker id="arrow-agent" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
    <polygon points="0 0, 10 3.5, 0 7" fill="#C43E00"/>
  </marker>
  <marker id="arrow-gateway" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
    <polygon points="0 0, 10 3.5, 0 7" fill="#1A237E"/>
  </marker>
  <marker id="arrow-interceptor" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
    <polygon points="0 0, 10 3.5, 0 7" fill="#1B5E20"/>
  </marker>
  <marker id="arrow-cedar" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
    <polygon points="0 0, 10 3.5, 0 7" fill="#4A148C"/>
  </marker>
  <marker id="arrow-tool" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
    <polygon points="0 0, 10 3.5, 0 7" fill="#004D40"/>
  </marker>
  <marker id="arrow-allow" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
    <polygon points="0 0, 10 3.5, 0 7" fill="#1B5E20"/>
  </marker>
  <marker id="arrow-deny" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
    <polygon points="0 0, 10 3.5, 0 7" fill="#B71C1C"/>
  </marker>
</defs>
<rect width="{width}" height="{height}" fill="white"/>
'''


def rect(x, y, w, h, fill, stroke, stroke_width=2, rx=10):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'


def text(x, y, content, size, color, bold=False, italic=False, anchor="middle", mono=False):
    weight = ' font-weight="bold"' if bold else ''
    style = ' font-style="italic"' if italic else ''
    family = "Courier New, monospace" if mono else "Segoe UI, Helvetica, Arial, sans-serif"
    # Escape special XML characters
    content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
    return f'<text x="{x}" y="{y}" font-size="{size}" font-family="{family}"{weight}{style} fill="{color}" text-anchor="{anchor}" dominant-baseline="middle">{content}</text>'


def line(x1, y1, x2, y2, color="#333333", width=2.5, dashed=False, marker="arrow-black"):
    dash = ' stroke-dasharray="8,5"' if dashed else ''
    marker_attr = f' marker-end="url(#{marker})"' if marker else ''
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"{dash}{marker_attr}/>'


def dashed_line(x1, y1, x2, y2, color="#BBBBBB", width=1.5):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}" stroke-dasharray="6,4"/>'


# =============================================================================
# DIAGRAM 1: SEQUENCE DIAGRAM — ACCESS CONTROL
# =============================================================================

def create_sequence_diagram_svg():
    W = 2400
    H = 3200
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

    # Title
    elements.append(text(W//2, 50, "AgentCore Gateway: Fine-Grained Access Control", 42, C_USER, bold=True))
    elements.append(text(W//2, 95, "GW Policy + Custom REQUEST/RESPONSE Interceptors + Cedar Authorization", 24, "#444444"))

    # Participants
    participants = [
        (180, "Ravi", "(Line Supervisor)", C_USER, "user"),
        (530, "Amazon", "Cognito", C_COGNITO, "cognito"),
        (880, "Agent", "(Strands SDK)", C_AGENT, "agent"),
        (1280, "AgentCore", "Gateway", C_GATEWAY, "gateway"),
        (1630, "REQUEST", "Interceptor", C_INTERCEPTOR, "interceptor"),
        (1960, "Cedar Policy", "Engine", C_CEDAR, "cedar"),
        (2280, "MCP Tool", "(Lambda)", C_TOOL, "tool"),
    ]

    header_y = 140
    header_h = 70
    lifeline_bottom = 3050

    for px, label1, label2, color, _ in participants:
        # Header box
        elements.append(rect(px - 100, header_y, 200, header_h, color, color, rx=8))
        elements.append(text(px, header_y + 25, label1, 20, "white", bold=True))
        elements.append(text(px, header_y + 50, label2, 18, "white"))
        # Lifeline
        elements.append(dashed_line(px, header_y + header_h, px, lifeline_bottom, "#CCCCCC"))
        # Bottom box
        elements.append(rect(px - 100, lifeline_bottom, 200, header_h, color, color, rx=8))
        elements.append(text(px, lifeline_bottom + 25, label1, 20, "white", bold=True))
        elements.append(text(px, lifeline_bottom + 50, label2, 18, "white"))

    # ---- PHASE LABELS AND MESSAGES ----
    y = 270

    # --- Authentication Phase ---
    elements.append(text(80, y, "Authentication", 22, "#222222", bold=True, anchor="start"))
    elements.append(f'<line x1="80" y1="{y+12}" x2="2350" y2="{y+12}" stroke="#EEEEEE" stroke-width="1"/>')

    y = 320
    # 1. Login
    elements.append(line(180, y, 530, y, C_USER, marker="arrow-user"))
    elements.append(text(355, y - 18, "1. Login (credentials)", 20, C_USER, italic=True))

    y = 400
    # 2. JWT return
    elements.append(line(530, y, 180, y, C_COGNITO, dashed=True, marker="arrow-cognito"))
    elements.append(text(355, y - 18, "2. JWT {role, line_scope, plant_scope}", 20, C_COGNITO, italic=True))

    # JWT Claims note
    ny = y + 40
    elements.append(rect(380, ny, 300, 110, "#E3F2FD", C_COGNITO, stroke_width=1.5, rx=8))
    elements.append(text(530, ny + 25, "JWT Claims:", 20, C_COGNITO, bold=True))
    elements.append(text(530, ny + 52, "role = line_supervisor", 18, C_COGNITO, mono=True))
    elements.append(text(530, ny + 77, "line_scope = Line 7", 18, C_COGNITO, mono=True))
    elements.append(text(530, ny + 100, "plant_scope = Plant 2", 18, C_COGNITO, mono=True))

    # --- Tool Invocation Phase ---
    y = 590
    elements.append(text(80, y, "Tool Invocation", 22, "#222222", bold=True, anchor="start"))
    elements.append(f'<line x1="80" y1="{y+12}" x2="2350" y2="{y+12}" stroke="#EEEEEE" stroke-width="1"/>')

    y = 650
    # 3. User query
    elements.append(line(180, y, 880, y, C_USER, marker="arrow-agent"))
    elements.append(text(530, y - 18, '3. "What\'s the OEE for Line 7?"', 20, C_USER))

    y = 730
    # 4. Agent self-call (note)
    elements.append(rect(900, y - 25, 520, 55, "#FFF3E0", C_AGENT, stroke_width=1.5, rx=8))
    elements.append(text(1160, y + 2, "4. LLM reasons: need get_oee_trends(line='Line 7')", 20, C_AGENT))

    y = 820
    # 5. Agent → Gateway
    elements.append(line(880, y, 1280, y, C_AGENT, marker="arrow-gateway"))
    elements.append(text(1080, y - 18, "5. MCP call: get_oee_trends(line=\"Line 7\") + Bearer JWT", 20, C_AGENT))

    # Activation bar on gateway
    elements.append(rect(1270, y + 5, 20, 400, "#1A237E", "#1A237E", stroke_width=0, rx=3))

    # --- Enrichment Phase ---
    y = 890
    elements.append(text(80, y, "Enrichment", 22, "#222222", bold=True, anchor="start"))
    elements.append(f'<line x1="80" y1="{y+12}" x2="2350" y2="{y+12}" stroke="#EEEEEE" stroke-width="1"/>')

    y = 950
    # 6. Gateway → Interceptor
    elements.append(line(1280, y, 1630, y, C_GATEWAY, marker="arrow-interceptor"))
    elements.append(text(1455, y - 18, "6. Invoke REQUEST Interceptor", 20, C_GATEWAY))

    # Activation bar on interceptor
    elements.append(rect(1620, y + 5, 20, 180, C_INTERCEPTOR, C_INTERCEPTOR, stroke_width=0, rx=3))

    y = 1020
    # 7. Interceptor self-work (note)
    elements.append(rect(1650, y - 30, 400, 80, "#E8F5E9", C_INTERCEPTOR, stroke_width=1.5, rx=8))
    elements.append(text(1850, y - 5, "7. Decode JWT payload", 20, C_INTERCEPTOR, bold=True))
    elements.append(text(1850, y + 25, "Extract role, line_scope → inject user_context", 18, C_INTERCEPTOR))

    y = 1130
    # 8. Interceptor → Gateway (return)
    elements.append(line(1630, y, 1280, y, C_INTERCEPTOR, dashed=True, marker="arrow-gateway"))
    elements.append(text(1455, y - 18, "8. Enriched request: user_context = {role, scope}", 19, C_INTERCEPTOR, italic=True))

    # --- Authorization Phase ---
    y = 1200
    elements.append(text(80, y, "Authorization", 22, "#222222", bold=True, anchor="start"))
    elements.append(f'<line x1="80" y1="{y+12}" x2="2350" y2="{y+12}" stroke="#EEEEEE" stroke-width="1"/>')

    y = 1260
    # 9. Gateway → Cedar
    elements.append(line(1280, y, 1960, y, C_GATEWAY, marker="arrow-cedar"))
    elements.append(text(1620, y - 18, "9. Evaluate: role=line_supervisor, action=get_oee_trends, line=\"Line 7\"", 19, C_GATEWAY))

    # Activation bar on cedar
    elements.append(rect(1950, y + 5, 20, 180, C_CEDAR, C_CEDAR, stroke_width=0, rx=3))

    # Cedar evaluation note
    ny = y + 50
    elements.append(rect(1780, ny, 380, 140, "#E8F5E9", C_CEDAR, stroke_width=1.5, rx=8))
    elements.append(text(1970, ny + 22, "Cedar Evaluation:", 20, C_CEDAR, bold=True))
    elements.append(text(1970, ny + 50, "permit_all → PERMIT", 18, C_CEDAR, mono=True))
    elements.append(text(1970, ny + 75, "forbid_line_scope:", 18, C_CEDAR, mono=True))
    elements.append(text(1970, ny + 100, "  'Line 7' in ['Line 7']? YES", 18, C_CEDAR, mono=True))
    elements.append(text(1970, ny + 125, "Result: ALLOW", 20, C_ALLOW, bold=True))

    # ---- ALT FRAME ----
    alt_top = 1510
    alt_mid = 1990
    alt_bottom = 2530

    # Outer frame
    elements.append(f'<rect x="100" y="{alt_top}" width="2250" height="{alt_bottom - alt_top}" fill="none" stroke="#555555" stroke-width="2" rx="6"/>')
    elements.append(text(140, alt_top + 28, "alt", 22, "#444444", bold=True, anchor="start"))
    # Divider
    elements.append(f'<line x1="100" y1="{alt_mid}" x2="2350" y2="{alt_mid}" stroke="#555555" stroke-width="1.5" stroke-dasharray="8,4"/>')
    # Guards
    elements.append(text(200, alt_top + 60, "[ALLOW — parameter in user scope]", 21, C_ALLOW, bold=True, anchor="start"))
    elements.append(text(200, alt_mid + 35, "[DENY — parameter outside scope]", 21, C_DENY, bold=True, anchor="start"))

    # --- ALLOW PATH ---
    y = 1600
    # 10a. Cedar → Gateway: ALLOW
    elements.append(line(1960, y, 1280, y, C_ALLOW, dashed=True, marker="arrow-allow"))
    elements.append(text(1620, y - 18, "10a. Decision: ALLOW", 21, C_ALLOW, bold=True))

    y = 1680
    # 11a. Gateway → Tool
    elements.append(line(1280, y, 2280, y, C_GATEWAY, marker="arrow-tool"))
    elements.append(text(1780, y - 18, "11a. Execute Lambda tool target", 20, C_GATEWAY))

    # Activation bar on tool
    elements.append(rect(2270, y + 5, 20, 80, C_TOOL, C_TOOL, stroke_width=0, rx=3))

    y = 1760
    # 12a. Tool → Gateway return
    elements.append(line(2280, y, 1280, y, C_TOOL, dashed=True, marker="arrow-gateway"))
    elements.append(text(1780, y - 18, "12a. OEE data (Line 7, 4 weeks)", 20, C_TOOL, italic=True))

    y = 1850
    # 13a. Gateway → Agent return
    elements.append(line(1280, y, 880, y, C_GATEWAY, dashed=True, marker="arrow-agent"))
    elements.append(text(1080, y - 18, "13a. Tool result → Agent", 20, C_GATEWAY, italic=True))

    # --- DENY PATH ---
    y = 2060
    # 10b. Cedar → Gateway: DENY
    elements.append(line(1960, y, 1280, y, C_DENY, dashed=True, marker="arrow-deny"))
    elements.append(text(1620, y - 18, "10b. Decision: DENY — \"Line 4 not in scope\"", 20, C_DENY, bold=True))

    # MCP NEVER INVOKED note
    elements.append(rect(2150, y + 30, 250, 70, "#FFEBEE", C_DENY, stroke_width=2, rx=8))
    elements.append(text(2275, y + 55, "MCP Server", 20, C_DENY, bold=True))
    elements.append(text(2275, y + 80, "NEVER INVOKED", 20, C_DENY, bold=True))

    y = 2200
    # 11b. Gateway → Agent: deny
    elements.append(line(1280, y, 880, y, C_DENY, dashed=True, marker="arrow-deny"))
    elements.append(text(1080, y - 18, '11b. Error: "[Policy] Access denied. Scope: Line 7 only"', 19, C_DENY, italic=True))

    # --- Response Phase ---
    y = 2620
    elements.append(text(80, y, "Response", 22, "#222222", bold=True, anchor="start"))
    elements.append(f'<line x1="80" y1="{y+12}" x2="2350" y2="{y+12}" stroke="#EEEEEE" stroke-width="1"/>')

    y = 2680
    # Agent self-note
    elements.append(rect(700, y - 25, 450, 75, "#FFF3E0", C_AGENT, stroke_width=1.5, rx=8))
    elements.append(text(925, y, "LLM synthesizes:", 20, C_AGENT, bold=True))
    elements.append(text(925, y + 28, "ALLOW → data summary | DENY → explains scope", 19, C_AGENT))

    y = 2800
    # 14. Agent → User
    elements.append(line(880, y, 180, y, C_AGENT, dashed=True, marker="arrow-user"))
    elements.append(text(530, y - 18, "14. Natural language response to user", 20, C_AGENT, italic=True))

    # --- Legend ---
    y = 2920
    elements.append(text(200, y, "Legend:", 22, "#333333", bold=True, anchor="start"))
    # Solid arrow
    elements.append(line(330, y, 430, y, "#333333", marker="arrow-black"))
    elements.append(text(450, y, "Synchronous call", 20, "#333333", anchor="start"))
    # Dashed arrow
    elements.append(line(750, y, 850, y, "#333333", dashed=True, marker="arrow-black"))
    elements.append(text(870, y, "Response / return", 20, "#333333", anchor="start"))
    # Green = ALLOW
    elements.append(rect(1200, y - 12, 24, 24, C_ALLOW, C_ALLOW, rx=4))
    elements.append(text(1240, y, "ALLOW path", 20, C_ALLOW, anchor="start"))
    # Red = DENY
    elements.append(rect(1500, y - 12, 24, 24, C_DENY, C_DENY, rx=4))
    elements.append(text(1540, y, "DENY path", 20, C_DENY, anchor="start"))

    elements.append('</svg>')
    return '\n'.join(elements)


# =============================================================================
# DIAGRAM 2: THREE PERSONAS COMPARISON
# =============================================================================

def create_personas_diagram_svg():
    W = 2200
    H = 1400
    elements = [svg_header(W, H)]

    # Colors
    C_USER = "#232F3E"
    C_AGENT = "#C43E00"
    C_GATEWAY = "#1A237E"
    C_CEDAR = "#4A148C"
    C_ALLOW = "#1B5E20"
    C_DENY = "#B71C1C"

    # Title
    elements.append(text(W//2, 45, "Same Agent, Same Interface — Different Data Access", 38, C_USER, bold=True))
    elements.append(text(W//2, 85, "AgentCore Gateway enforces Cedar policies at the parameter level", 22, "#555555"))

    # Column headers
    cols = [
        (200, "User Query"),
        (520, "Strands Agent"),
        (870, "AgentCore Gateway"),
        (1230, "Cedar Policy Engine"),
        (1580, "MCP Tool (Lambda)"),
        (1950, "Agent Response"),
    ]

    for cx, label in cols:
        elements.append(text(cx, 130, label, 20, "#333333", bold=True))

    # Personas data
    personas = [
        {
            "name": "Priya (Plant Manager)",
            "query": '"Anomalies across\nall lines?"',
            "agent": "LLM reasons →\nselects MCP tool",
            "gateway": "REQUEST Interceptor\n+ JWT extraction",
            "cedar": "Full Access\n(all plants/lines)",
            "result": "ALLOW",
            "tool": "Lambda executes\n✓ Returns data",
            "response": "Sees all 12 lines,\nprioritized by severity",
        },
        {
            "name": "Ravi (Line Supervisor)",
            "query": '"Show Line 4\nequipment"',
            "agent": "LLM reasons →\nselects MCP tool",
            "gateway": "REQUEST Interceptor\n+ JWT extraction",
            "cedar": "Line 7,\nPlant 2 only",
            "result": "DENY",
            "tool": "Lambda NOT\ninvoked ✗",
            "response": "Line 4 outside scope.\nSuggests Line 7 instead.",
        },
        {
            "name": "Ankit (Maintenance Tech)",
            "query": '"Machine 72\nvibration?"',
            "agent": "LLM reasons →\nselects MCP tool",
            "gateway": "REQUEST Interceptor\n+ JWT extraction",
            "cedar": "Machines 41-45\nonly",
            "result": "DENY",
            "tool": "Lambda NOT\ninvoked ✗",
            "response": "Machine 72 not assigned.\nSuggests Machine 42.",
        },
    ]

    box_w = 260
    box_h = 90
    row_height = 380
    start_y = 180

    for idx, persona in enumerate(personas):
        row_y = start_y + idx * row_height
        is_allow = persona["result"] == "ALLOW"
        result_color = C_ALLOW if is_allow else C_DENY
        result_bg = "#E8F5E9" if is_allow else "#FFEBEE"

        # Persona name label
        elements.append(text(200, row_y, persona["name"], 24, C_USER, bold=True))

        # AgentCore region highlight
        elements.append(rect(720, row_y + 20, 660, box_h + 30, "#EDE7F6", C_GATEWAY, stroke_width=1.5, rx=10))
        elements.append(text(1050, row_y + 37, "Amazon Bedrock AgentCore", 16, C_GATEWAY, italic=True))

        # Box Y center
        by = row_y + 55

        # Step boxes with multiline text
        steps = [
            (200, persona["query"], "#E3F2FD", "#1565C0"),
            (520, persona["agent"], "#FFF3E0", C_AGENT),
            (870, persona["gateway"], "#E8EAF6", C_GATEWAY),
            (1230, persona["cedar"], "#F3E5F5", C_CEDAR),
            (1580, persona["tool"], result_bg, result_color),
            (1950, persona["response"], result_bg, result_color),
        ]

        for sx, stext, sfill, sstroke in steps:
            elements.append(rect(sx - box_w//2, by - box_h//2, box_w, box_h, sfill, sstroke, stroke_width=2, rx=8))
            lines = stext.split('\n')
            if len(lines) == 1:
                elements.append(text(sx, by + 2, lines[0], 18, "#222222"))
            else:
                elements.append(text(sx, by - 12, lines[0], 18, "#222222"))
                elements.append(text(sx, by + 14, lines[1], 18, "#222222"))

        # Arrows between boxes
        arrow_xs = [200, 520, 870, 1230, 1580, 1950]
        for i in range(len(arrow_xs) - 1):
            x1 = arrow_xs[i] + box_w // 2 + 5
            x2 = arrow_xs[i + 1] - box_w // 2 - 5
            # Color arrows to/from tool based on result
            if i >= 3:
                marker = "arrow-allow" if is_allow else "arrow-deny"
                color = result_color
            else:
                marker = "arrow-black"
                color = "#333333"
            elements.append(line(x1, by, x2, by, color, width=2, marker=marker))

        # Decision badge between cedar and tool
        badge_x = (1230 + 1580) // 2
        badge_color = C_ALLOW if is_allow else C_DENY
        elements.append(rect(badge_x - 45, by - 35, 90, 28, badge_color, badge_color, rx=12))
        elements.append(text(badge_x, by - 20, persona["result"], 18, "white", bold=True))

        # Separator line (except last)
        if idx < len(personas) - 1:
            sep_y = row_y + row_height - 50
            elements.append(f'<line x1="80" y1="{sep_y}" x2="2120" y2="{sep_y}" stroke="#DDDDDD" stroke-width="1.5"/>')

    elements.append('</svg>')
    return '\n'.join(elements)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    # Diagram 1
    svg1 = create_sequence_diagram_svg()
    path1 = os.path.join(OUTPUT_DIR, "sequence_diagram_access_control.svg")
    with open(path1, 'w', encoding='utf-8') as f:
        f.write(svg1)
    print(f"Saved: {path1}")

    # Diagram 2
    svg2 = create_personas_diagram_svg()
    path2 = os.path.join(OUTPUT_DIR, "sequence_diagram_personas.svg")
    with open(path2, 'w', encoding='utf-8') as f:
        f.write(svg2)
    print(f"Saved: {path2}")

    print("\nDone! Two SVG diagrams generated with large readable fonts.")
