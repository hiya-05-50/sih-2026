"""Shared fixtures for integration tests."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


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
    """Expected contract for GET /ready."""
    return {
        "method": "GET",
        "path": "/ready",
        "expected_status": 503,
        "expected_body": {
            "status": "not_ready",
            "reason": "Readiness dependencies are not yet implemented",
        },
    }
