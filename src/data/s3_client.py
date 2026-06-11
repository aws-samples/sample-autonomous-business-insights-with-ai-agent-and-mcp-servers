# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Amazon S3 client for data lake access.

Used for accessing raw historical data, configuration files, and S3 Tables
(Iceberg format) that back the Redshift Spectrum external tables.

Source: Various operational systems → ETL → S3 (Parquet/Iceberg)

Environment variables:
  DATA_LAKE_BUCKET: S3 bucket name for the manufacturing data lake
"""

import json
import logging
import os
from typing import Any

import boto3

logger = logging.getLogger(__name__)


class S3DataLakeClient:
    """Client for accessing manufacturing data lake on S3."""

    def __init__(self) -> None:
        self.client = boto3.client("s3")
        self.bucket = os.getenv("DATA_LAKE_BUCKET", "")

    def get_json_object(self, key: str) -> dict[str, Any]:
        """Retrieve and parse a JSON object from S3.

        Args:
            key: S3 object key.

        Returns:
            Parsed JSON content.
        """
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        content = response["Body"].read().decode("utf-8")
        return json.loads(content)

    def list_objects(self, prefix: str, max_keys: int = 100) -> list[str]:
        """List object keys under a prefix.

        Args:
            prefix: S3 key prefix to search under.
            max_keys: Maximum number of keys to return.

        Returns:
            List of S3 object keys.
        """
        response = self.client.list_objects_v2(
            Bucket=self.bucket,
            Prefix=prefix,
            MaxKeys=max_keys,
        )
        return [obj["Key"] for obj in response.get("Contents", [])]


# --------------------------------------------------------------------------
# Domain query functions
# --------------------------------------------------------------------------

_client: S3DataLakeClient | None = None


def _get_client() -> S3DataLakeClient:
    global _client
    if _client is None:
        _client = S3DataLakeClient()
    return _client


def get_shared_infrastructure_config() -> dict:
    """Load shared infrastructure configuration from S3.

    Shared infrastructure relationships (coolant loops, power feeds)
    are stored as configuration JSON in the data lake.
    """
    client = _get_client()
    try:
        return client.get_json_object("config/shared_infrastructure.json")
    except Exception as e:
        logger.warning("Failed to load shared infrastructure from S3: %s", e)
        return {}


def get_equipment_catalog() -> list[dict]:
    """Load the full equipment catalog from S3 (org-scoped reference data)."""
    client = _get_client()
    try:
        data = client.get_json_object("catalog/equipment_catalog.json")
        return data.get("equipment", [])
    except Exception as e:
        logger.warning("Failed to load equipment catalog from S3: %s", e)
        return []
