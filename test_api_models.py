"""Tests for the /v1/models API endpoints."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app, adapter_manager, registry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_state():
    """Reset global singletons between tests."""
    # Clear before
    for entry in registry.list_all():
        adapter_manager.remove_adapter(entry.model_id)
    for entry in registry.list_all():
        registry.delete(entry.model_id)
    yield
    # Clear after
    for entry in registry.list_all():
        adapter_manager.remove_adapter(entry.model_id)
    for entry in registry.list_all():
        registry.delete(entry.model_id)


@pytest.fixture()
def client():
    return TestClient(app)


def _model_payload(
    model_id: str = "api-test",
    name: str = "API Test Model",
    family: str = "test",
    capabilities: list[str] | None = None,
    context_length: int = 4096,
    tool_calling: bool = False,
) -> dict:
    return {
        "model_id": model_id,
        "name": name,
        "family": family,
        "capabilities": capabilities or ["TEXT"],
        "context_length": context_length,
        "tool_calling": tool_calling,
    }


# ---------------------------------------------------------------------------
# Registration (POST /v1/models/)
# ---------------------------------------------------------------------------


class TestRegisterModel:
    def test_register_returns_201(self, client):
        resp = client.post("/v1/models/", json=_model_payload())
        assert resp.status_code == 201

    def test_register_returns_entry(self, client):
        resp = client.post("/v1/models/", json=_model_payload())
        body = resp.json()
        assert body["model_id"] == "api-test"
        assert body["name"] == "API Test Model"

    def test_register_invalid_payload(self, client):
        resp = client.post("/v1/models/", json={"name": "missing fields"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Listing (GET /v1/models/)
# ---------------------------------------------------------------------------


class TestListModels:
    def test_empty_list(self, client):
        resp = client.get("/v1/models/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_lists_registered_models(self, client):
        client.post("/v1/models/", json=_model_payload(model_id="a"))
        client.post("/v1/models/", json=_model_payload(model_id="b"))
        resp = client.get("/v1/models/")
        ids = {m["model_id"] for m in resp.json()}
        assert ids == {"a", "b"}


# ---------------------------------------------------------------------------
# Get by ID (GET /v1/models/{id})
# ---------------------------------------------------------------------------


class TestGetModel:
    def test_get_existing(self, client):
        client.post("/v1/models/", json=_model_payload())
        resp = client.get("/v1/models/api-test")
        assert resp.status_code == 200
        assert resp.json()["model_id"] == "api-test"

    def test_get_not_found(self, client):
        resp = client.get("/v1/models/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Delete (DELETE /v1/models/{id})
# ---------------------------------------------------------------------------


class TestDeleteModel:
    def test_delete_existing(self, client):
        client.post("/v1/models/", json=_model_payload())
        resp = client.delete("/v1/models/api-test")
        assert resp.status_code == 200
        assert resp.json()["deleted"] == "api-test"
        # Verify it's gone
        assert client.get("/v1/models/api-test").status_code == 404

    def test_delete_not_found(self, client):
        resp = client.delete("/v1/models/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Generate (POST /v1/models/{id}/generate)
# ---------------------------------------------------------------------------


class TestGenerate:
    def test_generate_success(self, client):
        client.post("/v1/models/", json=_model_payload())
        resp = client.post(
            "/v1/models/api-test/generate",
            json={"prompt": "Hello"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "text" in body
        assert body["model_id"] == "api-test"

    def test_generate_not_found(self, client):
        resp = client.post(
            "/v1/models/nonexistent/generate",
            json={"prompt": "Hello"},
        )
        assert resp.status_code == 404

    def test_generate_invalid_payload(self, client):
        client.post("/v1/models/", json=_model_payload())
        resp = client.post("/v1/models/api-test/generate", json={})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Stream (POST /v1/models/{id}/stream)  —  SSE
# ---------------------------------------------------------------------------


class TestStream:
    def test_stream_success(self, client):
        client.post("/v1/models/", json=_model_payload())
        resp = client.post(
            "/v1/models/api-test/stream",
            json={"prompt": "Hello"},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

    def test_stream_yields_sse_events(self, client):
        client.post("/v1/models/", json=_model_payload())
        resp = client.post(
            "/v1/models/api-test/stream",
            json={"prompt": "Hello"},
        )
        events = [
            line
            for line in resp.text.split("\n")
            if line.startswith("data: ")
        ]
        assert len(events) > 0
        # Last event should have finished=True
        last = json.loads(events[-1].removeprefix("data: "))
        assert last["finished"] is True

    def test_stream_not_found(self, client):
        resp = client.post(
            "/v1/models/nonexistent/stream",
            json={"prompt": "Hello"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tool Call (POST /v1/models/{id}/tool-call)
# ---------------------------------------------------------------------------


class TestToolCall:
    def test_tool_call_success(self, client):
        client.post("/v1/models/", json=_model_payload())
        resp = client.post(
            "/v1/models/api-test/tool-call",
            json={
                "prompt": "Use a tool",
                "tools": [{"name": "my_tool", "description": "A test tool"}],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["model_id"] == "api-test"
        assert len(body["tool_calls"]) >= 1

    def test_tool_call_not_found(self, client):
        resp = client.post(
            "/v1/models/nonexistent/tool-call",
            json={
                "prompt": "Use a tool",
                "tools": [{"name": "t"}],
            },
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Model Health (GET /v1/models/{id}/health)
# ---------------------------------------------------------------------------


class TestModelHealth:
    def test_health_success(self, client):
        client.post("/v1/models/", json=_model_payload())
        resp = client.get("/v1/models/api-test/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["healthy"] is True
        assert body["model_id"] == "api-test"

    def test_health_not_found(self, client):
        resp = client.get("/v1/models/nonexistent/health")
        assert resp.status_code == 404
