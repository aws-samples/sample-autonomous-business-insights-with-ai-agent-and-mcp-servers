# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Simulated manufacturing data for demo purposes.

In production, this data would come from SageMaker Lakehouse, Redshift,
Aurora, IoT Core, and other enterprise systems via their respective MCP
server connectors.
"""

from datetime import datetime, timedelta
import random

# --------------------------------------------------------------------------
# Equipment Registry
# --------------------------------------------------------------------------

ASSEMBLY_LINES = {
    f"Line {i}": {
        "line_id": f"LINE-{i:02d}",
        "plant": f"Plant {1 if i <= 4 else (2 if i <= 8 else 3)}",
        "machines": [f"Machine {i * 10 + j}" for j in range(1, 6)],
        "supervisor": (
            "Raj Patel" if i == 7 else
            "Anita Sharma" if i <= 4 else
            "Michael Torres"
        ),
    }
    for i in range(1, 13)
}

EQUIPMENT_REGISTRY = {}
for line_name, line_info in ASSEMBLY_LINES.items():
    for machine in line_info["machines"]:
        machine_id = int(machine.split(" ")[1])
        EQUIPMENT_REGISTRY[machine] = {
            "machine_id": machine_id,
            "line": line_name,
            "plant": line_info["plant"],
            "type": random.choice(["CNC Mill", "Press", "Robot Arm", "Conveyor Motor", "Welder"]),
            "install_date": "2022-03-15",
            "last_maintenance": (
                datetime.now() - timedelta(days=random.randint(30, 240))
            ).strftime("%Y-%m-%d"),
            "operating_hours": random.randint(5000, 15000),
            "rated_capacity_factor": round(random.uniform(0.8, 1.4), 2),
        }

# Specific scenario data for Machine 42 (Line 4) from the blog narrative
EQUIPMENT_REGISTRY["Machine 42"] = {
    "machine_id": 42,
    "line": "Line 4",
    "plant": "Plant 1",
    "type": "Conveyor Motor",
    "install_date": "2023-06-10",
    "last_maintenance": (datetime.now() - timedelta(days=240)).strftime("%Y-%m-%d"),
    "last_maintenance_type": "Bearing Replacement",
    "warranty_months": 12,
    "operating_hours": 11200,
    "rated_capacity_factor": 1.3,
    "notes": "Running at 1.3x rated capacity since January",
}

# --------------------------------------------------------------------------
# IoT Sensor Data (simulated time-series)
# --------------------------------------------------------------------------


def generate_sensor_readings(machine_id: int, metric: str, days: int = 7) -> list[dict]:
    """Generate simulated sensor readings for a machine."""
    readings = []
    now = datetime.now()

    # Machine 42 has anomalous temperature trending
    is_anomalous = machine_id == 42 and metric == "temperature"

    for day in range(days, 0, -1):
        for hour in range(0, 24, 4):
            timestamp = now - timedelta(days=day, hours=hour)
            if metric == "temperature":
                baseline = 65.0
                if is_anomalous:
                    # Trending 12°C above baseline over 3 days
                    trend = min(12.0, (days - day) * 4.0)
                    value = baseline + trend + random.uniform(-1.5, 1.5)
                else:
                    value = baseline + random.uniform(-3, 3)
            elif metric == "vibration":
                baseline = 2.5  # mm/s
                if machine_id == 42:
                    # Gradually increasing vibration
                    trend = (days - day) * 0.3
                    value = baseline + trend + random.uniform(-0.2, 0.2)
                else:
                    value = baseline + random.uniform(-0.5, 0.5)
            elif metric == "pressure":
                baseline = 4.2  # bar
                value = baseline + random.uniform(-0.3, 0.3)
            else:
                value = random.uniform(0, 100)

            readings.append({
                "timestamp": timestamp.isoformat(),
                "machine_id": machine_id,
                "metric": metric,
                "value": round(value, 2),
                "unit": {
                    "temperature": "°C",
                    "vibration": "mm/s",
                    "pressure": "bar",
                }.get(metric, ""),
            })

    return readings


# --------------------------------------------------------------------------
# Anomaly Detection Thresholds
# --------------------------------------------------------------------------

ANOMALY_THRESHOLDS = {
    "temperature": {"warning": 72.0, "critical": 80.0, "unit": "°C"},
    "vibration": {"warning": 4.0, "critical": 6.0, "unit": "mm/s"},
    "pressure": {"warning": 5.0, "critical": 6.0, "unit": "bar"},
}

# --------------------------------------------------------------------------
# OEE (Overall Equipment Effectiveness) Data
# --------------------------------------------------------------------------

OEE_DATA = {}
for line_name in ASSEMBLY_LINES:
    weekly_oee = []
    base_availability = random.uniform(88, 96)
    for week in range(4, 0, -1):
        # Line 4 shows declining availability
        if line_name == "Line 4":
            availability = 94.0 - (4 - week) * 2.3
        elif line_name == "Line 9":
            availability = 92.0 - (4 - week) * 1.5
        else:
            availability = base_availability + random.uniform(-1, 1)

        weekly_oee.append({
            "week": f"W-{week}",
            "availability": round(availability, 1),
            "performance": round(random.uniform(85, 95), 1),
            "quality": round(random.uniform(96, 99.5), 1),
            "oee": round(
                availability * random.uniform(85, 95) * random.uniform(96, 99.5) / 10000, 1
            ),
        })
    OEE_DATA[line_name] = weekly_oee

# --------------------------------------------------------------------------
# Quality Metrics
# --------------------------------------------------------------------------

QUALITY_DATA = {}
for line_name in ASSEMBLY_LINES:
    if line_name == "Line 4":
        scrap_rate = [1.2, 1.4, 1.8, 3.5]  # Jump on last Tuesday
    elif line_name == "Line 9":
        scrap_rate = [1.1, 1.1, 1.2, 1.2]  # No quality impact yet
    else:
        scrap_rate = [round(random.uniform(0.8, 1.5), 1) for _ in range(4)]

    QUALITY_DATA[line_name] = {
        "weekly_scrap_rate_pct": scrap_rate,
        "defect_categories": ["dimensional", "surface_finish", "assembly_error"],
        "last_inspection": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
    }

# --------------------------------------------------------------------------
# Supply Chain / Inventory
# --------------------------------------------------------------------------

PARTS_INVENTORY = {
    "bearing_6205": {
        "description": "Deep Groove Ball Bearing 6205",
        "quantity_on_hand": 12,
        "reorder_point": 20,
        "lead_time_days": 14,
        "supplier": "SKF Industrial",
        "unit_cost": 45.00,
        "applicable_machines": ["Machine 42", "Machine 43", "Machine 51"],
    },
    "motor_coolant_5L": {
        "description": "Synthetic Coolant 5L",
        "quantity_on_hand": 85,
        "reorder_point": 50,
        "lead_time_days": 3,
        "supplier": "CastrolPro",
        "unit_cost": 32.00,
        "applicable_machines": ["Line 4 (all)", "Line 9 (all)"],
    },
    "vibration_sensor_vs200": {
        "description": "Vibration Sensor VS-200",
        "quantity_on_hand": 5,
        "reorder_point": 10,
        "lead_time_days": 21,
        "supplier": "Bruel & Kjaer",
        "unit_cost": 890.00,
        "applicable_machines": ["All lines"],
    },
    "drive_belt_v42": {
        "description": "V-Belt for Motor Drive Size 42",
        "quantity_on_hand": 8,
        "reorder_point": 15,
        "lead_time_days": 7,
        "supplier": "Gates Industrial",
        "unit_cost": 28.00,
        "applicable_machines": ["Machine 42", "Machine 72"],
    },
}

# --------------------------------------------------------------------------
# Maintenance History
# --------------------------------------------------------------------------

MAINTENANCE_HISTORY = {
    "Machine 42": [
        {
            "date": (datetime.now() - timedelta(days=240)).strftime("%Y-%m-%d"),
            "type": "Corrective",
            "description": "Bearing replacement - deep groove ball bearing 6205",
            "technician": "Priya Nair",
            "downtime_hours": 4.5,
            "cost": 680.00,
        },
        {
            "date": (datetime.now() - timedelta(days=120)).strftime("%Y-%m-%d"),
            "type": "Preventive",
            "description": "Lubrication and alignment check",
            "technician": "Priya Nair",
            "downtime_hours": 1.0,
            "cost": 150.00,
        },
        {
            "date": (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d"),
            "type": "Inspection",
            "description": "Vibration measurement - elevated but within limits",
            "technician": "Priya Nair",
            "downtime_hours": 0.5,
            "cost": 75.00,
        },
    ],
}

# --------------------------------------------------------------------------
# Shared Infrastructure Relationships (not modeled in most dashboards)
# --------------------------------------------------------------------------

SHARED_INFRASTRUCTURE = {
    "coolant_loop_A": {
        "description": "Primary coolant supply loop",
        "serves": ["Line 4", "Line 9"],
        "capacity_liters_per_min": 120,
        "current_flow_rate": 108,
        "temperature_inlet": 18.5,
        "temperature_outlet": 24.2,
        "last_filter_change": (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d"),
    },
}
