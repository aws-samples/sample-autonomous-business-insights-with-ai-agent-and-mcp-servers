# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Streamlit Web UI for the Manufacturing Insights Agent demo.

Features:
- Left sidebar: User persona selection, data mode toggle, sample queries
- Center: Chat interface with markdown-rendered responses
- Right panel: Live backend activity log showing MCP calls, policy decisions, memory lookups

Run with:
    streamlit run src/demo_ui.py

Ensure MCP servers are running in another terminal:
    python -m src.servers.start_all
"""

import io
import logging
import os
import sys
import time
from pathlib import Path

# Add project root to path so 'src' module resolves
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from src.config import AppConfig
from src.identity.models import DEMO_USERS, UserIdentity, UserRole
from src.agent.agent import ManufacturingInsightsAgent

# --------------------------------------------------------------------------
# Page config
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Manufacturing Insights Agent",
    page_icon="🏭",
    layout="wide",
)

# --------------------------------------------------------------------------
# Custom logging handler that captures logs for the UI
# --------------------------------------------------------------------------


class StreamlitLogHandler(logging.Handler):
    """Captures log messages into a list for display in the UI."""

    def __init__(self):
        super().__init__()
        self.logs: list[dict] = []

    def emit(self, record):
        emoji = "📋"
        if "ALLOW" in record.getMessage():
            emoji = "✅"
        elif "DENY" in record.getMessage():
            emoji = "🚫"
        elif "Connected to" in record.getMessage():
            emoji = "🔌"
        elif "Processing query" in record.getMessage():
            emoji = "🧠"
        elif "Created new session" in record.getMessage():
            emoji = "💾"
        elif "MCP" in record.getMessage() or "tools available" in record.getMessage():
            emoji = "🔧"

        self.logs.append({
            "time": time.strftime("%H:%M:%S"),
            "emoji": emoji,
            "level": record.levelname,
            "source": record.name.split(".")[-1],
            "message": record.getMessage(),
        })

    def clear(self):
        self.logs = []


# Initialize or get the log handler
if "log_handler" not in st.session_state:
    handler = StreamlitLogHandler()
    handler.setLevel(logging.INFO)

    # Attach to our project loggers
    for logger_name in [
        "src.agent.agent",
        "src.identity.gateway_hook",
        "src.identity.policy",
        "src.memory.manager",
    ]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

    st.session_state.log_handler = handler

log_handler: StreamlitLogHandler = st.session_state.log_handler

# --------------------------------------------------------------------------
# Initialize session state
# --------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent" not in st.session_state:
    st.session_state.agent = ManufacturingInsightsAgent(AppConfig())
if "current_user_key" not in st.session_state:
    st.session_state.current_user_key = "sarah"
if "last_logs" not in st.session_state:
    st.session_state.last_logs = []
if "current_mode" not in st.session_state:
    st.session_state.current_mode = "agentcore_gateway"

# --------------------------------------------------------------------------
# Sidebar — User persona selection
# --------------------------------------------------------------------------
with st.sidebar:
    st.image("https://d1.awsstatic.com/logos/aws-logo-lockups/poweredbyaws/PB_AWS_logo_RGB.61d334f1a1172da22295b6578b4bafa7c87fba20.png", width=180)
    st.title("🏭 Manufacturing Insights")
    st.caption("Powered by Amazon Bedrock AgentCore + Strands Agents + MCP")

    st.divider()

    # Data mode toggle
    st.subheader("Data Mode")
    data_mode = st.radio(
        "Choose data backend:",
        options=["agentcore_gateway", "live", "simulated"],
        format_func=lambda x: {
            "agentcore_gateway": "🚀 AgentCore Gateway (default — real Gateway + Lambda)",
            "live": "🔴 Live (real AWS data services, no Gateway)",
            "simulated": "🧪 Simulated (local MCP servers, SIMULATION_MODE)",
        }[x],
        index=0 if os.getenv("SIMULATION_MODE") != "true" else 2,
        help="AgentCore Gateway is the default production architecture. Simulation mode uses local MCP servers for development.",
    )
    if data_mode == "agentcore_gateway":
        os.environ["SIMULATION_MODE"] = "false"
        os.environ["DATA_MODE"] = "live"
        st.success("🚀 Using AgentCore Gateway + Lambda targets (default)")
    elif data_mode == "live":
        os.environ["SIMULATION_MODE"] = "true"
        os.environ["DATA_MODE"] = "live"
        st.success("Connected to real AWS data services (simulation mode, live data)")
    else:
        os.environ["SIMULATION_MODE"] = "true"
        os.environ["DATA_MODE"] = "simulated"
        st.info("Using simulated data — local MCP servers (simulation fallback)")

    # Re-create agent if mode changed
    if data_mode != st.session_state.current_mode:
        st.session_state.current_mode = data_mode
        st.session_state.agent = ManufacturingInsightsAgent(AppConfig())
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.subheader("Select User Persona")

    user_options = {
        "sarah": "👩‍💼 Sarah Chen — Plant Manager",
        "raj": "👨‍🔧 Raj Patel — Line Supervisor",
        "priya": "👩‍🔬 Priya Nair — Technician",
    }

    selected = st.radio(
        "Who are you?",
        options=list(user_options.keys()),
        format_func=lambda x: user_options[x],
        index=list(user_options.keys()).index(st.session_state.current_user_key),
    )

    # Clear chat when user changes
    if selected != st.session_state.current_user_key:
        st.session_state.current_user_key = selected
        st.session_state.messages = []
        st.session_state.last_logs = []
        st.rerun()

    user = DEMO_USERS[selected]

    st.divider()
    st.subheader("Access Scope")
    st.markdown(f"**Role:** {user.role.value.replace('_', ' ').title()}")
    if user.has_full_access:
        st.success("Full access — all plants, all lines")
    else:
        st.info(f"**Plants:** {', '.join(user.plant_scope)}")
        st.info(f"**Lines:** {', '.join(user.line_scope)}")
        if user.equipment_scope:
            st.info(f"**Equipment:** {', '.join(user.equipment_scope)}")

    st.divider()
    st.subheader("Sample Queries")
    sample_queries = {
        "sarah": [
            "Which assembly lines need attention this week?",
            "What's the relationship between Line 4 and Line 9 issues?",
            "Show me parts inventory status across all lines",
        ],
        "raj": [
            "What's the current status of Line 7?",
            "Are there any anomalies on my line?",
            "What is the status of Line 4?",
        ],
        "priya": [
            "Has the vibration on Machine 42 gotten worse since last week?",
            "What's the maintenance history for Machine 42?",
            "Are replacement bearings in stock for Machine 42?",
        ],
    }
    for q in sample_queries[selected]:
        if st.button(q, key=q, use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": q})
            st.rerun()

# --------------------------------------------------------------------------
# Main layout: Chat (left 65%) + Activity Log (right 35%)
# --------------------------------------------------------------------------
chat_col, log_col = st.columns([0.65, 0.35])

# --------------------------------------------------------------------------
# Left column — Chat
# --------------------------------------------------------------------------
with chat_col:
    st.title("🏭 Manufacturing Insights Agent")
    st.caption(f"Logged in as **{user.name}** ({user.role.value.replace('_', ' ').title()})")

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask about your manufacturing operations..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

    # Generate response for the last user message
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        last_query = st.session_state.messages[-1]["content"]

        with st.chat_message("assistant"):
            with st.spinner("Querying MCP servers..."):
                # Clear logs before this query
                log_handler.clear()

                try:
                    response = st.session_state.agent.query(user, last_query)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    # Capture logs from this query
                    st.session_state.last_logs = log_handler.logs.copy()
                except Exception as e:
                    error_msg = f"❌ **Error:** {str(e)}\n\nMake sure MCP servers are running:\n```\npython -m src.servers.start_all\n```"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    st.session_state.last_logs = log_handler.logs.copy()

# --------------------------------------------------------------------------
# Right column — Backend Activity Log
# --------------------------------------------------------------------------
with log_col:
    st.markdown("### ⚡ Backend Activity")
    st.caption("Real-time log of MCP calls, policy decisions, and memory lookups")
    st.divider()

    if st.session_state.last_logs:
        for log_entry in st.session_state.last_logs:
            emoji = log_entry["emoji"]
            source = log_entry["source"]
            message = log_entry["message"]
            timestamp = log_entry["time"]

            # Color-code by type
            if "DENY" in message:
                st.markdown(
                    f"<div style='background-color:#ffcccc;padding:8px;border-radius:5px;margin-bottom:6px;font-size:13px;'>"
                    f"<b>{emoji} {timestamp}</b> [{source}]<br/>{message}</div>",
                    unsafe_allow_html=True,
                )
            elif "ALLOW" in message:
                st.markdown(
                    f"<div style='background-color:#ccffcc;padding:8px;border-radius:5px;margin-bottom:6px;font-size:13px;'>"
                    f"<b>{emoji} {timestamp}</b> [{source}]<br/>{message}</div>",
                    unsafe_allow_html=True,
                )
            elif "Connected" in message or "tools available" in message:
                st.markdown(
                    f"<div style='background-color:#cce5ff;padding:8px;border-radius:5px;margin-bottom:6px;font-size:13px;'>"
                    f"<b>{emoji} {timestamp}</b> [{source}]<br/>{message}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div style='background-color:#f0f0f0;padding:8px;border-radius:5px;margin-bottom:6px;font-size:13px;'>"
                    f"<b>{emoji} {timestamp}</b> [{source}]<br/>{message}</div>",
                    unsafe_allow_html=True,
                )
    else:
        st.markdown(
            "<div style='color:#888;text-align:center;padding:40px;'>"
            "Submit a query to see backend activity here.<br/><br/>"
            "You'll see:<br/>"
            "🔌 MCP server connections<br/>"
            "🔧 Tool discovery<br/>"
            "✅ Policy ALLOW decisions<br/>"
            "🚫 Policy DENY decisions<br/>"
            "💾 Memory lookups<br/>"
            "🧠 Agent reasoning<br/>"
            "</div>",
            unsafe_allow_html=True,
        )
