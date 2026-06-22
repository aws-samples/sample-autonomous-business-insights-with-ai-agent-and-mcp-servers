# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Semantic Layer MCP Server — powered by SageMaker Data Catalog.

This MCP server exposes the Semantic Layer as a tool that the agent calls
BEFORE querying domain MCP servers. It tells the agent what data exists,
where it lives, and which tools to use — enabling intelligent routing
without hard-coded logic.

Blog architecture flow:
  User Query → Agent → Semantic Layer (discover sources) → MCP Servers → Data

In production, this would be backed by Amazon SageMaker Data Catalog with
semantic annotations, business glossary, and data lineage metadata.
"""

import json
import os

from mcp.server import FastMCP

mcp = FastMCP(
    "Semantic Layer Server",
    port=int(os.getenv("SEMANTIC_LAYER_SERVER_PORT", "8005")),
)

# --------------------------------------------------------------------------
# Data Catalog Registry
# --------------------------------------------------------------------------

DATA_SOURCES = [
    {
        "source_id": "ds-equipment",
        "name": "Equipment Registry",
        "description": "Machine master data, installation records, specifications, shared infrastructure",
        "mcp_tools": ["get_equipment_status", "get_maintenance_history", "get_shared_infrastructure"],
        "glossary_terms": ["machine", "assembly line", "plant", "equipment", "motor", "bearing", "maintenance", "repair", "warranty"],
        "data_origin": "SAP S/4HANA → Zero-ETL → Redshift",
        "refresh_frequency": "Real-time (CDC)",
    },
    {
        "source_id": "ds-iot",
        "name": "IoT Sensor Telemetry",
        "description": "Real-time and historical sensor readings from 2000+ sensors — temperature, vibration, pressure",
        "mcp_tools": ["get_sensor_readings", "detect_anomaly"],
        "glossary_terms": ["temperature", "vibration", "pressure", "sensor", "anomaly", "threshold", "trend", "IoT", "telemetry"],
        "data_origin": "AWS IoT Core → IoT Rule → Amazon Timestream",
        "refresh_frequency": "Streaming (sub-second)",
    },
    {
        "source_id": "ds-supply-chain",
        "name": "Supply Chain & Inventory",
        "description": "Spare parts inventory levels, supplier data, procurement lead times, stock status",
        "mcp_tools": ["check_parts_inventory", "get_supplier_lead_times"],
        "glossary_terms": ["parts", "inventory", "stock", "supplier", "lead time", "reorder", "procurement", "bearing", "spare"],
        "data_origin": "SAP MM → Zero-ETL → Redshift",
        "refresh_frequency": "Hourly batch",
    },
    {
        "source_id": "ds-analytics",
        "name": "Production Analytics",
        "description": "OEE calculations, quality metrics, scrap rates, production KPIs over 4-week windows",
        "mcp_tools": ["get_oee_trends", "get_quality_metrics"],
        "glossary_terms": ["OEE", "availability", "performance", "quality", "scrap", "defect", "production", "throughput", "efficiency"],
        "data_origin": "Production systems → daily ETL → Redshift",
        "refresh_frequency": "Daily",
    },
]


@mcp.tool(description=(
    "Discover which data sources and tools are relevant for a given query. "
    "Call this FIRST before calling any domain-specific tools. "
    "Returns the relevant MCP tools to use, their data origins, and freshness."
))
def discover_data_sources(query_keywords: str) -> str:
    """Look up the Semantic Layer to find relevant data sources for a query.

    The agent should call this tool first to understand:
    - Which data sources contain relevant information
    - Which specific MCP tools to call
    - Where the data originates and how fresh it is

    This enables new data sources to be onboarded by registering them in the
    catalog rather than changing agent logic.

    Args:
        query_keywords: Space-separated keywords extracted from the user's query
                       (e.g., "vibration machine 42 trend week").

    Returns:
        JSON with ranked list of relevant data sources and recommended tools.
    """
    keywords = [k.lower().strip() for k in query_keywords.split() if k.strip()]

    scored_sources = []
    for source in DATA_SOURCES:
        score = 0
        for keyword in keywords:
            # Match against glossary terms
            for term in source["glossary_terms"]:
                if keyword in term.lower() or term.lower() in keyword:
                    score += 2
            # Match against description
            if keyword in source["description"].lower():
                score += 1
            # Match against name
            if keyword in source["name"].lower():
                score += 1

        if score > 0:
            scored_sources.append({
                "source_id": source["source_id"],
                "name": source["name"],
                "description": source["description"],
                "recommended_tools": source["mcp_tools"],
                "data_origin": source["data_origin"],
                "refresh_frequency": source["refresh_frequency"],
                "relevance_score": score,
            })

    # Sort by relevance score descending
    scored_sources.sort(key=lambda x: -x["relevance_score"])

    return json.dumps({
        "query_keywords": keywords,
        "sources_found": len(scored_sources),
        "recommended_sources": scored_sources,
        "guidance": (
            "Call the recommended_tools from the most relevant sources. "
            "Higher relevance_score means stronger match to your query."
        ),
    }, indent=2)


@mcp.tool(description="Get the full data catalog — all registered data sources, their tools, glossary terms, and lineage.")
def get_data_catalog() -> str:
    """Return the complete data catalog for exploration.

    Useful when the agent needs to understand the full scope of available
    data sources, or when the user asks what data is available.

    Returns:
        JSON with all registered data sources and their metadata.
    """
    return json.dumps({
        "total_sources": len(DATA_SOURCES),
        "catalog": DATA_SOURCES,
    }, indent=2)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
