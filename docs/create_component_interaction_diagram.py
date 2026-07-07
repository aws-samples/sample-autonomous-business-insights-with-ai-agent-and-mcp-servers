#!/usr/bin/env python3
"""Generate AgentCore Component Interactions diagram as SVG with large readable fonts.

Outputs a pure SVG file — no rasterization, infinitely scalable, crisp text at any zoom.
All font sizes >= 20px. Titles 44-48px. Component labels 28-32px. Body text 22-24px.
"""

import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "agentcore_component_interactions.svg")

# ViewBox dimensions - large enough for generous spacing
W = 1800
H = 2200

# Colors
C_USER = "#1565C0"
C_USER_BG = "#E3F2FD"
C_AGENT = "#4527A0"
C_AGENT_BG = "#EDE7F6"
C_GATEWAY = "#E65100"
C_GATEWAY_BG = "#FFF8E1"
C_INTERCEPT = "#BF360C"
C_INTERCEPT_BG = "#FBE9E7"
C_CEDAR = "#6A1B9A"
C_CEDAR_BG = "#F3E5F5"
C_ALLOW = "#2E7D32"
C_ALLOW_BG = "#E8F5E9"
C_DENY = "#C62828"
C_DENY_BG = "#FFEBEE"
C_RESPONSE = "#00695C"
C_RESPONSE_BG = "#E0F2F1"
C_TITLE = "#1a1a2e"
C_ARROW = "#444444"

# Font sizes
F_TITLE = 46
F_SUBTITLE = 24
F_BOX_TITLE = 30
F_BOX_BODY = 22
F_LABEL = 21
F_MONO = 20
F_PRINCIPLE = 22


def rounded_rect(x, y, w, h, fill, stroke, stroke_width=3, rx=12):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" ry="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"/>'


def text_elem(x, y, content, size, color, bold=False, italic=False, anchor="middle", mono=False):
    weight = ' font-weight="bold"' if bold else ''
    style = ' font-style="italic"' if italic else ''
    family = ' font-family="Courier New, monospace"' if mono else ' font-family="Segoe UI, Helvetica, Arial, sans-serif"'
    return f'<text x="{x}" y="{y}" font-size="{size}"{family}{weight}{style} fill="{color}" text-anchor="{anchor}">{content}</text>'


def arrow_down(x, y1, y2, color=C_ARROW):
    mid = x
    return f'''<line x1="{mid}" y1="{y1}" x2="{mid}" y2="{y2}" stroke="{color}" stroke-width="3" marker-end="url(#arrowhead-{color.replace('#','')})"/>'''


def arrow_right(x1, y, x2, color=C_ARROW):
    return f'''<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{color}" stroke-width="3" marker-end="url(#arrowhead-{color.replace('#','')})"/>'''


def arrow_diag(x1, y1, x2, y2, color=C_ARROW):
    return f'''<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="3" marker-end="url(#arrowhead-{color.replace('#','')})"/>'''


