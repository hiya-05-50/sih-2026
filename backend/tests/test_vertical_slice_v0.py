from __future__ import annotations

"""End-to-end integration tests for Vertical Slice V0:
  `UPLOAD → OCR → EVIDENCE → RETRIEVAL → REASONING → ARTIFACT`
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_upload_document_endpoint(client):
    response = client.post("/v1/documents/upload")
    assert response.status_code == 200
    data = response.json()
    assert "document_id" in data
    assert "sha256_hash" in data
    assert len(data["sha256_hash"]) == 64


def test_parse_document_endpoint(client):
    # 1. Upload
    up_resp = client.post("/v1/documents/upload")
    doc_id = up_resp.json()["document_id"]

    # 2. Parse
    parse_resp = client.post(f"/v1/documents/{doc_id}/parse")
    assert parse_resp.status_code == 200
    data = parse_resp.json()
    assert data["document_id"] == doc_id
    assert len(data["evidence_objects"]) >= 5


def test_full_vertical_slice_v0_pipeline(client):
    doc_id = "doc-v0-test-spec"
    response = client.post(f"/v1/documents/{doc_id}/vertical-slice")
    assert response.status_code == 200

    result = response.json()
    assert "execution_id" in result
    assert result["document_metadata"]["document_id"] == doc_id
    assert result["evidence_count"] >= 5
    assert result["retrieval_indexed_count"] >= 5
    assert "Agent completed in" in result["reasoning_summary"]
    assert result["generated_artifact"]["status"] == "VALIDATED"
    assert result["pipeline_duration_ms"] > 0
