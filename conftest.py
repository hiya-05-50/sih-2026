"""Shared fixtures for integration tests."""

import pytest
from fastapi.testclient import TestClient
from app.main import app, registry, adapter_manager


@pytest.fixture(autouse=True)
def _clean_integration_state():
    """Reset global singletons between integration tests."""
    for entry in registry.list_all():
        adapter_manager.remove_adapter(entry.model_id)
    for entry in registry.list_all():
        registry.delete(entry.model_id)
    yield
    for entry in registry.list_all():
        adapter_manager.remove_adapter(entry.model_id)
    for entry in registry.list_all():
        registry.delete(entry.model_id)


@pytest.fixture
def client():
    """FastAPI TestClient for integration testing."""
    return TestClient(app)


# Canonical contract fixtures representing the expected API behavior.
# These fixtures define the contract that backend and frontend agree on.
# They can be expanded as new endpoints are added in later sprints.

@pytest.fixture
def root_contract():
    """Expected contract for GET /."""
    return {
        "method": "GET",
        "path": "/",
        "expected_status": 200,
        "expected_body": {
            "name": "SAFIRE Backend",
            "status": "running",
        },
    }


@pytest.fixture
def health_contract():
    """Expected contract for GET /health."""
    return {
        "method": "GET",
        "path": "/health",
        "expected_status": 200,
        "expected_body": {
            "status": "ok",
        },
    }


@pytest.fixture
def ready_contract():
    """Expected contract for GET /ready (no models registered)."""
    return {
        "method": "GET",
        "path": "/ready",
        "expected_status": 503,
        "expected_body": {
            "status": "not_ready",
            "reason": "No models registered",
        },
    }


# Sprint 1 contract fixtures --------------------------------------------------

@pytest.fixture
def register_model_contract():
    """Expected contract for POST /v1/models/."""
    return {
        "method": "POST",
        "path": "/v1/models/",
        "expected_status": 201,
        "payload": {
            "model_id": "contract-model",
            "name": "Contract Model",
            "family": "test",
            "capabilities": ["TEXT"],
            "context_length": 4096,
            "tool_calling": False,
        },
    }


@pytest.fixture
def list_models_contract():
    """Expected contract for GET /v1/models/."""
    return {
        "method": "GET",
        "path": "/v1/models/",
        "expected_status": 200,
    }


@pytest.fixture
def route_no_match_contract():
    """Expected contract for POST /v1/route when no model matches."""
    return {
        "method": "POST",
        "path": "/v1/route",
        "expected_status": 404,
        "payload": {
            "required_capabilities": ["VISION"],
        },
    }
