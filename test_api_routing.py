"""Tests for the /v1/route API endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app, adapter_manager, registry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_state():
    """Reset global singletons between tests."""
    for entry in registry.list_all():
        adapter_manager.remove_adapter(entry.model_id)
    for entry in registry.list_all():
        registry.delete(entry.model_id)
    yield
    for entry in registry.list_all():
        adapter_manager.remove_adapter(entry.model_id)
    for entry in registry.list_all():
        registry.delete(entry.model_id)


@pytest.fixture()
def client():
    return TestClient(app)


def _register_model(
    client,
    model_id: str = "rt-model",
    capabilities: list[str] | None = None,
    context_length: int = 4096,
) -> None:
    client.post(
        "/v1/models/",
        json={
            "model_id": model_id,
            "name": f"Route Test {model_id}",
            "family": "test",
            "capabilities": capabilities or ["TEXT"],
            "context_length": context_length,
            "tool_calling": False,
        },
    )


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


class TestRouteEndpoint:
    def test_route_finds_match(self, client):
        _register_model(client)
        resp = client.post(
            "/v1/route",
            json={"required_capabilities": ["TEXT"]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["model_id"] == "rt-model"
        assert "reasoning" in body

    def test_route_no_match_returns_404(self, client):
        _register_model(client, capabilities=["TEXT"])
        resp = client.post(
            "/v1/route",
            json={"required_capabilities": ["VISION"]},
        )
        assert resp.status_code == 404

    def test_route_empty_registry_returns_404(self, client):
        resp = client.post(
            "/v1/route",
            json={"required_capabilities": ["TEXT"]},
        )
        assert resp.status_code == 404

    def test_route_with_context_length(self, client):
        _register_model(client, model_id="small", context_length=2048)
        _register_model(client, model_id="large", context_length=8192)
        resp = client.post(
            "/v1/route",
            json={
                "required_capabilities": ["TEXT"],
                "min_context_length": 4096,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["model_id"] == "large"

    def test_route_invalid_payload(self, client):
        resp = client.post("/v1/route", json={})
        assert resp.status_code == 422

    def test_route_empty_capabilities_rejected(self, client):
        resp = client.post(
            "/v1/route",
            json={"required_capabilities": []},
        )
        assert resp.status_code == 422
