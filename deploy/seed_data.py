# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Seed all data infrastructure with sample manufacturing data.

Run after deploying the CloudFormation stack to populate:
- Aurora PostgreSQL (equipment + maintenance)
- Amazon Timestream (IoT sensor readings)
- Amazon Redshift (supply chain + OEE analytics)
- Amazon OpenSearch Serverless (quality metrics)
- Amazon S3 (shared infrastructure config)

Usage:
    python deploy/seed_data.py

Prerequisites:
    - CloudFormation stack deployed
    - .env configured with stack outputs (or pass via environment)
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta

import boto3
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def seed_aurora():
    """Seed Aurora PostgreSQL with equipment and maintenance data."""
    logger.info("Seeding Aurora PostgreSQL...")

    client = boto3.client("rds-data")
    cluster_arn = os.getenv("AURORA_CLUSTER_ARN")
    secret_arn = os.getenv("AURORA_SECRET_ARN")
    database = os.getenv("AURORA_DATABASE", "manufacturing")

    if not cluster_arn or not secret_arn:
        logger.warning("AURORA_CLUSTER_ARN or AURORA_SECRET_ARN not set. Skipping Aurora seeding.")
        return

    def execute(sql):
        client.execute_statement(
            resourceArn=cluster_arn, secretArn=secret_arn, database=database, sql=sql
        )

    # Create tables
    execute("""
        CREATE TABLE IF NOT EXISTS equipment_registry (
            machine_id INTEGER PRIMARY KEY,
            machine_name VARCHAR(50) NOT NULL,
            line_name VARCHAR(20) NOT NULL,
            plant VARCHAR(20) NOT NULL,
            machine_type VARCHAR(50),
            install_date DATE,
            last_maintenance DATE,
            operating_hours INTEGER,
            rated_capacity_factor DECIMAL(3,2),
            warranty_months INTEGER,
            notes VARCHAR(500)
        )
    """)
    execute("""
        CREATE TABLE IF NOT EXISTS assembly_lines (
            line_name VARCHAR(20) PRIMARY KEY,
            plant VARCHAR(20) NOT NULL,
            supervisor VARCHAR(100),
            machine_count INTEGER
        )
    """)
    execute("""
        CREATE TABLE IF NOT EXISTS maintenance_history (
            record_id SERIAL PRIMARY KEY,
            machine_id INTEGER,
            maintenance_date DATE NOT NULL,
            maintenance_type VARCHAR(20) NOT NULL,
            description VARCHAR(500),
            technician VARCHAR(100),
            downtime_hours DECIMAL(5,2),
            cost DECIMAL(10,2)
        )
    """)

    # Seed equipment
    equipment = [
        (42, "Machine 42", "Line 4", "Plant 1", "Conveyor Motor", "2023-06-10", "2025-10-15", 11200, 1.30, 12, "Running at 1.3x rated capacity since January"),
        (43, "Machine 43", "Line 4", "Plant 1", "CNC Mill", "2022-03-15", "2026-04-10", 8500, 0.95, None, None),
        (44, "Machine 44", "Line 4", "Plant 1", "Press", "2022-05-20", "2026-03-22", 7800, 1.00, None, None),
        (45, "Machine 45", "Line 4", "Plant 1", "Welder", "2021-11-10", "2026-05-15", 12000, 0.90, None, None),
        (71, "Machine 71", "Line 7", "Plant 2", "Robot Arm", "2022-01-20", "2026-03-01", 9200, 1.05, None, None),
        (72, "Machine 72", "Line 7", "Plant 2", "CNC Mill", "2022-06-14", "2026-04-20", 8100, 0.92, None, None),
        (91, "Machine 91", "Line 9", "Plant 3", "Conveyor Motor", "2023-02-01", "2026-02-28", 6500, 1.10, None, None),
    ]
    for eq in equipment:
        execute(f"""
            INSERT INTO equipment_registry VALUES ({eq[0]}, '{eq[1]}', '{eq[2]}', '{eq[3]}',
            '{eq[4]}', '{eq[5]}', '{eq[6]}', {eq[7]}, {eq[8]},
            {eq[9] if eq[9] else 'NULL'}, {f"'{eq[10]}'" if eq[10] else 'NULL'})
            ON CONFLICT (machine_id) DO NOTHING
        """)

    # Seed assembly lines
    lines = [
        ("Line 4", "Plant 1", "Anita Sharma", 5),
        ("Line 7", "Plant 2", "Raj Patel", 5),
        ("Line 9", "Plant 3", "Michael Torres", 5),
    ]
    for ln in lines:
        execute(f"INSERT INTO assembly_lines VALUES ('{ln[0]}', '{ln[1]}', '{ln[2]}', {ln[3]}) ON CONFLICT DO NOTHING")

    # Seed maintenance history
    execute("""
        INSERT INTO maintenance_history (machine_id, maintenance_date, maintenance_type, description, technician, downtime_hours, cost)
        VALUES (42, '2025-10-15', 'Corrective', 'Bearing replacement - deep groove ball bearing 6205', 'Priya Nair', 4.5, 680.00)
    """)
    execute("""
        INSERT INTO maintenance_history (machine_id, maintenance_date, maintenance_type, description, technician, downtime_hours, cost)
        VALUES (42, '2026-02-10', 'Preventive', 'Lubrication and alignment check', 'Priya Nair', 1.0, 150.00)
    """)
    execute("""
        INSERT INTO maintenance_history (machine_id, maintenance_date, maintenance_type, description, technician, downtime_hours, cost)
        VALUES (42, '2026-04-25', 'Inspection', 'Vibration elevated but within limits - 3.8 mm/s', 'Priya Nair', 0.5, 75.00)
    """)

    logger.info("  ✓ Aurora seeded with %d machines, %d lines, maintenance records", len(equipment), len(lines))


