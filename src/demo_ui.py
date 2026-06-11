# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Streamlit Web UI for the Manufacturing Insights Agent demo.

Run with:
    streamlit run src/demo_ui.py

Ensure MCP servers are running in another terminal:
    python -m src.servers.start_all
"""

import os
import sys
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
# Initialize session state
# --------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent" not in st.session_state:
    st.session_state.agent = ManufacturingInsightsAgent(AppConfig())
if "current_user_key" not in st.session_state:
    st.session_state.current_user_key = "sarah"

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
        options=["simulated", "live"],
        format_func=lambda x: {
            "simulated": "🧪 Simulated (no AWS infra needed)",
            "live": "🔴 Live (real AWS services)",
        }[x],
        index=0 if os.getenv("DATA_MODE", "simulated") == "simulated" else 1,
        help="Simulated uses in-memory sample data. Live queries Aurora, Timestream, Redshift, and OpenSearch.",
    )
    os.environ["DATA_MODE"] = data_mode

    if data_mode == "live":
        st.success("Connected to real AWS infrastructure")
    else:
        st.info("Using simulated data — only Bedrock is called")

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
            "What's the OEE trend for Line 7?",
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
# Main chat area
# --------------------------------------------------------------------------
st.title(f"🏭 Manufacturing Insights Agent")
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
            try:
                response = st.session_state.agent.query(user, last_query)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                error_msg = f"❌ **Error:** {str(e)}\n\nMake sure MCP servers are running:\n```\npython -m src.servers.start_all\n```"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
