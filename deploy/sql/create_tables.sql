-- Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
-- SPDX-License-Identifier: MIT-0

-- Schema for manufacturing data in SageMaker Lakehouse (Redshift)
-- 
-- Data sources and ingestion patterns:
--   equipment_registry  ← SAP S/4HANA via Zero-ETL (real-time CDC)
--   maintenance_history ← SAP PM via Zero-ETL (real-time CDC)
--   sensor_readings     ← AWS IoT Core → MSK → S3 Tables (Iceberg, external)
--   detected_anomalies  ← SageMaker inference pipeline (real-time)
--   parts_inventory     ← SAP MM via Zero-ETL (hourly batch)
--   oee_weekly          ← Daily ETL aggregation in Redshift
--   quality_metrics     ← SAP QM via Zero-ETL (real-time CDC)

CREATE SCHEMA IF NOT EXISTS manufacturing;
SET search_path TO manufacturing;

-- ============================================================
-- Equipment Registry (source: SAP S/4HANA)
-- ============================================================
CREATE TABLE IF NOT EXISTS equipment_registry (
    machine_id          INTEGER PRIMARY KEY,
    machine_name        VARCHAR(50) NOT NULL,
    line_name           VARCHAR(20) NOT NULL,
    plant               VARCHAR(20) NOT NULL,
    machine_type        VARCHAR(50),
    install_date        DATE,
    last_maintenance    DATE,
    operating_hours     INTEGER,
    rated_capacity_factor DECIMAL(3,2),
    warranty_months     INTEGER,
    notes               VARCHAR(500)
);

CREATE TABLE IF NOT EXISTS assembly_lines (
    line_name           VARCHAR(20) PRIMARY KEY,
    plant               VARCHAR(20) NOT NULL,
    supervisor          VARCHAR(100),
    machine_count       INTEGER
);

CREATE TABLE IF NOT EXISTS shared_infrastructure (
    infra_id            VARCHAR(50) PRIMARY KEY,
    description         VARCHAR(200),
    serves_lines        SUPER,  -- JSON array of line names
    capacity            DECIMAL(10,2),
    current_load        DECIMAL(10,2),
    last_service_date   DATE
);

-- ============================================================
-- Maintenance History (source: SAP PM)
-- ============================================================
CREATE TABLE IF NOT EXISTS maintenance_history (
    record_id           INTEGER IDENTITY(1,1) PRIMARY KEY,
    machine_id          INTEGER REFERENCES equipment_registry(machine_id),
    maintenance_date    DATE NOT NULL,
    maintenance_type    VARCHAR(20) NOT NULL,  -- 'Corrective', 'Preventive', 'Inspection'
    description         VARCHAR(500),
    technician          VARCHAR(100),
    downtime_hours      DECIMAL(5,2),
    cost                DECIMAL(10,2)
);

-- ============================================================
-- IoT Sensor Readings (source: S3 Tables via Redshift Spectrum)
-- This is an EXTERNAL table pointing to S3 Tables (Iceberg format)
-- Data flows: IoT Core → MSK → S3 Tables
-- ============================================================
-- Note: In production, this would be:
-- CREATE EXTERNAL TABLE sensor_readings (...)
-- STORED AS ICEBERG
-- LOCATION 's3://lakehouse-bucket/sensor_readings/'

CREATE TABLE IF NOT EXISTS sensor_readings (
    reading_timestamp   TIMESTAMP NOT NULL,
    machine_id          INTEGER NOT NULL,
    metric              VARCHAR(20) NOT NULL,  -- 'temperature', 'vibration', 'pressure'
    value               DECIMAL(10,3) NOT NULL,
    unit                VARCHAR(10),
    SORTKEY (machine_id, metric, reading_timestamp)
);

-- ============================================================
-- Detected Anomalies (source: SageMaker inference pipeline)
-- ============================================================
CREATE TABLE IF NOT EXISTS detected_anomalies (
    anomaly_id          INTEGER IDENTITY(1,1) PRIMARY KEY,
    machine_name        VARCHAR(50) NOT NULL,
    line_name           VARCHAR(20) NOT NULL,
    plant               VARCHAR(20),
    metric              VARCHAR(20) NOT NULL,
    current_value       DECIMAL(10,3) NOT NULL,
    threshold_warning   DECIMAL(10,3),
    threshold_critical  DECIMAL(10,3),
    unit                VARCHAR(10),
    severity            VARCHAR(10) NOT NULL,  -- 'WARNING', 'CRITICAL'
    detected_at         TIMESTAMP DEFAULT GETDATE()
);

-- ============================================================
-- Parts Inventory (source: SAP MM)
-- ============================================================
CREATE TABLE IF NOT EXISTS parts_inventory (
    part_id             VARCHAR(50) PRIMARY KEY,
    description         VARCHAR(200) NOT NULL,
    quantity_on_hand    INTEGER NOT NULL,
    reorder_point       INTEGER NOT NULL,
    lead_time_days      INTEGER,
    supplier            VARCHAR(100),
    unit_cost           DECIMAL(10,2)
);

CREATE TABLE IF NOT EXISTS part_machine_mapping (
    part_id             VARCHAR(50) REFERENCES parts_inventory(part_id),
    machine_id          INTEGER REFERENCES equipment_registry(machine_id),
    PRIMARY KEY (part_id, machine_id)
);

-- ============================================================
-- OEE Weekly (source: daily ETL aggregation)
-- ============================================================
CREATE TABLE IF NOT EXISTS oee_weekly (
    line_name           VARCHAR(20) NOT NULL,
    plant               VARCHAR(20) NOT NULL,
    week_start          DATE NOT NULL,
    availability        DECIMAL(5,2),
    performance         DECIMAL(5,2),
    quality             DECIMAL(5,2),
    oee                 DECIMAL(5,2),
    PRIMARY KEY (line_name, week_start)
);

-- ============================================================
-- Quality Metrics (source: SAP QM)
-- ============================================================
CREATE TABLE IF NOT EXISTS quality_metrics (
    record_id           INTEGER IDENTITY(1,1) PRIMARY KEY,
    line_name           VARCHAR(20) NOT NULL,
    plant               VARCHAR(20),
    inspection_date     DATE NOT NULL,
    scrap_rate_pct      DECIMAL(5,2),
    defect_category     VARCHAR(50),
    units_produced      INTEGER,
    units_scrapped      INTEGER
);

-- ============================================================
-- Indexes for common query patterns
-- ============================================================
CREATE INDEX idx_sensor_machine_metric ON sensor_readings(machine_id, metric);
CREATE INDEX idx_anomalies_line ON detected_anomalies(line_name, detected_at);
CREATE INDEX idx_maintenance_machine ON maintenance_history(machine_id, maintenance_date);
CREATE INDEX idx_quality_line_date ON quality_metrics(line_name, inspection_date);
