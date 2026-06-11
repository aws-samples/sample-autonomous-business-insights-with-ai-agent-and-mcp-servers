---
title: "The Semantic Layer Server"
weight: 34
---

# The Semantic Layer — Data Source Discovery via MCP

## The Scalability Problem

With 4 servers and ~10 tools, the agent can pick the right tools from descriptions alone. But what happens at enterprise scale?

| Scale | Without Semantic Layer | With Semantic Layer |
|-------|----------------------|---------------------|
| 10 tools | ✅ LLM picks fine | Works, slight overhead |
| 30 tools | ⚠️ Prompt bloats, some mis-routing | Narrows to 5-8 relevant tools |
| 50+ tools | ❌ Context overflow, accuracy drops | Still returns top-N, scales cleanly |
| New source added | Must update prompt, redeploy | Register in catalog — zero code change |

The Semantic Layer is itself an **MCP server** — but instead of serving data, it serves **metadata about data**.

## The Implementation

Open `src/servers/semantic_layer_server.py`:

```python
from mcp.server import FastMCP
import json
import os

mcp = FastMCP(
    "Semantic Layer Server",
    port=int(os.getenv("SEMANTIC_LAYER_SERVER_PORT", "8005")),
)
```

### The Data Catalog

Each data source is registered with metadata:

```python
DATA_SOURCES = [
    {
        "source_id": "ds-equipment",
        "name": "Equipment Registry",
        "description": "Machine master data, installation records, specifications, shared infrastructure",
        "mcp_tools": ["get_equipment_status", "get_maintenance_history", "get_shared_infrastructure"],
        "glossary_terms": ["machine", "assembly line", "plant", "equipment", "motor",
                          "bearing", "maintenance", "repair", "warranty"],
        "data_origin": "SAP S/4HANA → Zero-ETL → Aurora PostgreSQL",
        "refresh_frequency": "Real-time (CDC)",
    },
    {
        "source_id": "ds-iot",
        "name": "IoT Sensor Telemetry",
        "description": "Real-time and historical sensor readings — temperature, vibration, pressure",
        "mcp_tools": ["get_sensor_readings", "detect_anomaly"],
        "glossary_terms": ["temperature", "vibration", "pressure", "sensor",
                          "anomaly", "threshold", "trend", "IoT", "telemetry"],
        "data_origin": "AWS IoT Core → Amazon MSK → S3 Tables → Redshift Spectrum",
        "refresh_frequency": "Streaming (sub-second)",
    },
    {
        "source_id": "ds-supply-chain",
        "name": "Supply Chain & Inventory",
        "description": "Spare parts inventory levels, supplier data, procurement lead times",
        "mcp_tools": ["check_parts_inventory", "get_supplier_lead_times"],
        "glossary_terms": ["parts", "inventory", "stock", "supplier", "lead time",
                          "reorder", "procurement", "bearing", "spare"],
        "data_origin": "SAP MM → Zero-ETL → Redshift",
        "refresh_frequency": "Hourly batch",
    },
    {
        "source_id": "ds-analytics",
        "name": "Production Analytics",
        "description": "OEE calculations, quality metrics, scrap rates, production KPIs",
        "mcp_tools": ["get_oee_trends", "get_quality_metrics"],
        "glossary_terms": ["OEE", "availability", "performance", "quality",
                          "scrap", "defect", "production", "throughput"],
        "data_origin": "Production systems → daily ETL → Redshift",
        "refresh_frequency": "Daily",
    },
]
```

### Tool: `discover_data_sources`

```python
@mcp.tool(description=(
    "Discover which data sources and tools are relevant for a given query. "
    "Call this FIRST before calling any domain-specific tools. "
    "Returns the relevant MCP tools to use, their data origins, and freshness."
))
def discover_data_sources(query_keywords: str) -> str:
    """Look up the Semantic Layer to find relevant data sources.

    Args:
        query_keywords: Space-separated keywords from the user's query
                       (e.g., "vibration machine 42 trend week").
    """
    keywords = [k.lower().strip() for k in query_keywords.split() if k.strip()]

    scored_sources = []
    for source in DATA_SOURCES:
        score = 0
        for keyword in keywords:
            # Match against glossary terms (strong signal)
            for term in source["glossary_terms"]:
                if keyword in term.lower() or term.lower() in keyword:
                    score += 2
            # Match against description (weaker signal)
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

    # Sort by relevance
    scored_sources.sort(key=lambda x: -x["relevance_score"])

    return json.dumps({
        "query_keywords": keywords,
        "sources_found": len(scored_sources),
        "recommended_sources": scored_sources,
        "guidance": "Call the recommended_tools from the most relevant sources.",
    }, indent=2)
```

## How the Agent Uses It

The system prompt instructs the agent:

```
## Query Workflow
1. Extract keywords from the user's question
2. Call discover_data_sources with those keywords
3. Use the recommended_tools from the response
4. Synthesize results into a unified answer
```

### Example: "Has vibration on Machine 42 gotten worse?"

```
Agent extracts keywords: "vibration machine 42 worse trend"

Agent calls: discover_data_sources("vibration machine 42 worse trend")

Response:
{
  "sources_found": 3,
  "recommended_sources": [
    {"name": "IoT Sensor Telemetry", "relevance_score": 8,
     "recommended_tools": ["get_sensor_readings", "detect_anomaly"]},
    {"name": "Equipment Registry", "relevance_score": 4,
     "recommended_tools": ["get_equipment_status", "get_maintenance_history"]},
    {"name": "Supply Chain & Inventory", "relevance_score": 2,
     "recommended_tools": ["check_parts_inventory"]}
  ]
}

Agent then calls: get_sensor_readings(machine_id=42, metric="vibration")
Agent then calls: get_maintenance_history(machine_id=42)
```

## Adding a New Data Source

To onboard a new data source (e.g., a predictive maintenance ML model), you just add an entry to the catalog:

```python
{
    "source_id": "ds-predictive",
    "name": "Predictive Maintenance",
    "description": "ML-based failure predictions, remaining useful life estimates",
    "mcp_tools": ["get_failure_prediction", "get_remaining_useful_life"],
    "glossary_terms": ["prediction", "failure", "RUL", "remaining life", "forecast"],
    "data_origin": "SageMaker inference pipeline → DynamoDB",
    "refresh_frequency": "Hourly (batch inference)",
}
```

**Zero changes to the agent code.** The agent will discover it on the next query that matches those glossary terms.

This is **"configuration, not code"** in practice.

### Tool: `get_data_catalog`

For exploration queries ("what data do you have access to?"):

```python
@mcp.tool(description="Get the full data catalog — all registered data sources, their tools, glossary terms, and lineage.")
def get_data_catalog() -> str:
    """Return the complete data catalog."""
    return json.dumps({
        "total_sources": len(DATA_SOURCES),
        "catalog": DATA_SOURCES,
    }, indent=2)
```

{{% notice success %}}
**Key Takeaway:** The Semantic Layer makes the system extensible through configuration. New data sources, new tools, new connectors — all added through catalog registration, not code changes.
{{% /notice %}}
