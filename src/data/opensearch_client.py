# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Amazon OpenSearch Serverless client for quality documents and semantic search.

Uses OpenSearch Serverless for hybrid keyword-vector queries on quality
inspection reports, defect descriptions, and unstructured manufacturing data.

Source: SAP QM → Amazon MSK → OpenSearch Serverless (with vector embeddings)

Environment variables:
  OPENSEARCH_ENDPOINT: OpenSearch Serverless collection endpoint
  OPENSEARCH_INDEX: Index name (default: "quality_metrics")
"""

import json
import logging
import os
from typing import Any

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials
import urllib.request

logger = logging.getLogger(__name__)


class OpenSearchClient:
    """Client for querying Amazon OpenSearch Serverless."""

    def __init__(self) -> None:
        self.endpoint = os.getenv("OPENSEARCH_ENDPOINT", "")
        self.index = os.getenv("OPENSEARCH_INDEX", "quality_metrics")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.session = boto3.Session()

    def search(self, query_body: dict) -> list[dict[str, Any]]:
        """Execute an OpenSearch query with SigV4 authentication.

        Args:
            query_body: OpenSearch DSL query body.

        Returns:
            List of hit source documents.
        """
        url = f"{self.endpoint}/{self.index}/_search"
        body = json.dumps(query_body).encode("utf-8")

        # Sign request with SigV4
        credentials = self.session.get_credentials().get_frozen_credentials()
        request = AWSRequest(method="POST", url=url, data=body, headers={
            "Content-Type": "application/json",
            "Host": self.endpoint.replace("https://", ""),
        })
        SigV4Auth(credentials, "aoss", self.region).add_auth(request)

        # Execute
        req = urllib.request.Request(
            url,
            data=body,
            headers=dict(request.headers),
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        hits = result.get("hits", {}).get("hits", [])
        return [hit["_source"] for hit in hits]


# --------------------------------------------------------------------------
# Domain query functions
# --------------------------------------------------------------------------

_client: OpenSearchClient | None = None


def _get_client() -> OpenSearchClient:
    global _client
    if _client is None:
        _client = OpenSearchClient()
    return _client


def query_quality_metrics(
    line: str | None = None,
    plant: str | None = None,
) -> list[dict]:
    """Query quality metrics from OpenSearch.

    Supports both structured queries (filter by line/plant) and
    semantic search (for defect pattern matching).
    """
    client = _get_client()

    must_clauses: list[dict] = []
    if line:
        must_clauses.append({"term": {"line_name.keyword": line}})
    if plant:
        must_clauses.append({"term": {"plant.keyword": plant}})

    query_body = {
        "size": 50,
        "sort": [{"inspection_date": {"order": "desc"}}],
        "query": {
            "bool": {
                "must": must_clauses if must_clauses else [{"match_all": {}}],
                "filter": [
                    {"range": {"inspection_date": {"gte": "now-28d"}}}
                ],
            }
        },
    }

    return client.search(query_body)


def search_quality_documents(search_text: str, line: str | None = None) -> list[dict]:
    """Semantic search across quality inspection documents.

    Uses OpenSearch hybrid search (keyword + vector) to find relevant
    quality reports, defect patterns, and inspection findings.

    Args:
        search_text: Natural language search query.
        line: Optional line filter.

    Returns:
        List of matching quality documents.
    """
    client = _get_client()

    filter_clauses = []
    if line:
        filter_clauses.append({"term": {"line_name.keyword": line}})

    query_body = {
        "size": 10,
        "query": {
            "bool": {
                "must": [
                    {"multi_match": {
                        "query": search_text,
                        "fields": ["description", "defect_category", "root_cause", "notes"],
                    }}
                ],
                "filter": filter_clauses,
            }
        },
    }

    return client.search(query_body)