def seed_timestream():
    """Seed Timestream with IoT sensor readings."""
    logger.info("Seeding Amazon Timestream...")

    write_client = boto3.client("timestream-write")
    database = os.getenv("TIMESTREAM_DATABASE", "manufacturing_iot_dev")
    table = os.getenv("TIMESTREAM_TABLE", "sensor_readings")

    now = int(time.time() * 1000)

    records = []
    # Machine 42 vibration — trending up over 7 days
    for hours_ago in range(168, 0, -4):
        ts = str(now - (hours_ago * 3600 * 1000))
        base = 2.5 + (168 - hours_ago) * 0.02  # Gradual increase
        records.append({
            "Time": ts,
            "Dimensions": [
                {"Name": "machine_id", "Value": "42"},
                {"Name": "machine_name", "Value": "Machine 42"},
                {"Name": "line_name", "Value": "Line 4"},
                {"Name": "plant", "Value": "Plant 1"},
                {"Name": "metric", "Value": "vibration"},
                {"Name": "unit", "Value": "mm/s"},
            ],
            "MeasureName": "value",
            "MeasureValue": f"{base:.2f}",
            "MeasureValueType": "DOUBLE",
        })

    # Machine 42 temperature — trending up
    for hours_ago in range(168, 0, -4):
        ts = str(now - (hours_ago * 3600 * 1000))
        base = 65.0 + (168 - hours_ago) * 0.07
        records.append({
            "Time": ts,
            "Dimensions": [
                {"Name": "machine_id", "Value": "42"},
                {"Name": "machine_name", "Value": "Machine 42"},
                {"Name": "line_name", "Value": "Line 4"},
                {"Name": "plant", "Value": "Plant 1"},
                {"Name": "metric", "Value": "temperature"},
                {"Name": "unit", "Value": "C"},
            ],
            "MeasureName": "value",
            "MeasureValue": f"{base:.2f}",
            "MeasureValueType": "DOUBLE",
        })

    # Write in batches of 100
    for i in range(0, len(records), 100):
        batch = records[i:i + 100]
        try:
            write_client.write_records(
                DatabaseName=database,
                TableName=table,
                Records=batch,
            )
        except Exception as e:
            logger.warning("  Timestream batch %d: %s", i // 100, e)

    logger.info("  ✓ Timestream seeded with %d sensor readings", len(records))


def seed_redshift():
    """Seed Redshift with supply chain and OEE data."""
    logger.info("Seeding Amazon Redshift Serverless...")

    client = boto3.client("redshift-data")
    workgroup = os.getenv("REDSHIFT_WORKGROUP")
    database = os.getenv("REDSHIFT_DATABASE", "manufacturing")

    if not workgroup:
        logger.warning("REDSHIFT_WORKGROUP not set. Skipping Redshift seeding.")
        return

    def execute(sql):
        resp = client.execute_statement(WorkgroupName=workgroup, Database=database, Sql=sql)
        # Wait for completion
        stmt_id = resp["Id"]
        while True:
            status = client.describe_statement(Id=stmt_id)["Status"]
            if status == "FINISHED":
                return
            elif status in ("FAILED", "ABORTED"):
                raise RuntimeError(f"Redshift query failed: {client.describe_statement(Id=stmt_id).get('Error')}")
            time.sleep(2)

    # Create tables
    execute("""
        CREATE TABLE IF NOT EXISTS parts_inventory (
            part_id VARCHAR(50) PRIMARY KEY, description VARCHAR(200),
            quantity_on_hand INTEGER, reorder_point INTEGER,
            lead_time_days INTEGER, supplier VARCHAR(100), unit_cost DECIMAL(10,2)
        )
    """)
    execute("""
        CREATE TABLE IF NOT EXISTS oee_weekly (
            line_name VARCHAR(20), plant VARCHAR(20), week_start DATE,
            availability DECIMAL(5,2), performance DECIMAL(5,2),
            quality DECIMAL(5,2), oee DECIMAL(5,2),
            PRIMARY KEY (line_name, week_start)
        )
    """)

    # Seed parts
    execute("""
        INSERT INTO parts_inventory VALUES
        ('bearing_6205', 'Deep Groove Ball Bearing 6205', 12, 20, 14, 'SKF Industrial', 45.00),
        ('motor_coolant_5L', 'Synthetic Coolant 5L', 85, 50, 3, 'CastrolPro', 32.00),
        ('vibration_sensor_vs200', 'Vibration Sensor VS-200', 5, 10, 21, 'Bruel & Kjaer', 890.00),
        ('drive_belt_v42', 'V-Belt for Motor Drive Size 42', 8, 15, 7, 'Gates Industrial', 28.00)
    """)

    # Seed OEE
    execute("""
        INSERT INTO oee_weekly VALUES
        ('Line 4', 'Plant 1', '2026-05-19', 94.0, 91.5, 98.2, 84.5),
        ('Line 4', 'Plant 1', '2026-05-26', 91.7, 89.0, 97.8, 79.8),
        ('Line 4', 'Plant 1', '2026-06-02', 89.4, 88.5, 96.5, 76.4),
        ('Line 4', 'Plant 1', '2026-06-09', 87.1, 87.0, 95.2, 72.2),
        ('Line 7', 'Plant 2', '2026-05-19', 92.0, 90.5, 98.5, 81.9),
        ('Line 7', 'Plant 2', '2026-05-26', 91.5, 91.0, 98.0, 81.7),
        ('Line 7', 'Plant 2', '2026-06-02', 91.8, 90.0, 98.2, 81.1),
        ('Line 7', 'Plant 2', '2026-06-09', 91.2, 91.5, 97.8, 81.5),
        ('Line 9', 'Plant 3', '2026-05-19', 92.0, 90.0, 98.0, 81.1),
        ('Line 9', 'Plant 3', '2026-05-26', 90.5, 89.5, 97.5, 79.0),
        ('Line 9', 'Plant 3', '2026-06-02', 89.0, 90.0, 97.8, 78.3),
        ('Line 9', 'Plant 3', '2026-06-09', 87.5, 89.0, 97.5, 75.9)
    """)

    logger.info("  ✓ Redshift seeded with parts inventory and OEE data")


def seed_s3():
    """Seed S3 with configuration and catalog data."""
    logger.info("Seeding Amazon S3...")

    s3 = boto3.client("s3")
    bucket = os.getenv("DATA_LAKE_BUCKET")

    if not bucket:
        logger.warning("DATA_LAKE_BUCKET not set. Skipping S3 seeding.")
        return

    # Shared infrastructure config
    shared_infra = {
        "coolant_loop_A": {
            "description": "Primary coolant supply loop",
            "serves": ["Line 4", "Line 9"],
            "capacity_liters_per_min": 120,
            "current_flow_rate": 108,
            "temperature_inlet": 18.5,
            "temperature_outlet": 24.2,
            "last_filter_change": "2026-04-10",
        },
        "power_feed_B": {
            "description": "480V power distribution bus B",
            "serves": ["Line 7", "Line 8"],
            "capacity_kw": 500,
            "current_load_kw": 380,
        },
    }
    s3.put_object(
        Bucket=bucket,
        Key="config/shared_infrastructure.json",
        Body=json.dumps(shared_infra, indent=2),
        ContentType="application/json",
    )

    # Equipment catalog
    catalog = {
        "equipment": [
            {"machine_id": 42, "type": "Conveyor Motor", "manufacturer": "Siemens", "model": "1LE1"},
            {"machine_id": 43, "type": "CNC Mill", "manufacturer": "DMG Mori", "model": "CMX 50"},
            {"machine_id": 71, "type": "Robot Arm", "manufacturer": "FANUC", "model": "M-20iD"},
        ]
    }
    s3.put_object(
        Bucket=bucket,
        Key="catalog/equipment_catalog.json",
        Body=json.dumps(catalog, indent=2),
        ContentType="application/json",
    )

    logger.info("  ✓ S3 seeded with shared infrastructure config and equipment catalog")


def seed_opensearch():
    """Seed OpenSearch Serverless with quality metrics."""
    logger.info("Seeding Amazon OpenSearch Serverless...")

    endpoint = os.getenv("OPENSEARCH_ENDPOINT")
    index = os.getenv("OPENSEARCH_INDEX", "quality_metrics")

    if not endpoint:
        logger.warning("OPENSEARCH_ENDPOINT not set. Skipping OpenSearch seeding.")
        return

    # Use boto3 to sign requests
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest
    import urllib.request

    session = boto3.Session()
    credentials = session.get_credentials().get_frozen_credentials()
    region = os.getenv("AWS_REGION", "us-east-1")

    def put_doc(doc_id, doc):
        url = f"{endpoint}/{index}/_doc/{doc_id}"
        body = json.dumps(doc).encode("utf-8")
        request = AWSRequest(method="PUT", url=url, data=body, headers={
            "Content-Type": "application/json",
        })
        SigV4Auth(credentials, "aoss", region).add_auth(request)
        req = urllib.request.Request(url, data=body, headers=dict(request.headers), method="PUT")
        try:
            urllib.request.urlopen(req)
        except Exception as e:
            logger.warning("  OpenSearch doc %s: %s", doc_id, e)

    # Quality metrics documents
    docs = [
        {"line_name": "Line 4", "plant": "Plant 1", "inspection_date": "2026-06-03", "scrap_rate_pct": 3.5, "defect_category": "dimensional", "units_produced": 1000, "units_scrapped": 35, "description": "Dimensional tolerance failures on shaft assemblies", "root_cause": "Suspected bearing wear causing thermal expansion"},
        {"line_name": "Line 4", "plant": "Plant 1", "inspection_date": "2026-05-27", "scrap_rate_pct": 1.8, "defect_category": "surface_finish", "units_produced": 1050, "units_scrapped": 19, "description": "Surface roughness out of spec", "root_cause": "Tool wear on CNC Mill"},
        {"line_name": "Line 7", "plant": "Plant 2", "inspection_date": "2026-06-03", "scrap_rate_pct": 1.1, "defect_category": "assembly_error", "units_produced": 980, "units_scrapped": 11, "description": "Minor assembly alignment issues", "root_cause": "Operator training gap"},
        {"line_name": "Line 9", "plant": "Plant 3", "inspection_date": "2026-06-03", "scrap_rate_pct": 1.2, "defect_category": "surface_finish", "units_produced": 1020, "units_scrapped": 12, "description": "Coolant contamination causing surface defects", "root_cause": "Shared coolant loop filter degradation"},
    ]

    for i, doc in enumerate(docs):
        put_doc(f"quality-{i}", doc)

    logger.info("  ✓ OpenSearch seeded with %d quality metric documents", len(docs))


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Seeding Manufacturing Data Infrastructure")
    logger.info("=" * 60)

    seed_aurora()
    seed_timestream()
    seed_redshift()
    seed_s3()
    seed_opensearch()

    logger.info("\n" + "=" * 60)
    logger.info("✅ All data sources seeded successfully!")
    logger.info("=" * 60)
    logger.info("\nYou can now run the agent in live mode:")
    logger.info("  export DATA_MODE=live")
    logger.info("  python -m src.servers.start_all")
    logger.info("  streamlit run src/demo_ui.py")
