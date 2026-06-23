# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Data provider abstraction — routes between live and simulated data sources.

Controls which data backend the local MCP servers use (SIMULATION_MODE only):
  DATA_MODE=simulated  →  In-memory sample data (default, no AWS infra needed)
  DATA_MODE=live       →  Real AWS services per domain:
                            Equipment/Maintenance → Aurora PostgreSQL (RDS Data API)
                            IoT Telemetry        → Amazon Timestream
                            Supply Chain/OEE     → Amazon Redshift Serverless
                            Quality/Unstructured → Amazon OpenSearch Serverless
                            Config/Catalog       → Amazon S3

Important: This module is only used when SIMULATION_MODE=true (i.e., local MCP
servers handle data retrieval). In the default production architecture, the
AgentCore Gateway routes tool calls to Lambda targets that query AWS services
directly — this data_provider is bypassed entirely.

Set DATA_MODE and SIMULATION_MODE in your .env file or environment variables.
See .env.example for all configuration options.
"""

import json
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

DATA_MODE = os.getenv("DATA_MODE", "simulated")


# ---------------------------------------------------------------------------
# Startup validation
# ---------------------------------------------------------------------------

def _validate_live_mode_credentials() -> None:
    """Warn early if DATA_MODE=live but required env vars are missing.

    This prevents confusing errors deep in Aurora/Timestream/Redshift clients
    when credentials haven't been configured.
    """
    required_vars = {
        "AURORA_CLUSTER_ARN": "Aurora PostgreSQL (Equipment data)",
        "AURORA_SECRET_ARN": "Aurora credentials (Secrets Manager)",
        "TIMESTREAM_DATABASE": "Timestream (IoT telemetry)",
        "REDSHIFT_WORKGROUP": "Redshift Serverless (Supply Chain/OEE)",
    }
    missing = [
        f"  - {var} ({desc})"
        for var, desc in required_vars.items()
        if not os.getenv(var) or "<YOUR_" in os.getenv(var, "")
    ]
    if missing:
        logger.warning(
            "DATA_MODE=live but the following environment variables are missing or "
            "still contain placeholder values:\n%s\n"
            "Live data queries will fail. Set these in your .env file or switch to "
            "DATA_MODE=simulated.\nSee .env.example for reference.",
            "\n".join(missing),
        )


if DATA_MODE == "live":
    _validate_live_mode_credentials()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _compute_stock_status(quantity: int, reorder_point: int) -> str:
    """Determine inventory stock status from quantity vs. reorder point."""
    if quantity == 0:
        return "OUT_OF_STOCK"
    if quantity < reorder_point * 0.5:
        return "CRITICAL"
    if quantity < reorder_point:
        return "LOW"
    return "ADEQUATE"


# ---------------------------------------------------------------------------
# Equipment
# ---------------------------------------------------------------------------

def get_equipment_status(
    line: Optional[str] = None,
    machine_id: Optional[int] = None,
    plant: Optional[str] = None,
) -> str:
    """Get equipment status — routes to Aurora (live) or sample_data (simulated)."""
    if DATA_MODE == "live":
        from src.data.aurora_client import query_equipment_status
        results = query_equipment_status(line=line, machine_id=machine_id, plant=plant)
        return json.dumps(results, default=str)
    else:
        from src.data.sample_data import ASSEMBLY_LINES, EQUIPMENT_REGISTRY
        results = []
        if machine_id is not None:
            machine_name = f"Machine {machine_id}"
            if machine_name in EQUIPMENT_REGISTRY:
                results.append({"machine": machine_name, **EQUIPMENT_REGISTRY[machine_name]})
        elif line is not None:
            for machine_name, info in EQUIPMENT_REGISTRY.items():
                if info["line"] == line:
                    results.append({"machine": machine_name, **info})
        elif plant is not None:
            for machine_name, info in EQUIPMENT_REGISTRY.items():
                if info["plant"] == plant:
                    results.append({"machine": machine_name, **info})
        else:
            for line_name, line_info in ASSEMBLY_LINES.items():
                results.append({
                    "line": line_name,
                    "plant": line_info["plant"],
                    "machine_count": len(line_info["machines"]),
                    "supervisor": line_info["supervisor"],
                })
        return json.dumps(results, default=str)


# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------

def get_maintenance_history(machine_id: int) -> str:
    """Get maintenance history — routes to Aurora (live) or sample_data (simulated)."""
    if DATA_MODE == "live":
        from src.data.aurora_client import query_maintenance_history, query_equipment_status
        equipment = query_equipment_status(machine_id=machine_id)
        history = query_maintenance_history(machine_id)
        return json.dumps({
            "machine": f"Machine {machine_id}",
            "equipment_info": equipment[0] if equipment else {},
            "maintenance_records": history,
            "total_records": len(history),
        }, default=str)
    else:
        from src.data.sample_data import EQUIPMENT_REGISTRY, MAINTENANCE_HISTORY
        machine_name = f"Machine {machine_id}"
        history = MAINTENANCE_HISTORY.get(machine_name, [])
        equipment_info = EQUIPMENT_REGISTRY.get(machine_name, {})
        return json.dumps({
            "machine": machine_name,
            "equipment_info": equipment_info,
            "maintenance_records": history,
            "total_records": len(history),
        }, default=str)


# ---------------------------------------------------------------------------
# IoT Telemetry
# ---------------------------------------------------------------------------

def get_sensor_readings(machine_id: int, metric: str = "temperature", days: int = 7) -> str:
    """Get sensor readings — routes to Timestream (live) or sample_data (simulated)."""
    if DATA_MODE == "live":
        from src.data.timestream_client import query_sensor_readings
        rows = query_sensor_readings(machine_id, metric, days)
        if not rows:
            return json.dumps({"error": f"No readings found for Machine {machine_id}"})
        values = [float(r.get("value", 0)) for r in rows if r.get("value")]
        return json.dumps({
            "machine_id": machine_id,
            "metric": metric,
            "period_days": days,
            "total_readings": len(rows),
            "current_value": values[-1] if values else None,
            "min_value": round(min(values), 2) if values else None,
            "max_value": round(max(values), 2) if values else None,
            "avg_value": round(sum(values) / len(values), 2) if values else None,
            "unit": rows[0].get("unit", "") if rows else "",
            "latest_readings": rows[-6:],
        }, default=str)
    else:
        from src.data.sample_data import generate_sensor_readings
        readings = generate_sensor_readings(machine_id, metric, days)
        if not readings:
            return json.dumps({"error": f"No readings found for Machine {machine_id}"})
        values = [r["value"] for r in readings]
        first_q = sum(values[:len(values) // 4]) / max(len(values) // 4, 1)
        last_q = sum(values[-len(values) // 4:]) / max(len(values) // 4, 1)
        diff = ((last_q - first_q) / first_q) * 100 if first_q else 0
        trend = (
            f"increasing (+{diff:.1f}%)" if diff > 5
            else f"decreasing ({diff:.1f}%)" if diff < -5
            else "stable"
        )
        return json.dumps({
            "machine_id": machine_id,
            "metric": metric,
            "period_days": days,
            "total_readings": len(readings),
            "current_value": values[-1],
            "min_value": round(min(values), 2),
            "max_value": round(max(values), 2),
            "avg_value": round(sum(values) / len(values), 2),
            "unit": readings[0]["unit"],
            "trend": trend,
            "latest_readings": readings[-6:],
        }, default=str)


# ---------------------------------------------------------------------------
# Anomaly Detection
# ---------------------------------------------------------------------------

def detect_anomaly(
    line: Optional[str] = None,
    plant: Optional[str] = None,
    metric: Optional[str] = None,
) -> str:
    """Detect anomalies — routes to Timestream (live) or sample_data (simulated)."""
    if DATA_MODE == "live":
        from src.data.timestream_client import query_anomalies
        anomalies = query_anomalies(line=line, plant=plant)
        if metric:
            anomalies = [a for a in anomalies if a.get("metric") == metric]
        return json.dumps({
            "scan_scope": {"line": line, "plant": plant, "metric": metric},
            "anomalies_found": len(anomalies),
            "anomalies": anomalies,
        }, default=str)
    else:
        from src.data.sample_data import ANOMALY_THRESHOLDS, ASSEMBLY_LINES, generate_sensor_readings
        from datetime import datetime
        anomalies = []
        metrics_to_check = [metric] if metric else ["temperature", "vibration", "pressure"]
        lines_to_check = (
            [line] if line else
            [n for n, i in ASSEMBLY_LINES.items() if i["plant"] == plant] if plant else
            list(ASSEMBLY_LINES.keys())
        )
        for line_name in lines_to_check:
            line_info = ASSEMBLY_LINES.get(line_name, {})
            for machine_name in line_info.get("machines", []):
                mid = int(machine_name.split(" ")[1])
                for m in metrics_to_check:
                    readings = generate_sensor_readings(mid, m, days=1)
                    if not readings:
                        continue
                    val = readings[-1]["value"]
                    thresh = ANOMALY_THRESHOLDS.get(m, {})
                    warning = thresh.get("warning", float("inf"))
                    critical = thresh.get("critical", float("inf"))
                    if val >= critical:
                        sev = "CRITICAL"
                    elif val >= warning:
                        sev = "WARNING"
                    else:
                        continue
                    anomalies.append({
                        "machine": machine_name, "line": line_name, "metric": m,
                        "current_value": round(val, 2),
                        "threshold_warning": warning, "threshold_critical": critical,
                        "unit": thresh.get("unit", ""), "severity": sev,
                        "detected_at": datetime.now().isoformat(),
                    })
        anomalies.sort(key=lambda x: (0 if x["severity"] == "CRITICAL" else 1, -x["current_value"]))
        return json.dumps({
            "scan_scope": {"line": line, "plant": plant, "metric": metric},
            "anomalies_found": len(anomalies),
            "anomalies": anomalies,
        }, default=str)


# ---------------------------------------------------------------------------
# Supply Chain / Inventory
# ---------------------------------------------------------------------------

def check_parts_inventory(
    part_id: Optional[str] = None,
    machine_id: Optional[int] = None,
) -> str:
    """Check parts inventory — routes to Redshift (live) or sample_data (simulated)."""
    if DATA_MODE == "live":
        from src.data.lakehouse_client import query_parts_inventory
        rows = query_parts_inventory(part_id=part_id, machine_id=machine_id)
        results = []
        for r in rows:
            qty = int(r.get("quantity_on_hand", 0))
            reorder = int(r.get("reorder_point", 0))
            r["stock_status"] = _compute_stock_status(qty, reorder)
            results.append(r)
        return json.dumps({
            "inventory_items": results,
            "total_items": len(results),
            "items_below_reorder_point": sum(
                1 for r in results if r["stock_status"] in ("LOW", "CRITICAL", "OUT_OF_STOCK")
            ),
        }, default=str)
    else:
        from src.data.sample_data import PARTS_INVENTORY
        results = []
        if part_id:
            items = {part_id: PARTS_INVENTORY[part_id]} if part_id in PARTS_INVENTORY else {}
        elif machine_id:
            machine_name = f"Machine {machine_id}"
            items = {pid: p for pid, p in PARTS_INVENTORY.items()
                     if any(machine_name in m for m in p.get("applicable_machines", []))}
        else:
            items = PARTS_INVENTORY
        for pid, info in items.items():
            qty = info["quantity_on_hand"]
            reorder = info["reorder_point"]
            results.append({
                "part_id": pid,
                "stock_status": _compute_stock_status(qty, reorder),
                **info,
            })
        return json.dumps({
            "inventory_items": results,
            "total_items": len(results),
            "items_below_reorder_point": sum(
                1 for r in results if r["stock_status"] in ("LOW", "CRITICAL", "OUT_OF_STOCK")
            ),
        }, default=str)


# ---------------------------------------------------------------------------
# OEE (Overall Equipment Effectiveness)
# ---------------------------------------------------------------------------

def get_oee_trends(
    line: Optional[str] = None,
    plant: Optional[str] = None,
) -> str:
    """Get OEE trends — routes to Redshift (live) or sample_data (simulated)."""
    if DATA_MODE == "live":
        from src.data.lakehouse_client import query_oee_trends
        rows = query_oee_trends(line=line, plant=plant)
        trends: dict = {}
        for r in rows:
            ln = r["line_name"]
            if ln not in trends:
                trends[ln] = {"weekly_data": [], "plant": r.get("plant", "")}
            trends[ln]["weekly_data"].append(r)
        for ln, data in trends.items():
            weeks = data["weekly_data"]
            if len(weeks) >= 2:
                change = float(weeks[-1].get("availability", 0)) - float(weeks[0].get("availability", 0))
            else:
                change = 0.0
            data["availability_change_4w"] = round(change, 1)
            data["needs_attention"] = change < -3.0
        return json.dumps({
            "period": "Last 4 weeks", "lines_analyzed": len(trends),
            "lines_needing_attention": sum(1 for v in trends.values() if v["needs_attention"]),
            "trends": trends,
        }, default=str)
    else:
        from src.data.sample_data import ASSEMBLY_LINES, OEE_DATA
        results = {}
        lines_to_report = (
            [line] if line and line in OEE_DATA else
            [n for n, i in ASSEMBLY_LINES.items() if i["plant"] == plant] if plant else
            list(OEE_DATA.keys())
        )
        for ln in lines_to_report:
            weeks = OEE_DATA.get(ln, [])
            if not weeks:
                continue
            change = round(weeks[-1]["availability"] - weeks[0]["availability"], 1) if len(weeks) >= 2 else 0.0
            results[ln] = {
                "weekly_data": weeks, "current_availability": weeks[-1]["availability"],
                "availability_change_4w": change, "needs_attention": change < -3.0,
                "plant": ASSEMBLY_LINES[ln]["plant"],
            }
        ranked = sorted(results.items(), key=lambda x: x[1]["availability_change_4w"])
        return json.dumps({
            "period": "Last 4 weeks", "lines_analyzed": len(results),
            "lines_needing_attention": sum(1 for _, v in results.items() if v["needs_attention"]),
            "trends": dict(ranked),
        }, default=str)


# ---------------------------------------------------------------------------
# Quality
# ---------------------------------------------------------------------------

def get_quality_metrics(
    line: Optional[str] = None,
    plant: Optional[str] = None,
) -> str:
    """Get quality metrics — routes to OpenSearch (live) or sample_data (simulated)."""
    if DATA_MODE == "live":
        from src.data.opensearch_client import query_quality_metrics
        rows = query_quality_metrics(line=line, plant=plant)
        metrics: dict = {}
        for r in rows:
            ln = r.get("line_name", "unknown")
            if ln not in metrics:
                metrics[ln] = {"scrap_rates": [], "defect_categories": set()}
            if r.get("scrap_rate_pct"):
                metrics[ln]["scrap_rates"].append(float(r["scrap_rate_pct"]))
            if r.get("defect_category"):
                metrics[ln]["defect_categories"].add(r["defect_category"])
        result = {}
        for ln, data in metrics.items():
            rates = data["scrap_rates"]
            current = rates[0] if rates else 0
            change = rates[0] - rates[1] if len(rates) >= 2 else 0
            result[ln] = {
                "current_scrap_rate_pct": current,
                "scrap_rate_change_wow": round(change, 2),
                "quality_alert": change > 1.0,
                "defect_categories": list(data["defect_categories"]),
            }
        return json.dumps({
            "lines_analyzed": len(result),
            "quality_alerts": sum(1 for v in result.values() if v["quality_alert"]),
            "metrics": result,
        }, default=str)
    else:
        from src.data.sample_data import ASSEMBLY_LINES, QUALITY_DATA
        results = {}
        lines_to_report = (
            [line] if line and line in QUALITY_DATA else
            [n for n, i in ASSEMBLY_LINES.items() if i["plant"] == plant] if plant else
            list(QUALITY_DATA.keys())
        )
        for ln in lines_to_report:
            quality = QUALITY_DATA.get(ln, {})
            if not quality:
                continue
            scrap_rates = quality.get("weekly_scrap_rate_pct", [])
            current = scrap_rates[-1] if scrap_rates else 0
            change = current - scrap_rates[-2] if len(scrap_rates) >= 2 else 0
            results[ln] = {
                "current_scrap_rate_pct": current,
                "average_scrap_rate_pct": round(sum(scrap_rates) / len(scrap_rates), 2) if scrap_rates else 0,
                "scrap_rate_change_wow": round(change, 2),
                "weekly_scrap_rates": scrap_rates,
                "defect_categories": quality.get("defect_categories", []),
                "quality_alert": change > 1.0,
            }
        return json.dumps({
            "lines_analyzed": len(results),
            "quality_alerts": sum(1 for v in results.values() if v["quality_alert"]),
            "metrics": results,
        }, default=str)