def build_svg():
    elements = []

    # Collect all arrow colors for marker definitions
    arrow_colors = {C_ARROW, C_USER, C_AGENT, C_INTERCEPT, C_ALLOW, C_DENY, C_RESPONSE, C_GATEWAY, C_CEDAR, C_TITLE}

    # SVG header
    elements.append(f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<style>
  text {{ dominant-baseline: middle; }}
</style>
<defs>''')

    # Arrow markers for each color
    for color in arrow_colors:
        cid = color.replace('#', '')
        elements.append(f'''  <marker id="arrowhead-{cid}" markerWidth="12" markerHeight="8" refX="10" refY="4" orient="auto">
    <polygon points="0 0, 12 4, 0 8" fill="{color}"/>
  </marker>''')

    elements.append('</defs>')

    # Background
    elements.append(f'<rect width="{W}" height="{H}" fill="white"/>')

    # ===== TITLE =====
    elements.append(text_elem(W//2, 55, "AgentCore Component Interactions", F_TITLE, C_TITLE, bold=True))
    elements.append(text_elem(W//2, 92, "Authentication → Enrichment → Authorization → Execution → Response", F_SUBTITLE, "#555555"))

    # ===== ROW 1: User → Cognito =====
    # User box
    uy = 125
    elements.append(rounded_rect(60, uy, 320, 80, C_USER_BG, C_USER))
    elements.append(text_elem(220, uy + 43, "User / Client", F_BOX_TITLE, C_USER, bold=True))

    # Arrow User → Cognito
    elements.append(arrow_right(380, uy + 40, 520, C_USER))
    elements.append(text_elem(450, uy + 22, "Login", F_LABEL, C_USER, italic=True))

    # Cognito box
    elements.append(rounded_rect(520, uy, 400, 80, C_USER_BG, C_USER))
    elements.append(text_elem(720, uy + 43, "Amazon Cognito / IdP", F_BOX_TITLE, C_USER, bold=True))

    # JWT Claims annotation
    jx = 1050
    elements.append(rounded_rect(jx, uy - 10, 380, 100, C_USER_BG, C_USER, stroke_width=2))
    elements.append(text_elem(jx + 190, uy + 15, "JWT Claims:", F_BOX_BODY, C_USER, bold=True))
    elements.append(text_elem(jx + 190, uy + 42, "role, line_scope,", F_MONO, C_USER, mono=True))
    elements.append(text_elem(jx + 190, uy + 67, "equipment_scope", F_MONO, C_USER, mono=True))

    # Arrow Cognito → JWT (return)
    elements.append(arrow_right(920, uy + 40, 1050, C_USER))
    elements.append(text_elem(985, uy + 22, "JWT", F_LABEL, C_USER, italic=True))

    # ===== Arrow down to Agent =====
    elements.append(arrow_down(720, 205, 250, C_USER))

    # ===== ROW 2: AGENT =====
    ay = 260
    elements.append(rounded_rect(160, ay, 1120, 100, C_AGENT_BG, C_AGENT))
    elements.append(text_elem(720, ay + 38, "AI AGENT (Strands SDK + Amazon Bedrock Claude)", F_BOX_TITLE, C_AGENT, bold=True))
    elements.append(text_elem(720, ay + 72, "System prompt: identity + scope + memory. LLM decides which tools to call.", F_BOX_BODY, C_AGENT))

    # Arrow Agent → Gateway
    elements.append(arrow_down(720, 360, 400, C_AGENT))
    elements.append(text_elem(740, 382, "tools/call (MCP JSON-RPC)", F_LABEL, C_AGENT, italic=True, anchor="start"))

    # ===== GATEWAY CONTAINER =====
    gw_y = 410
    gw_h = 1350
    elements.append(rounded_rect(80, gw_y, 1640, gw_h, C_GATEWAY_BG, C_GATEWAY, stroke_width=4, rx=16))
    elements.append(text_elem(W//2, gw_y + 45, "AgentCore GATEWAY", 38, C_GATEWAY, bold=True))
    elements.append(text_elem(W//2, gw_y + 80, "Single entry point — every tool call flows through here", F_BOX_BODY, C_GATEWAY))

    # --- Step 1: JWT Validation ---
    jv_y = gw_y + 110
    elements.append(rounded_rect(180, jv_y, 1440, 90, "#FFF8E1", C_GATEWAY))
    elements.append(text_elem(W//2, jv_y + 35, "1. Validate JWT Signature", F_BOX_TITLE, C_GATEWAY, bold=True))
    elements.append(text_elem(W//2, jv_y + 66, "Cognito JWKS verification — reject expired/invalid tokens", F_BOX_BODY, C_GATEWAY))

    # Arrow down
    elements.append(arrow_down(W//2, jv_y + 90, jv_y + 120, C_GATEWAY))

    # --- Step 2: Request Interceptor ---
    ri_y = jv_y + 130
    elements.append(rounded_rect(180, ri_y, 1440, 90, C_INTERCEPT_BG, C_INTERCEPT))
    elements.append(text_elem(W//2, ri_y + 35, "2. REQUEST Interceptor (Lambda)", F_BOX_TITLE, C_INTERCEPT, bold=True))
    elements.append(text_elem(W//2, ri_y + 66, "Decode JWT → inject user_context into tool args + set x-user-role header", F_BOX_BODY, C_INTERCEPT))

    # Arrow down
    elements.append(arrow_down(W//2, ri_y + 90, ri_y + 120, C_INTERCEPT))

    # --- Step 3: Cedar Policy Engine ---
    ce_y = ri_y + 130
    ce_h = 310
    elements.append(rounded_rect(180, ce_y, 1440, ce_h, C_CEDAR_BG, C_CEDAR))
    elements.append(text_elem(W//2, ce_y + 38, "3. CEDAR Policy Engine", F_BOX_TITLE, C_CEDAR, bold=True))

    cedar_lines = [
        "permit_all → PERMIT (baseline access)",
        "forbid_line_scope → check line param vs user scope",
        "forbid_equipment_scope → check machine_id vs user scope",
        "forbid_plant_scope → check plant param vs user scope",
        "",
        "Priority: forbid > permit > deny-by-default",
    ]
    cy = ce_y + 80
    for line in cedar_lines:
        if line:
            elements.append(text_elem(W//2, cy, line, F_MONO, C_CEDAR, mono=True))
        cy += 38

    # --- Step 4: ALLOW / DENY fork ---
    fork_y = ce_y + ce_h + 10

    # ALLOW arrow (left)
    elements.append(arrow_diag(580, ce_y + ce_h, 420, fork_y + 40, C_ALLOW))
    elements.append(text_elem(480, fork_y + 15, "PERMIT", F_LABEL, C_ALLOW, bold=True))

    # DENY arrow (right)
    elements.append(arrow_diag(1220, ce_y + ce_h, 1380, fork_y + 40, C_DENY))
    elements.append(text_elem(1320, fork_y + 15, "FORBID", F_LABEL, C_DENY, bold=True))

    # ALLOW box
    allow_y = fork_y + 50
    elements.append(rounded_rect(140, allow_y, 620, 150, C_ALLOW_BG, C_ALLOW))
    elements.append(text_elem(450, allow_y + 38, "ALLOW", F_BOX_TITLE, C_ALLOW, bold=True))
    elements.append(text_elem(450, allow_y + 75, "Invoke Lambda Tool Target", F_BOX_BODY, C_ALLOW))
    elements.append(text_elem(450, allow_y + 105, "Execute tool logic, return data", F_BOX_BODY, C_ALLOW))

    # DENY box
    elements.append(rounded_rect(1040, allow_y, 620, 150, C_DENY_BG, C_DENY))
    elements.append(text_elem(1350, allow_y + 38, "DENY", F_BOX_TITLE, C_DENY, bold=True))
    elements.append(text_elem(1350, allow_y + 75, '"[Policy] Access denied."', F_BOX_BODY, C_DENY))
    elements.append(text_elem(1350, allow_y + 105, '"Not authorized for Line 4"', F_BOX_BODY, C_DENY))

    # Arrows from ALLOW/DENY down to Response Interceptor
    resp_y = allow_y + 210
    elements.append(arrow_diag(450, allow_y + 150, 720, resp_y, C_ALLOW))
    elements.append(arrow_diag(1350, allow_y + 150, 1080, resp_y, C_DENY))

    # --- Step 5: Response Interceptor ---
    elements.append(rounded_rect(180, resp_y, 1440, 90, C_RESPONSE_BG, C_RESPONSE))
    elements.append(text_elem(W//2, resp_y + 35, "4. RESPONSE Interceptor (Lambda)", F_BOX_TITLE, C_RESPONSE, bold=True))
    elements.append(text_elem(W//2, resp_y + 66, "tools/list → filter by role  |  tool results → pass through", F_BOX_BODY, C_RESPONSE))

    # Arrow out of gateway
    elements.append(arrow_down(W//2, resp_y + 90, gw_y + gw_h + 30, C_RESPONSE))

    # ===== ROW: Agent Receives Result =====
    ar_y = gw_y + gw_h + 40
    elements.append(rounded_rect(160, ar_y, 1480, 130, C_AGENT_BG, C_AGENT))
    elements.append(text_elem(W//2, ar_y + 38, "AGENT Receives Result", F_BOX_TITLE, C_AGENT, bold=True))
    elements.append(text_elem(W//2, ar_y + 75, "ALLOW → synthesizes data into human-readable response", F_BOX_BODY, C_ALLOW))
    elements.append(text_elem(W//2, ar_y + 105, "DENY → explains scope limit, suggests alternative within user's scope", F_BOX_BODY, C_DENY))

    # ===== DESIGN PRINCIPLES =====
    dp_y = ar_y + 160
    elements.append(text_elem(W//2, dp_y, "Design Principles", 32, C_TITLE, bold=True))

    principles = [
        "▸  LLM decides WHAT to do, Cedar decides IF it's allowed",
        "▸  Fail-secure: No explicit permit = DENY",
        "▸  Parameter-level access control: Same tool, different data scope",
        "▸  MCP servers are auth-unaware: Zero access control logic in Lambdas",
    ]
    py = dp_y + 42
    for p in principles:
        elements.append(text_elem(200, py, p, F_PRINCIPLE, C_TITLE, anchor="start"))
        py += 38

    # Close SVG
    elements.append('</svg>')

    return '\n'.join(elements)


if __name__ == "__main__":
    svg_content = build_svg()
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(svg_content)
    print(f"SVG saved: {OUTPUT_PATH}")
    print(f"ViewBox: {W}x{H}, all fonts >= {F_MONO}px")
