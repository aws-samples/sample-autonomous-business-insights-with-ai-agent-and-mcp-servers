# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Semantic Layer — powered by SageMaker Data Catalog.

The Semantic Layer sits between the Agent and the MCP server
connectors. It exposes metadata about available data sources — table schemas,
column descriptions, business glossary terms, data lineage, and source
mappings — enabling the agent to understand what data exists across the
enterprise and where it resides without hard-coded logic.

This separation of metadata discovery from data retrieval means new sources
can be on-boarded by registering them in the Data Catalog rather than writing
custom integration code, keeping the system extensible through configuration.

In production, this would be backed by Amazon SageMaker Data Catalog
(formerly AWS Glue Data Catalog) with semantic annotations.
"""

import json
from dataclasses import dataclass, field


@dataclass
class DataSourceMapping:
    """Represents a registered data source in the semantic catalog."""

    source_id: str
    name: str
    description: str
    mcp_server: str
    tables: list[str] = field(default_factory=list)
    glossary_terms: list[str] = field(default_factory=list)
    lineage: dict[str, str] = field(default_factory=dict)


# Simulated SageMaker Data Catalog entries
CATALOG_ENTRIES = [
    DataSourceMapping(
        source_id="ds-equipment",
        name="Equipment Registry",
        description="Machine master data, installation records, and specifications",
        mcp_server="equipment-mcp-server",
        tables=["equipment_registry", "assembly_lines", "shared_infrastructure"],
        glossary_terms=["machine", "assembly line", "plant", "equipment type"],
        lineage={"source": "SAP S/4HANA", "refresh": "real-time via CDC"},
    ),
    DataSourceMapping(
        source_id="ds-maintenance",
        name="Maintenance Management",
        description="Work orders, maintenance history, warranty tracking",
        mcp_server="equipment-mcp-server",
        tables=["maintenance_history", "work_orders", "warranty_records"],
        glossary_terms=["corrective maintenance", "preventive maintenance", "MTBF", "downtime"],
        lineage={"source": "SAP PM", "refresh": "real-time via CDC"},
    ),
    DataSourceMapping(
        source_id="ds-iot",
        name="IoT Sensor Telemetry",
        description="Real-time and historical sensor readings from 2000+ sensors",
        mcp_server="iot-telemetry-mcp-server",
        tables=["sensor_readings", "anomaly_thresholds", "sensor_registry"],
        glossary_terms=["vibration", "temperature", "pressure", "anomaly", "threshold"],
        lineage={"source": "AWS IoT Core via Kepware", "refresh": "streaming via MSK"},
    ),
    DataSourceMapping(
        source_id="ds-supply-chain",
        name="Supply Chain & Inventory",
        description="Spare parts inventory, supplier data, procurement lead times",
        mcp_server="supply-chain-mcp-server",
        tables=["parts_inventory", "suppliers", "purchase_orders"],
        glossary_terms=["reorder point", "lead time", "safety stock", "BOM"],
        lineage={"source": "SAP MM", "refresh": "hourly batch"},
    ),
    DataSourceMapping(
        source_id="ds-analytics",
        name="Production Analytics",
        description="OEE calculations, quality metrics, production KPIs",
        mcp_server="analytics-mcp-server",
        tables=["oee_daily", "quality_inspections", "scrap_records", "production_output"],
        glossary_terms=["OEE", "availability", "performance", "quality rate", "scrap rate"],
        lineage={"source": "SageMaker Lakehouse (aggregated)", "refresh": "daily ETL"},
    ),
]


class SemanticCatalog:
    """Provides data source discovery and routing metadata.

    The Agent queries the Semantic Catalog to understand which
    MCP server handles which type of data, enabling intelligent routing
    without hard-coded logic.
    """

    def __init__(self) -> None:
        self._entries = {e.source_id: e for e in CATALOG_ENTRIES}
        self._glossary_index = self._build_glossary_index()

    def _build_glossary_index(self) -> dict[str, list[str]]:
        """Build an inverted index from glossary terms to source IDs."""
        index: dict[str, list[str]] = {}
        for entry in CATALOG_ENTRIES:
            for term in entry.glossary_terms:
                index.setdefault(term.lower(), []).append(entry.source_id)
        return index

    def discover_sources(self, query_terms: list[str]) -> list[DataSourceMapping]:
        """Find relevant data sources based on query terms.

        This simulates how the Agent uses the Semantic Layer
        to determine which MCP servers to invoke for a given query.

        Args:
            query_terms: Keywords extracted from the user's natural language query.

        Returns:
            Ordered list of relevant data source mappings.
        """
        scores: dict[str, int] = {}
        for term in query_terms:
            term_lower = term.lower()
            for source_id_list in self._glossary_index.values():
                for source_id in source_id_list:
                    entry = self._entries[source_id]
                    if term_lower in [t.lower() for t in entry.glossary_terms]:
                        scores[source_id] = scores.get(source_id, 0) + 1
                    if term_lower in entry.description.lower():
                        scores[source_id] = scores.get(source_id, 0) + 1

        ranked = sorted(scores.items(), key=lambda x: -x[1])
        return [self._entries[sid] for sid, _ in ranked]

    def get_all_sources(self) -> list[dict]:
        """Return all registered data sources as a JSON-serializable list."""
        return [
            {
                "source_id": e.source_id,
                "name": e.name,
                "description": e.description,
                "mcp_server": e.mcp_server,
                "tables": e.tables,
                "glossary_terms": e.glossary_terms,
            }
            for e in CATALOG_ENTRIES
        ]

    def get_source_by_server(self, mcp_server: str) -> list[DataSourceMapping]:
        """Get catalog entries for a specific MCP server."""
        return [e for e in CATALOG_ENTRIES if e.mcp_server == mcp_server]
